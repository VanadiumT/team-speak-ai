"""
Pipeline 定义模型

定义 Pipeline（功能页）和 Node（节点）的结构。
支持一次性节点（如 OCR）和后台监听节点（如 STT 监听）。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeType(Enum):
    """支持的节点类型"""
    INPUT_IMAGE = "input_image"       # 上传图片
    OCR = "ocr"                       # 图片识别
    STT_LISTEN = "stt_listen"         # TS 语音持续监听
    CONTEXT_BUILD = "context_build"   # 上下文合并
    LLM = "llm"                       # 大模型
    TTS = "tts"                       # 语音合成
    TS_OUTPUT = "ts_output"           # TS 播放


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
    type: str = "on_complete"          # "on_complete" | "on_keyword"
    source_node: str = ""              # 监听哪个节点
    keywords: list = field(default_factory=list)   # 关键词列表


@dataclass
class NodeDefinition:
    """节点定义"""
    id: str                            # 节点 ID, 如 "ocr_01"
    type: str                          # 节点类型, 如 "ocr"
    name: str                          # 显示名称
    config: dict = field(default_factory=dict)     # 节点配置
    input_mappings: list[InputMapping] = field(default_factory=list)  # 输入映射
    trigger: Optional[TriggerConfig] = None        # 触发条件
    listener: bool = False                         # 是否后台常驻节点


@dataclass
class PipelineDefinition:
    """Pipeline 定义"""
    id: str                            # 功能页 ID
    name: str                          # 显示名称
    group: str                          # 所属分组
    icon: str                           # 图标
    nodes: list[NodeDefinition] = field(default_factory=list)  # 节点列表
    skill_prompt: str = ""              # 技能提示词

    def get_node(self, node_id: str) -> Optional[NodeDefinition]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_listener_nodes(self) -> list[NodeDefinition]:
        """获取所有后台常驻节点"""
        return [n for n in self.nodes if n.listener]

    def get_action_nodes(self) -> list[NodeDefinition]:
        """获取所有非后台节点"""
        return [n for n in self.nodes if not n.listener]
