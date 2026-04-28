"""
HistoryManager —— 撤销/重做操作栈

每个 flow 独立维护 undo_stack + redo_stack（上限 100 条），JSONL 持久化。
使用 asyncio.Lock 保证同一 flow 的并发操作安全。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_STACK_SIZE = 100
MERGE_WINDOW_MS = 500  # 合并窗口


class HistoryManager:
    """操作历史管理（撤销/重做）"""

    def __init__(self, data_dir: str):
        self.history_dir = Path(data_dir) / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._undo_stacks: dict[str, list[dict]] = {}
        self._redo_stacks: dict[str, list[dict]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, flow_id: str) -> asyncio.Lock:
        if flow_id not in self._locks:
            self._locks[flow_id] = asyncio.Lock()
        return self._locks[flow_id]

    # ── 文件路径 ───────────────────────────────────────────────

    def _history_path(self, flow_id: str) -> Path:
        return self.history_dir / f"{flow_id}.jsonl"

    # ── 记录操作 ───────────────────────────────────────────────

    async def record_operation(self, flow_id: str, action: str,
                               forward: dict, reverse: dict) -> dict:
        """记录一条可撤销操作，返回操作记录"""
        async with self._get_lock(flow_id):
            return self._record_operation_sync(flow_id, action, forward, reverse)

    def _record_operation_sync(self, flow_id: str, action: str,
                               forward: dict, reverse: dict) -> dict:
        now = datetime.now(timezone.utc)
        op = {
            "seq": self._next_seq(flow_id),
            "action": action,
            "timestamp": now.isoformat(),
            "forward": forward,
            "reverse": reverse,
        }

        stack = self._get_undo_stack(flow_id)

        if stack and self._should_merge(stack[-1], op):
            merged = self._merge_ops(stack[-1], op)
            stack[-1] = merged
            self._rewrite_last_line(flow_id, merged)
        else:
            stack.append(op)
            self._append_to_jsonl(flow_id, op)

        # 清空 redo 栈（新操作使 redo 失效）
        self._redo_stacks[flow_id] = []

        # 裁剪：超过上限时移除最旧条目
        if len(stack) > MAX_STACK_SIZE:
            removed = stack.pop(0)
            logger.debug(f"History stack trimmed for [{flow_id}]: removed seq {removed['seq']}")

        return op

    # ── 撤销 / 重做 ────────────────────────────────────────────

    async def undo(self, flow_id: str) -> Optional[dict]:
        """撤销一步，返回被撤销的操作"""
        async with self._get_lock(flow_id):
            return self._undo_sync(flow_id)

    def _undo_sync(self, flow_id: str) -> Optional[dict]:
        stack = self._get_undo_stack(flow_id)
        if not stack:
            return None

        op = stack.pop()
        self._get_redo_stack(flow_id).append(op)
        self._truncate_last_line(flow_id, len(stack))

        logger.debug(f"Undo [{flow_id}]: {op['action']} (seq {op['seq']})")
        return op

    async def redo(self, flow_id: str) -> Optional[dict]:
        """重做一步，返回被重做的操作"""
        async with self._get_lock(flow_id):
            return self._redo_sync(flow_id)

    def _redo_sync(self, flow_id: str) -> Optional[dict]:
        redo_stack = self._get_redo_stack(flow_id)
        if not redo_stack:
            return None

        op = redo_stack.pop()
        self._get_undo_stack(flow_id).append(op)
        self._append_to_jsonl(flow_id, op)

        logger.debug(f"Redo [{flow_id}]: {op['action']} (seq {op['seq']})")
        return op

    def can_undo(self, flow_id: str) -> bool:
        return len(self._get_undo_stack(flow_id)) > 0

    def can_redo(self, flow_id: str) -> bool:
        return len(self._get_redo_stack(flow_id)) > 0

    def history_state(self, flow_id: str) -> dict:
        """返回当前可撤销/重做状态"""
        stack = self._get_undo_stack(flow_id)
        last_action = stack[-1]["action"] if stack else None
        return {
            "can_undo": self.can_undo(flow_id),
            "can_redo": self.can_redo(flow_id),
            "last_action": last_action,
        }

    # ── 加载 ───────────────────────────────────────────────────

    def load_history(self, flow_id: str) -> None:
        """从 JSONL 加载操作历史到内存"""
        path = self._history_path(flow_id)
        if not path.exists():
            self._undo_stacks[flow_id] = []
            self._redo_stacks[flow_id] = []
            return

        stack = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stack.append(json.loads(line))
        if len(stack) > MAX_STACK_SIZE:
            stack = stack[-MAX_STACK_SIZE:]
            self._rewrite_all(flow_id, stack)
        self._undo_stacks[flow_id] = stack
        self._redo_stacks[flow_id] = []

    # ── 内部方法 ───────────────────────────────────────────────

    def _get_undo_stack(self, flow_id: str) -> list[dict]:
        if flow_id not in self._undo_stacks:
            self.load_history(flow_id)
        return self._undo_stacks[flow_id]

    def _get_redo_stack(self, flow_id: str) -> list[dict]:
        if flow_id not in self._redo_stacks:
            self._redo_stacks[flow_id] = []
        return self._redo_stacks[flow_id]

    def _next_seq(self, flow_id: str) -> int:
        stack = self._get_undo_stack(flow_id)
        return stack[-1]["seq"] + 1 if stack else 1

    @staticmethod
    def _should_merge(prev: dict, current: dict) -> bool:
        if prev.get("action") != "node.update_config":
            return False
        if current.get("action") != "node.update_config":
            return False
        nid_prev = prev.get("forward", {}).get("node_id", "")
        nid_cur = current.get("forward", {}).get("node_id", "")
        if nid_prev != nid_cur:
            return False
        try:
            t_prev = datetime.fromisoformat(prev["timestamp"])
            t_cur = datetime.fromisoformat(current["timestamp"])
            return (t_cur - t_prev).total_seconds() * 1000 <= MERGE_WINDOW_MS
        except (KeyError, ValueError):
            return False

    @staticmethod
    def _merge_ops(prev: dict, current: dict) -> dict:
        return {
            "seq": prev["seq"],
            "action": prev["action"],
            "timestamp": current["timestamp"],
            "forward": current["forward"],
            "reverse": prev["reverse"],
        }

    # ── JSONL 文件操作 ────────────────────────────────────────

    def _append_to_jsonl(self, flow_id: str, op: dict) -> None:
        path = self._history_path(flow_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(op, ensure_ascii=False) + "\n")

    def _truncate_last_line(self, flow_id: str, new_size: int) -> None:
        """通过文件截断移除最后一行，用于 undo 操作"""
        path = self._history_path(flow_id)
        if not path.exists():
            return
        # 重写文件只保留前 new_size 行（一次读写, O(n) 但 n≤100 可以接受）
        if new_size == 0:
            with open(path, "w", encoding="utf-8") as f:
                pass
            return
        lines = []
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > new_size:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines[:new_size])

    def _rewrite_last_line(self, flow_id: str, op: dict) -> None:
        path = self._history_path(flow_id)
        lines = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        if lines:
            lines[-1] = json.dumps(op, ensure_ascii=False) + "\n"
        else:
            lines = [json.dumps(op, ensure_ascii=False) + "\n"]
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def _rewrite_all(self, flow_id: str, stack: list[dict]) -> None:
        path = self._history_path(flow_id)
        with open(path, "w", encoding="utf-8") as f:
            for op in stack:
                f.write(json.dumps(op, ensure_ascii=False) + "\n")


# 全局单例
_history_manager: Optional[HistoryManager] = None


def get_history_manager() -> HistoryManager:
    global _history_manager
    if _history_manager is None:
        raise RuntimeError("HistoryManager not initialized")
    return _history_manager


def init_history_manager(data_dir: str) -> HistoryManager:
    global _history_manager
    _history_manager = HistoryManager(data_dir)
    return _history_manager
