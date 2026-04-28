"""
节点类型注册表

维护 node_type → NodeClass 的映射，并提供完整的 NodeTypeDef 元数据
供 WebSocket 连接建立时下发给前端。
"""

from typing import Type

from core.pipeline.definition import (
    NodeTypeDef, TabDef, PortDef, PortsDef, PortPosition,
)


# ── 节点类型元数据注册（独立于类注册，stt_history 无对应类也要注册） ──

_TYPE_METADATA: dict[str, NodeTypeDef] = {}


def _build_metadata():
    """构建所有节点类型的元数据。在模块加载时调用一次。"""

    def port(side: str, top: int, id_: str, label: str, data_type: str) -> PortDef:
        return PortDef(id=id_, label=label, data_type=data_type,
                       position=PortPosition(side=side, top=top))

    metadata = [
        NodeTypeDef(
            type="input_image", name="上传图片", icon="upload_file", color="secondary",
            default_config={"accepted_formats": ["png", "jpg", "webp"], "max_size_mb": 10},
            tabs=[],
            ports=PortsDef(
                inputs=[],
                outputs=[
                    port("right", 30, "img-out", "图片数据 (PNG/JPG)", "image"),
                    port("right", 72, "trigger-out", "触发信号", "event"),
                ],
            ),
        ),
        NodeTypeDef(
            type="ocr", name="OCR 识别", icon="document_scanner", color="secondary",
            default_config={"engine": "easyocr", "language": ["zh"], "confidence_threshold": 0.3},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[port("left", 30, "ocr-in", "图片 (PNG/JPG)", "image")],
                outputs=[port("right", 55, "ocr-out", "OCR文本 (String)", "string")],
            ),
        ),
        NodeTypeDef(
            type="stt_listen", name="STT 持续监听", icon="mic_external_on", color="primary",
            default_config={"engine": "sensevoice", "keywords": ["求助", "集合", "撤退"], "sample_rate": 16000},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="log", label="日志"),
                TabDef(id="fulltext", label="全文"),
            ],
            ports=PortsDef(
                inputs=[port("left", 30, "stt-in", "音频帧 (PCM 16bit)", "audio")],
                outputs=[port("right", 55, "stt-out", "识别文本 (String)", "string")],
            ),
        ),
        NodeTypeDef(
            type="stt_history", name="STT History · 关键词判断", icon="history_edu", color="tertiary",
            default_config={"max_entries": 20, "context_window": 128000},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[port("left", 30, "hist-in", "文本片段 (String)", "string")],
                outputs=[
                    port("right", 72, "hist-out", "stt_history (String[])", "string_array"),
                    port("right", 110, "hist-trigger", "触发信号 (Keyword)", "event"),
                ],
            ),
        ),
        NodeTypeDef(
            type="context_build", name="ContextBuild", icon="hub", color="primary",
            default_config={"max_context_length": 4096},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "ctx-in1", "skill_prompt (String)", "string"),
                    port("left", 58, "ctx-in2", "OCR文本 (String)", "string"),
                    port("left", 86, "ctx-in3", "stt_history (String[])", "string_array"),
                    port("left", 114, "ctx-in4", "对话历史 (String[])", "string_array"),
                ],
                outputs=[port("right", 55, "ctx-out", "组合上下文 (Messages[])", "messages")],
            ),
        ),
        NodeTypeDef(
            type="llm", name="LLM 生成", icon="smart_toy", color="primary",
            default_config={"model": "gpt-4-turbo", "temperature": 0.7, "max_tokens": 2048},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[port("left", 30, "llm-in", "组合上下文 (Messages[])", "messages")],
                outputs=[port("right", 55, "llm-out", "流式文本 (String)", "string")],
            ),
        ),
        NodeTypeDef(
            type="tts", name="TTS 合成", icon="record_voice_over", color="outline",
            default_config={"engine": "edge", "voice": "zh-CN-YunxiNeural", "speed": 1.0},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[port("left", 30, "tts-in", "文本 (String)", "string")],
                outputs=[port("right", 55, "tts-out", "合成音频 (WAV)", "audio")],
            ),
        ),
        NodeTypeDef(
            type="ts_output", name="TS 音频输出", icon="volume_up", color="secondary",
            default_config={"mode": "segment"},
            tabs=[],
            ports=PortsDef(
                inputs=[port("left", 30, "out-in", "音频数据 (WAV)", "audio")],
                outputs=[port("right", 72, "out-done", "播放完成信号", "event")],
            ),
        ),
    ]

    for m in metadata:
        _TYPE_METADATA[m.type] = m


_build_metadata()


class NodeRegistry:
    """节点注册表：type → NodeClass 映射"""

    _registry: dict[str, Type] = {}

    @classmethod
    def register(cls, node_type: str):
        """装饰器，注册节点类"""
        def decorator(node_cls):
            cls._registry[node_type] = node_cls
            return node_cls
        return decorator

    @classmethod
    def create(cls, node_type: str, config: dict) -> Type:
        """创建节点实例"""
        node_cls = cls._registry.get(node_type)
        if not node_cls:
            raise ValueError(f"Unknown node type: {node_type}")
        return node_cls(config)

    @classmethod
    def list_types(cls) -> list[str]:
        return list(cls._registry.keys())

    # ── 新增：类型元数据查询 ──

    @classmethod
    def get_type_def(cls, node_type: str) -> NodeTypeDef:
        """获取单个节点类型的完整元数据"""
        if node_type not in _TYPE_METADATA:
            raise ValueError(f"Unknown node type: {node_type}")
        return _TYPE_METADATA[node_type]

    @classmethod
    def list_type_defs(cls) -> list[NodeTypeDef]:
        """返回所有已注册节点类型的完整元数据列表"""
        return list(_TYPE_METADATA.values())
