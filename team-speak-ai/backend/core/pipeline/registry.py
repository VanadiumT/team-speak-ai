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

    def port(side: str, top: int, id_: str, label: str, data_type: str, visibility: str = "always",
             repeatable: bool = False, group: str = None, min: int = None, max: int = None) -> PortDef:
        return PortDef(id=id_, label=label, data_type=data_type,
                       position=PortPosition(side=side, top=top), visibility=visibility,
                       repeatable=repeatable, group=group, min=min, max=max)

    _on = "on-demand"  # shorthand for on-demand ports

    metadata = [
        NodeTypeDef(
            type="start", name="开始", icon="play_arrow", color="secondary",
            default_config={"auto_run": True, "init_params": {}},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[],
                outputs=[
                    port("right", 30, "event-out", "启动信号", "event"),
                    port("right", 72, "data-out", "初始数据", "any", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="input_image", name="上传图片", icon="upload_file", color="secondary",
            default_config={"accepted_formats": ["png", "jpg", "webp"], "max_size_mb": 10, "notify_on_reach": True},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 55, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "img-out", "图片数据 (PNG/JPG)", "image"),
                    port("right", 72, "trigger-out", "触发信号", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="text_input", name="文本输入", icon="edit_note", color="secondary",
            default_config={"text": "", "mode": "static", "notify_on_reach": True},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "text-in", "文本输入 (String)", "string", _on),
                    port("left", 68, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "text-out", "文本输出 (String)", "string"),
                    port("right", 68, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="ocr", name="OCR 识别", icon="document_scanner", color="secondary",
            default_config={"engine": "easyocr", "language": ["zh"], "confidence_threshold": 0.3},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "ocr-in", "图片 (PNG/JPG)", "image"),
                    port("left", 68, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "ocr-out", "OCR文本 (String)", "string"),
                    port("right", 68, "done", "完成", "event", _on),
                    port("right", 106, "line-count", "识别行数", "number", _on),
                    port("right", 144, "provider", "识别引擎", "string", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="stt_listen", name="STT合成", icon="mic_external_on", color="primary",
            default_config={"platform_id": "", "model_id": "", "overrides": {}},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "stream-audio-in", "流式音频 (Audio)", "audio"),
                    port("left", 56, "batch-audio-in", "非流式音频 (Audio)", "audio"),
                    port("left", 82, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "stream-text-out", "流式-识别文本 (String)", "string"),
                    port("right", 56, "batch-text-out", "非流式-完整文本 (String)", "string"),
                    port("right", 82, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="stt_history", name="STT History · 关键词判断", icon="history_edu", color="tertiary",
            default_config={"max_entries": 20, "context_window": 128000},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "hist-in", "文本片段 (String)", "string"),
                    port("left", 68, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "hist-out", "stt_history (String[])", "string_array"),
                    port("right", 68, "hist-trigger", "触发信号 (Keyword)", "event"),
                    port("right", 106, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="context_build", name="上下文构建器", icon="account_tree", color="primary",
            default_config={
                "max_context_length": 4096,
                "_repeatable_ports": {"ctx": []},
                "_port_labels": {},
            },
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "system-in", "系统提示词 (String)", "string", _on),
                    port("left", 58, "chat-in", "历史对话 (Messages[])", "messages", _on),
                    port("left", 86, "req-in", "用户提示词", "string", "always"),
                    port("left", 114, "ctx-in1", "信息1", "string", _on,
                         repeatable=True, group="ctx", min=0, max=20),
                    port("left", 142, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 55, "ctx-out", "组合上下文 (Messages[])", "messages"),
                    port("right", 93, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="llm", name="LLM 生成", icon="smart_toy", color="primary",
            default_config={"platform_id": "", "model_id": "", "overrides": {}},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "llm-in", "组合上下文 (Messages[])", "messages"),
                    port("left", 68, "trigger-in", "触发", "event", _on),
                    port("left", 106, "image-in", "图片输入 (Image[])", "image", _on),
                ],
                outputs=[
                    # 流式输出
                    port("right", 30, "stream-text-out", "流式-纯文本(拆分) (String)", "string"),
                    port("right", 56, "stream-think-out", "流式-思考过程(拆分) (String)", "string", _on),
                    port("right", 82, "stream-raw-out", "流式-完整输出(含思考) (String)", "string", _on),
                    # 非流式输出
                    port("right", 108, "batch-text-out", "非流式-纯文本(拆分) (String)", "string"),
                    port("right", 134, "batch-think-out", "非流式-思考过程(拆分) (String)", "string", _on),
                    port("right", 160, "batch-raw-out", "非流式-完整输出(含思考) (String)", "string", _on),
                    # 元数据
                    port("right", 186, "done", "完成", "event", _on),
                    port("right", 212, "meta-token-count", "Token 消耗", "number", _on),
                    port("right", 238, "meta-model", "模型名", "string", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="tts", name="TTS 合成", icon="record_voice_over", color="primary",
            default_config={"platform_id": "", "model_id": "", "overrides": {}},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "stream-text-in", "流式-文本(拆分) (String)", "string"),
                    port("left", 56, "batch-text-in", "非流式-文本 (String)", "string"),
                    port("left", 82, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "stream-audio-out", "流式-音频(拆分) (Audio)", "audio"),
                    port("right", 56, "batch-audio-out", "非流式-完整音频 (Audio)", "audio"),
                    port("right", 82, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="ts_output", name="TS 音频输出", icon="volume_up", color="secondary",
            default_config={"platform_id": "", "model_id": "", "overrides": {}},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 22, "stream-audio-in", "流式音频 (分段)", "audio", _on),
                    port("left", 44, "batch-audio-in", "完整音频 (WAV/PCM)", "audio", _on),
                    port("left", 66, "trigger-in", "触发", "event", _on),
                ],
                outputs=[port("right", 66, "done", "播放完成", "event", _on)],
            ),
        ),
        NodeTypeDef(
            type="ts_input", name="TS 音频输入", icon="headset_mic", color="secondary",
            default_config={"max_buffer_bytes": 10485760, "sample_rate": 16000, "channels": 1, "loopback": False},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 55, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "stream-pcm-out", "音频流 (PCM)", "audio"),
                    port("right", 72, "trigger-out", "触发信号", "event"),
                ],
            ),
        ),
        NodeTypeDef(
            type="vad", name="VAD分句", icon="voice_selection", color="primary",
            default_config={"platform_id": "", "model_id": "", "overrides": {}},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "stream-audio-in", "流式音频 (Audio)", "audio"),
                    port("left", 72, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "stream-chunk-out", "分句音频 (Audio)", "audio"),
                    port("right", 68, "trigger-out", "分句触发", "event"),
                    port("right", 106, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="display_text", name="文本显示", icon="text_fields", color="primary",
            default_config={"text": "", "mode": "passthrough"},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "text-in", "文本输入 (String)", "string", _on),
                    port("left", 68, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "text-out", "文本输出 (String)", "string"),
                    port("right", 68, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="flow_var_read", name="读取流程参数", icon="input", color="primary",
            default_config={"key": "", "default_value": ""},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 55, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "data-out", "参数值", "string"),
                    port("right", 68, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="flow_var_write", name="写入流程参数", icon="output", color="primary",
            default_config={"key": "", "merge_mode": "overwrite"},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "data-in", "待写入值", "string"),
                    port("left", 68, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "data-out", "写入值 (透传)", "string"),
                    port("right", 68, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="sys_var_read", name="读取系统变量", icon="settings_input", color="tertiary",
            default_config={"key": "", "default_value": ""},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 55, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "data-out", "变量值", "string"),
                    port("right", 68, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="sys_var_write", name="写入系统变量", icon="settings_output", color="tertiary",
            default_config={"key": "", "merge_mode": "overwrite"},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 30, "data-in", "待写入值", "string"),
                    port("left", 68, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 30, "data-out", "写入值 (透传)", "string"),
                    port("right", 68, "done", "完成", "event", _on),
                ],
            ),
        ),
        NodeTypeDef(
            type="audio_player", name="音频播放", icon="volume_up", color="secondary",
            default_config={"volume": 1.0, "auto_play": True},
            tabs=[
                TabDef(id="config", label="配置"),
                TabDef(id="detail", label="详情"),
                TabDef(id="io-data", label="IO数据"),
                TabDef(id="io-mgmt", label="IO管理"),
                TabDef(id="log", label="日志"),
            ],
            ports=PortsDef(
                inputs=[
                    port("left", 22, "stream-audio-in", "流式音频 (分段)", "audio", _on),
                    port("left", 44, "batch-audio-in", "完整音频 (WAV/PCM)", "audio", _on),
                    port("left", 66, "trigger-in", "触发", "event", _on),
                ],
                outputs=[
                    port("right", 22, "stream-audio-out", "流式透传", "audio", _on),
                    port("right", 44, "batch-audio-out", "完整透传", "audio", _on),
                    port("right", 66, "done", "播放完成", "event", _on),
                ],
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
