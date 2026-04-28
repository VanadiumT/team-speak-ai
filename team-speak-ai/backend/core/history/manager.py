"""
HistoryManager —— 撤销/重做操作栈

每个 flow 独立维护 undo_stack + redo_stack（上限 100 条），JSONL 持久化。
"""

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

    # ── 文件路径 ───────────────────────────────────────────────

    def _history_path(self, flow_id: str) -> Path:
        return self.history_dir / f"{flow_id}.jsonl"

    # ── 记录操作 ───────────────────────────────────────────────

    def record_operation(self, flow_id: str, action: str,
                         forward: dict, reverse: dict) -> dict:
        """记录一条可撤销操作，返回操作记录"""
        now = datetime.now(timezone.utc)
        op = {
            "seq": self._next_seq(flow_id),
            "action": action,
            "timestamp": now.isoformat(),
            "forward": forward,
            "reverse": reverse,
        }

        # 检查是否需要合并
        stack = self._get_undo_stack(flow_id)
        if stack and self._should_merge(stack[-1], op):
            merged = self._merge_ops(stack[-1], op)
            stack[-1] = merged
            # 更新 JSONL（重写最后一行）
            self._rewrite_last_line(flow_id, merged)
        else:
            stack.append(op)
            self._append_to_jsonl(flow_id, op)

        # 清空 redo 栈（新操作使 redo 失效）
        self._redo_stacks[flow_id] = []

        # 裁剪
        if len(stack) > MAX_STACK_SIZE:
            stack.pop(0)

        return op

    # ── 撤销 / 重做 ────────────────────────────────────────────

    def undo(self, flow_id: str) -> Optional[dict]:
        """撤销一步，返回被撤销的操作"""
        stack = self._get_undo_stack(flow_id)
        if not stack:
            return None

        op = stack.pop()
        self._get_redo_stack(flow_id).append(op)

        # 从 JSONL 移除最后一行
        self._pop_last_line(flow_id)

        logger.debug(f"Undo [{flow_id}]: {op['action']} (seq {op['seq']})")
        return op

    def redo(self, flow_id: str) -> Optional[dict]:
        """重做一步，返回被重做的操作"""
        redo_stack = self._get_redo_stack(flow_id)
        if not redo_stack:
            return None

        op = redo_stack.pop()
        self._get_undo_stack(flow_id).append(op)

        # 重做操作追加到 JSONL
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
        # 裁剪
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
        """同一节点 500ms 内的连续 update_config 可以合并"""
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
        """合并两次 update_config：forward 取最新，reverse 保留最早"""
        return {
            "seq": prev["seq"],
            "action": prev["action"],
            "timestamp": current["timestamp"],
            "forward": current["forward"],
            "reverse": prev["reverse"],
        }

    def _append_to_jsonl(self, flow_id: str, op: dict) -> None:
        path = self._history_path(flow_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(op, ensure_ascii=False) + "\n")

    def _pop_last_line(self, flow_id: str) -> None:
        """从 JSONL 文件移除最后一行"""
        path = self._history_path(flow_id)
        if not path.exists():
            return
        lines = []
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if lines:
            lines = lines[:-1]
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)

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
