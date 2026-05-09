/**
 * Node Component Registry
 *
 * 按 node.type 加载 Vue 组件。后端决定类型+状态，前端决定渲染方式。
 * 使用方式: registry[type] → Component
 */
import InputImageNode from './InputImageNode.vue'
import OcrNode from './OcrNode.vue'
import STTListenNode from './STTListenNode.vue'
import STTHistoryNode from './STTHistoryNode.vue'
import ContextBuildNode from './ContextBuildNode.vue'
import LLMNode from './LLMNode.vue'
import TTSNode from './TTSNode.vue'
import TSOutputNode from './TSOutputNode.vue'
import TSInputNode from './TSInputNode.vue'

export const nodeComponentRegistry = {
  input_image: InputImageNode,
  ocr: OcrNode,
  stt_listen: STTListenNode,
  stt_history: STTHistoryNode,
  context_build: ContextBuildNode,
  llm: LLMNode,
  tts: TTSNode,
  ts_output: TSOutputNode,
  ts_input: TSInputNode,
}

/**
 * Get component for node type.
 * Returns null if no custom component registered — caller should use NodeCard default body.
 */
export function getNodeComponent(nodeType) {
  return nodeComponentRegistry[nodeType] || null
}
