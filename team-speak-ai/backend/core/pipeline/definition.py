"""
Pipeline 定义模型

定义 Pipeline（功能页）和 Node（节点）的结构。
支持一次性节点（如 OCR）和后台监听节点（如 STT 监听）。

扩展了 NodeTypeDef / PortDef / ConnectionDef / FlowSummary 等完整元数据模型，
供 WebSocket 协议中的 node_types 下发和流程编辑使用。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union


class NodeType(Enum):
    """支持的节点类型"""
    INPUT_IMAGE = "input_image"       # 上传图片
    OCR = "ocr"                       # 图片识别
    STT_LISTEN = "stt_listen"         # TS 语音持续监听
    STT_HISTORY = "stt_history"       # STT 历史记录 + 关键词判断
    CONTEXT_BUILD = "context_build"   # 上下文合并
    LLM = "llm"                       # 大模型
    TTS = "tts"                       # 语音合成
    TS_OUTPUT = "ts_output"           # TS 播放


# ── 端口与 Tab 元数据 ──────────────────────────────────────────

@dataclass
class TabDef:
    """节点标签页定义"""
    id: str         # "config" | "detail" | "log" | "fulltext"
    label: str      # "配置" | "详情" | "日志" | "全文"


@dataclass
class PortPosition:
    """端口在节点卡片上的渲染位置"""
    side: str       # "left" (输入) 或 "right" (输出)
    top: int        # 距节点卡片顶部的像素偏移


@dataclass
class PortDef:
    """单个端口定义"""
    id: str                 # 端口标识符, e.g. "img-out", "ocr-in"
    label: str              # 悬停提示文字
    data_type: str          # "image" | "audio" | "string" | "string_array" | "messages" | "event"
    position: PortPosition  # 渲染位置


@dataclass
class PortsDef:
    """节点的输入/输出端口集合"""
    inputs: list[PortDef] = field(default_factory=list)
    outputs: list[PortDef] = field(default_factory=list)


@dataclass
class NodeTypeDef:
    """节点类型完整元数据 —— 后端下发，前端据此渲染节点"""
    type: str                       # 节点类型标识符, e.g. "ocr"
    name: str                       # 显示名, e.g. "OCR 识别"
    icon: str                       # Material Symbols 图标名
    color: str                      # 主题色: "primary" / "secondary" / "tertiary" / "outline"
    default_config: dict = field(default_factory=dict)   # 创建新节点时的初始配置
    tabs: list[TabDef] = field(default_factory=list)     # 节点内标签页列表
    ports: PortsDef = field(default_factory=PortsDef)    # 输入/输出端口定义


# ── 流程 / 节点 / 连线数据模型 ─────────────────────────────────

@dataclass
class InputMapping:
    """上游输入映射"""
    from_node: str          # 上游节点 ID
    as_field: str           # 当前节点 inputs 中的字段名
    source_field: str = ""  # 上游输出中的字段名（默认同 as_field）
    required: bool = True   # 是否必须


@dataclass
class TriggerConfig:
    """触发条件配置"""
    type: str = "on_complete"             # "on_complete" | "on_keyword"
    source_node: str = ""                 # 监听哪个节点
    keywords: list = field(default_factory=list)   # 关键词列表


@dataclass
class NodeDefinition:
    """节点定义（实例）"""
    id: str                            # 节点 ID, 如 "ocr_01"
    type: str                          # 节点类型, 如 "ocr"
    name: str                          # 显示名称
    position: dict = field(default_factory=lambda: {"x": 0, "y": 0})   # 画布坐标
    config: dict = field(default_factory=dict)          # 节点配置
    input_mappings: list[InputMapping] = field(default_factory=list)   # 输入映射
    trigger: Optional[TriggerConfig] = None             # 触发条件
    listener: bool = False                              # 是否后台常驻节点


@dataclass
class ConnectionDef:
    """连线定义"""
    id: str                     # 连线 ID, e.g. "conn_img_to_ocr"
    from_node: str              # 源节点 ID
    from_port: str              # 源端口 ID
    to_node: str                # 目标节点 ID
    to_port: str                # 目标端口 ID
    type: str = "data"          # "data" | "event" | "trigger"


@dataclass
class FlowSummary:
    """流程摘要 —— flow.list 返回"""
    id: str
    name: str
    group: str = ""
    icon: str = "account_tree"
    node_count: int = 0
    enabled: bool = True
    updated_at: str = ""        # ISO 8601 时间戳


@dataclass
class PipelineDefinition:
    """Pipeline / Flow 完整定义"""
    id: str                            # 功能页 ID
    name: str                          # 显示名称
    group: str = ""                    # 所属分组
    icon: str = "account_tree"         # 图标
    enabled: bool = True               # 是否启用
    skill_prompt: str = ""             # 技能提示词
    canvas: dict = field(default_factory=lambda: {"width": 1700, "height": 1250})   # 画布尺寸
    nodes: list[NodeDefinition] = field(default_factory=list)                        # 节点列表
    connections: list[ConnectionDef] = field(default_factory=list)                   # 连线列表

    def get_node(self, node_id: str) -> Optional[NodeDefinition]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_connection(self, connection_id: str) -> Optional[ConnectionDef]:
        for c in self.connections:
            if c.id == connection_id:
                return c
        return None

    def get_listener_nodes(self) -> list[NodeDefinition]:
        """获取所有后台常驻节点"""
        return [n for n in self.nodes if n.listener]

    def get_action_nodes(self) -> list[NodeDefinition]:
        """获取所有非后台节点"""
        return [n for n in self.nodes if not n.listener]


# ── 侧栏树结构 ─────────────────────────────────────────────────

@dataclass
class SidebarNode:
    """侧栏树节点"""
    id: str                              # 节点 ID
    name: str                            # 显示名
    icon: str = "folder"                 # Material Symbols 图标
    type: str = "group"                  # "section" | "group" | "flow_ref" | "action"
    flow_id: Optional[str] = None        # type="flow_ref" 时的 flow ID
    enabled: bool = True                 # type="flow_ref" 时的启用状态
    children: list["SidebarNode"] = field(default_factory=list)
