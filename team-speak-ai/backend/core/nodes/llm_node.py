"""
LLM 节点 — 调用大模型生成文本

支持流式/非流式输出、多模态图片输入、思考层级控制。
配置通过预设系统 (PresetManager) 管理。
"""

import logging
import re
from core.nodes.base import BaseNode
from core.pipeline.context import NodeContext, NodeOutput
from core.pipeline.emitter import EventEmitter
from core.pipeline.registry import NodeRegistry
from core.llm.factory import LLMProvider, create_llm
from core.config.defaults import get_preset_manager
from config import settings

logger = logging.getLogger(__name__)

# 匹配内嵌思考标签：<think>...</think>（兼容 MiniMax / DeepSeek / 其他格式）
_THINK_RE = re.compile(r'<\s*think\s*>(.*?)<\s*/\s*think\s*>', re.IGNORECASE | re.DOTALL)


@NodeRegistry.register("llm")
class LLMNode(BaseNode):
    """大模型文本生成节点"""

    node_type = "llm"

    async def execute(self, context: NodeContext, emit: EventEmitter) -> NodeOutput:
        cfg = context.node_config

        try:
            # ── 检测新旧配置格式 ──
            if cfg.get("platform_id") and cfg.get("model_id"):
                effective = self._resolve_preset_config(cfg)
            else:
                effective = self._resolve_legacy_config(cfg)

            # ── 构建 messages（兼容 as_field 为 "llm" 或 "messages" 的映射） ──
            messages = context.inputs.get("llm") or context.inputs.get("messages") or []
            if not messages:
                messages = [{"role": "user", "content": "你好"}]

            images = context.inputs.get("image", []) or []
            if effective.get("vision") and images:
                messages = self._inject_images(messages, images, effective)

            # ── 构造 LLM 实例 ──
            llm = self._build_llm(effective)

            # ── 思考模式 ──
            thinking_mode = effective.get("thinking_mode", "off")
            yield_reasoning = thinking_mode == "separate"

            await emit.emit_node_update(
                context.node_id, "processing", "AI 思考中...",
                data={"mode": "thinking"},
            )

            model_name = effective.get("model", "")

            if effective.get("streaming", True):
                return await self._execute_streaming(
                    context, emit, llm, messages,
                    yield_reasoning=yield_reasoning,
                    thinking_mode=thinking_mode,
                    model_name=model_name,
                )
            else:
                return await self._execute_batch(
                    context, emit, llm, messages,
                    yield_reasoning=yield_reasoning,
                    thinking_mode=thinking_mode,
                    model_name=model_name,
                )

        except Exception as e:
            logger.exception(f"LLM error")
            await emit.emit_node_error(context.node_id, str(e))
            return NodeOutput({"response": f"错误: {str(e)}", "reasoning": ""},
                              trigger_next=False)

    async def execute_stream(self, context: NodeContext, emit: EventEmitter):
        """流式大模型生成，逐 chunk yield NodeOutput(final=False)，最后 yield NodeOutput(final=True)"""
        cfg = context.node_config

        if cfg.get("platform_id") and cfg.get("model_id"):
            effective = self._resolve_preset_config(cfg)
        else:
            effective = self._resolve_legacy_config(cfg)

        messages = context.inputs.get("llm") or context.inputs.get("messages") or []
        if not messages:
            messages = [{"role": "user", "content": "你好"}]

        images = context.inputs.get("image", []) or []
        if effective.get("vision") and images:
            messages = self._inject_images(messages, images, effective)

        llm = self._build_llm(effective)
        thinking_mode = effective.get("thinking_mode", "off")
        yield_reasoning = thinking_mode == "separate"
        model_name = effective.get("model", "")

        await emit.emit_node_update(
            context.node_id, "processing", "AI 思考中...",
            data={"mode": "thinking"},
        )

        full_content = ""
        full_reasoning = ""

        try:
            async for chunk in llm.chat_stream(messages):
                if chunk.content:
                    full_content += chunk.content
                if chunk.reasoning:
                    full_reasoning = chunk.reasoning

                disp_text, inline_think = self._parse_think(full_content)

                chunk_data = {
                    "mode": "generating",
                    "content_chunk": chunk.content,
                    "content_full": disp_text,
                }
                if yield_reasoning or full_reasoning:
                    chunk_data["reasoning"] = full_reasoning or inline_think
                elif inline_think:
                    chunk_data["reasoning"] = inline_think
                elif thinking_mode == "inline" and chunk.reasoning:
                    chunk_data["inline_reasoning"] = chunk.reasoning

                await emit.emit_node_update(
                    context.node_id, "processing",
                    f"生成中 ({len(disp_text)} 字)...",
                    progress=min(len(disp_text) / 500, 0.95),
                    data=chunk_data,
                )
                yield NodeOutput(chunk_data, final=False)

        except Exception:
            logger.exception("LLM streaming error")
            raise

        # 构造最终输出（复用 _finish 逻辑）
        clean_content, inline_think = self._parse_think(full_content)
        reasoning = full_reasoning or inline_think
        output_content = clean_content or full_content

        await emit.emit_node_complete(
            context.node_id, f"生成完成 ({len(output_content)} 字)",
            output_data={"content": output_content, "model": model_name,
                         **({"reasoning": reasoning} if reasoning else {})},
        )

        # 保存对话历史
        acc = context.accumulated_context
        if "llm_messages" not in acc:
            acc["llm_messages"] = []
        user_messages = [m for m in context.inputs.get("messages", [])
                         if m.get("role") == "user"]
        for um in user_messages:
            existing = any(
                m.get("role") == "user" and m.get("content") == um.get("content")
                for m in acc["llm_messages"]
            )
            if not existing:
                acc["llm_messages"].append(um)
        acc["llm_messages"].append({"role": "assistant", "content": output_content})
        if len(acc["llm_messages"]) > 20:
            acc["llm_messages"] = acc["llm_messages"][-20:]

        outputs = {
            "response": output_content,
            "raw": full_content,
            "model": model_name,
        }
        if reasoning:
            outputs["reasoning"] = reasoning

        yield NodeOutput(outputs, final=True)

    # ═══════════════════════════════════════════════════════
    # Internal helpers
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _resolve_preset_config(cfg: dict) -> dict:
        pm = get_preset_manager()
        try:
            effective = pm.get_effective_config(
                cfg["platform_id"], cfg["model_id"],
                cfg.get("overrides"),
            )
            logger.info(f"LLM effective config (preset match): api_key={'***' if effective.get('api_key') else 'EMPTY'}, "
                        f"base_url={effective.get('base_url')}, model={effective.get('model')}")
            return effective
        except (ValueError, KeyError) as e:
            # 预设 ID 不匹配 → 降级用第一个默认预设（保留用户配置的 api_key/base_url）
            logger.warning(f"Preset not found ({e}), falling back to default preset")
            data = pm.list_all()
            platforms = data.get("platforms", [])
            for p in platforms:
                models = p.get("models", [])
                if not models:
                    continue
                default_model = next((m for m in models if m.get("is_default")), models[0])
                if default_model:
                    effective = pm.get_effective_config(p["id"], default_model["id"], cfg.get("overrides"))
                    logger.info(f"LLM effective config (default fallback): api_key={'***' if effective.get('api_key') else 'EMPTY'}, "
                                f"base_url={effective.get('base_url')}, model={effective.get('model')}")
                    return effective
            # 最后的最后才降级 legacy
            logger.warning(f"No presets available, falling back to legacy .env config")
            return LLMNode._resolve_legacy_config(cfg)

    @staticmethod
    def _resolve_legacy_config(cfg: dict) -> dict:
        """旧格式兼容：node.config 直接存 model/temperature 等"""
        return {
            "provider": settings.llm_provider,
            "base_url": settings.openai_base_url,
            "api_key": settings.openai_api_key,
            "model": cfg.get("model", settings.openai_model),
            "reasoning_split": cfg.get("reasoning_split", settings.openai_reasoning_split),
            "thinking_mode": "separate" if cfg.get("reasoning_split", settings.openai_reasoning_split) else "off",
            "temperature": cfg.get("temperature"),
            "max_tokens": cfg.get("max_tokens"),
            "top_p": None,
            "streaming": cfg.get("streaming", True),
            "vision": False,
            "image_detail": "auto",
            "max_images": 4,
            "system_prompt": "",
            "max_context_tokens": 0,
            "response_format": "text",
            "stop": [],
            "extra": {},
        }

    @staticmethod
    def _build_llm(effective: dict):
        provider = LLMProvider(effective["provider"])
        llm_config = {
            "api_key": effective["api_key"],
            "base_url": effective["base_url"],
            "model": effective["model"],
            "reasoning_split": effective.get("reasoning_split", False),
            "temperature": effective.get("temperature"),
            "max_tokens": effective.get("max_tokens"),
            "top_p": effective.get("top_p"),
            "stop": effective.get("stop"),
            "response_format": effective.get("response_format"),
            "extra": effective.get("extra"),
        }
        return create_llm(provider, llm_config)

    @staticmethod
    def _inject_images(messages: list, images: list, effective: dict) -> list:
        """将图片注入最后一条 user message 的 content 中（多模态格式）"""
        max_images = effective.get("max_images", 4)
        detail = effective.get("image_detail", "auto")
        images = images[:max_images]

        # 找到最后一条 user message 的索引
        msgs = [dict(m) for m in messages]
        last_user_idx = -1
        for i in range(len(msgs) - 1, -1, -1):
            if msgs[i].get("role") == "user":
                last_user_idx = i
                break

        if last_user_idx < 0:
            return msgs

        user_msg = msgs[last_user_idx]
        text_content = user_msg.get("content", "")

        # 构建 OpenAI vision content array
        content = [{"type": "text", "text": text_content}]
        for img in images:
            if isinstance(img, dict):
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": img.get("url") or img.get("data", ""),
                        "detail": detail,
                    }
                })

        user_msg["content"] = content
        msgs[last_user_idx] = user_msg
        return msgs

    async def _execute_streaming(self, context, emit, llm, messages,
                                 yield_reasoning, thinking_mode, model_name=""):
        """流式执行"""
        full_content = ""
        full_reasoning = ""

        async for chunk in llm.chat_stream(messages):
            if chunk.content:
                full_content += chunk.content
            if chunk.reasoning:
                full_reasoning = chunk.reasoning

            # 流式显示时去除内嵌 <think> 标签
            disp_text, inline_think = self._parse_think(full_content)

            data = {
                "mode": "generating",
                "content_chunk": chunk.content,
                "content_full": disp_text,
            }
            if yield_reasoning or full_reasoning:
                data["reasoning"] = full_reasoning or inline_think
            elif inline_think:
                data["reasoning"] = inline_think
            elif thinking_mode == "inline" and chunk.reasoning:
                data["inline_reasoning"] = chunk.reasoning

            await emit.emit_node_update(
                context.node_id, "processing",
                f"生成中 ({len(disp_text)} 字)...",
                progress=min(len(disp_text) / 500, 0.95),
                data=data,
            )

        return await self._finish(context, emit, full_content, full_reasoning,
                                  yield_reasoning, model_name)

    async def _execute_batch(self, context, emit, llm, messages,
                             yield_reasoning, thinking_mode, model_name=""):
        """非流式执行"""
        await emit.emit_node_update(
            context.node_id, "processing", "AI 生成中...",
            data={"mode": "batch"},
        )

        result = await llm.chat(messages)
        full_content = result.content
        full_reasoning = result.reasoning

        return await self._finish(context, emit, full_content, full_reasoning,
                                  yield_reasoning, model_name)

    @staticmethod
    def _parse_think(content: str) -> tuple[str, str]:
        """从 content 中提取 <think>...</think> 标签内的思考内容。
        返回 (去除标签后的内容, 思考文本)"""
        if not content:
            return content, ""
        matches = _THINK_RE.findall(content)
        think_text = "\n\n".join(m.strip() for m in matches if m.strip())
        clean_content = _THINK_RE.sub("", content).strip()
        return clean_content, think_text

    async def _finish(self, context, emit, full_content, full_reasoning,
                      yield_reasoning, model_name=""):
        """完成处理，分离思考/输出，保存对话历史"""
        # 从 content 中解析内嵌的 <think> 标签
        clean_content, inline_think = self._parse_think(full_content)

        # 合并：已有的 reasoning（来自 reasoning_split）优先，否则用内嵌 think
        reasoning = full_reasoning or inline_think
        output_content = clean_content or full_content

        data = {"content": output_content, "model": model_name}
        if reasoning:
            data["reasoning"] = reasoning

        await emit.emit_node_update(
            context.node_id, "completed",
            f"生成完成 ({len(output_content)} 字)",
            data=data,
        )

        # 对话历史管理 — 用清洗后的内容存储
        acc = context.accumulated_context
        if "llm_messages" not in acc:
            acc["llm_messages"] = []

        user_messages = [m for m in context.inputs.get("messages", [])
                         if m.get("role") == "user"]
        for um in user_messages:
            existing = any(
                m.get("role") == "user" and m.get("content") == um.get("content")
                for m in acc["llm_messages"]
            )
            if not existing:
                acc["llm_messages"].append(um)

        acc["llm_messages"].append({
            "role": "assistant",
            "content": output_content,
        })
        if len(acc["llm_messages"]) > 20:
            acc["llm_messages"] = acc["llm_messages"][-20:]

        outputs = {
            "response": output_content,
            "raw": full_content,        # 原始完整内容（含 <think> 标签）
            "model": model_name,
        }
        if reasoning:
            outputs["reasoning"] = reasoning

        return NodeOutput(outputs)
