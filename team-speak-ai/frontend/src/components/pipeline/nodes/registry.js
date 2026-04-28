/**
 * Node Component Registry
 *
 * 按 node.type 懒加载 Vue 组件。后端决定类型+状态，前端决定渲染方式。
 * 使用方式: registry[type] → AsyncComponent
 */

// 现阶段使用 NodeCard.vue 的 slot 机制渲染 body，
// 复杂节点可在后续扩展为独立组件。
export const nodeComponentRegistry = {
  input_image: null,   // → InputImageNode.vue
  ocr: null,           // → OcrNode.vue
  stt_listen: null,    // → STTListenNode.vue
  stt_history: null,   // → STTHistoryNode.vue
  context_build: null, // → ContextBuildNode.vue
  llm: null,           // → LLMNode.vue
  tts: null,           // → TTSNode.vue
  ts_output: null,     // → TSOutputNode.vue
}

/**
 * Get component for node type.
 * Returns null if no custom component registered — caller should use NodeCard default body.
 */
export function getNodeComponent(nodeType) {
  return nodeComponentRegistry[nodeType] || null
}
