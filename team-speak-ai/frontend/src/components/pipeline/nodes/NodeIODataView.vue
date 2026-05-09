<template>
  <div class="io-data-view">
    <div v-if="!hasAnyData" class="io-empty">暂无 IO 数据</div>

    <!-- 输入端口 -->
    <div v-if="inputRows.length" class="io-side">
      <div class="io-side-label">输入</div>
      <div v-for="row in inputRows" :key="row.port.id" class="io-entry">
        <div class="io-entry-header">
          <span class="io-port-name">{{ row.port.id }}</span>
          <span class="io-port-type">{{ row.port.data_type }}</span>
          <span v-if="row.sourceName" class="io-source">← {{ row.sourceName }}</span>
          <span v-else class="io-source io-unused">未连接</span>
        </div>
        <div v-if="row.hasValue" class="io-entry-value" :class="{ 'io-pre': row.pre }">{{ row.displayValue }}</div>
      </div>
    </div>

    <!-- 输出端口 -->
    <div v-if="outputRows.length" class="io-side">
      <div class="io-side-label">输出</div>
      <div v-for="row in outputRows" :key="row.port.id" class="io-entry">
        <div class="io-entry-header">
          <span class="io-port-name">{{ row.port.id }}</span>
          <span class="io-port-type">{{ row.port.data_type }}</span>
          <span v-if="row.targetNames.length" class="io-target">→ {{ row.targetNames.join(', ') }}</span>
          <span v-else class="io-target io-unused">未连接</span>
        </div>
        <div v-if="row.hasValue" class="io-entry-value" :class="{ 'io-pre': row.pre }">{{ row.displayValue }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps({
  node: { type: Object, required: true },
  inputPorts: { type: Array, default: () => [] },
  outputPorts: { type: Array, default: () => [] },
})

const editorStore = useEditorStore()
const execStore = useExecutionStore()

// Map node_id → name for quick lookup
const nodeNameMap = computed(() => {
  const m = {}
  editorStore.nodes.forEach(n => { m[n.id] = n.name })
  return m
})

// Connections indexed by target (input side) and source (output side)
const connsByTarget = computed(() => {
  const m = {}
  editorStore.connections.forEach(c => {
    const key = `${c.to_node}:${c.to_port}`
    if (!m[key]) m[key] = []
    m[key].push(c)
  })
  return m
})

const connsBySource = computed(() => {
  const m = {}
  editorStore.connections.forEach(c => {
    const key = `${c.from_node}:${c.from_port}`
    if (!m[key]) m[key] = []
    m[key].push(c)
  })
  return m
})

function getSourceRuntime(fromNodeId, fromPortId) {
  const rt = execStore.getNodeStatus(fromNodeId)
  if (!rt || !rt.data) return null
  return rt.data
}

function formatValue(v) {
  if (v === null || v === undefined) return null
  if (typeof v === 'object') return JSON.stringify(v, null, 1)
  return String(v)
}

const inputRows = computed(() => {
  return props.inputPorts.map(port => {
    const key = `${props.node.id}:${port.id}`
    const conns = connsByTarget.value[key] || []
    const sourceName = conns.length > 0 ? nodeNameMap.value[conns[0].from_node] || conns[0].from_node : null

    let displayValue = null
    if (conns.length > 0) {
      const rt = getSourceRuntime(conns[0].from_node, conns[0].from_port)
      if (rt) {
        const val = rt[conns[0].from_port] ?? rt.value ?? rt.text ?? rt
        displayValue = formatValue(val)
      }
    }

    return {
      port,
      sourceName,
      displayValue,
      hasValue: displayValue !== null,
      pre: displayValue !== null && displayValue.length > 80,
    }
  })
})

const outputRows = computed(() => {
  return props.outputPorts.map(port => {
    const key = `${props.node.id}:${port.id}`
    const conns = connsBySource.value[key] || []
    const targetNames = conns.map(c => nodeNameMap.value[c.to_node] || c.to_node)

    // Get this node's own runtime data
    const rt = execStore.getNodeStatus(props.node.id)
    let displayValue = null
    if (rt && rt.data) {
      const val = rt.data[port.id] ?? rt.data.value ?? rt.data.text ?? rt.data
      displayValue = formatValue(val)
    }

    return {
      port,
      targetNames,
      displayValue,
      hasValue: displayValue !== null,
      pre: displayValue !== null && displayValue.length > 80,
    }
  })
})

const hasAnyData = computed(() =>
  inputRows.value.some(r => r.hasValue || r.sourceName) ||
  outputRows.value.some(r => r.hasValue || r.targetNames.length > 0)
)
</script>

<style scoped>
.io-data-view { display: flex; flex-direction: column; gap: 8px; }
.io-empty { font-size: 10px; color: #64748b; text-align: center; padding: 12px 0; }

.io-side { }
.io-side-label {
  font-size: 9px; color: #8b90a0; text-transform: uppercase;
  letter-spacing: 0.06em; font-family: 'Space Grotesk', sans-serif;
  padding-bottom: 2px; border-bottom: 1px solid rgba(65,71,84,0.3);
  margin-bottom: 4px;
}
.io-entry { padding: 2px 0; }
.io-entry-header {
  display: flex; align-items: center; gap: 4px; flex-wrap: wrap;
}
.io-port-name {
  font-size: 10px; color: #c1c6d7; font-weight: 500;
  font-family: 'Space Grotesk', sans-serif;
}
.io-port-type {
  font-size: 8px; color: #64748b; font-family: 'Space Grotesk', sans-serif;
}
.io-source { font-size: 9px; color: #4a8eff; }
.io-target { font-size: 9px; color: #4edea3; }
.io-unused { color: #414754; }
.io-entry-value {
  font-size: 10px; color: #e0e2ed; margin-top: 2px;
  padding: 3px 6px; background: rgba(11,14,22,0.6); border-radius: 3px;
  word-break: break-all; line-height: 1.4; max-height: 80px; overflow-y: auto;
}
.io-entry-value.io-pre {
  font-family: 'Space Grotesk', sans-serif; font-size: 9px;
}
</style>
