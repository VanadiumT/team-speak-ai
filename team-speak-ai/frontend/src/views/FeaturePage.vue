<template>
  <div class="feat-page" v-if="feature">
    <!-- 多行汇聚流程图 -->
    <PipelineView
      :nodes="feature.nodes"
      :active-node-id="activeNodeId"
      :skill-prompt="feature.config?.skill_prompt || ''"
      @select-node="activeNodeId = $event"
      @restart="handleRestart"
    />

    <!-- 动态操作面板 -->
    <DynamicPanel
      v-if="activeNode"
      :node="activeNode"
      :skill-prompt="feature.config?.skill_prompt || ''"
      @action="handlePanelAction"
    />
  </div>

  <!-- 空状态 -->
  <div class="feat-empty" v-else>
    <span class="fe-ico">🎯</span>
    <span class="fe-msg">从左侧选择功能</span>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { usePipelineStore } from '@/stores/pipeline'
import PipelineView from '@/components/pipeline/PipelineView.vue'
import DynamicPanel from '@/components/panels/DynamicPanel.vue'

const pipelineStore = usePipelineStore()
const props = defineProps({ featureId: { type: String, default: null } })

const activeNodeId = ref(null)

const feature = computed(() => props.featureId ? pipelineStore.features[props.featureId] || null : null)

const activeNode = computed(() => {
  const f = feature.value
  if (!f) return null
  if (activeNodeId.value) return f.nodes.find((n) => n.id === activeNodeId.value)
  const proc = f.nodes.find((n) => n.status === 'processing')
  if (proc) return proc
  return f.nodes.find((n) => n.type === 'input_image') || null
})

const handleRestart = () => { pipelineStore.restart(); activeNodeId.value = null }
const handlePanelAction = (action, payload) => {
  if (action === 'upload' && payload && activeNode.value?.id) {
    pipelineStore.uploadFile(activeNode.value.id, payload)
  }
}

watch(() => props.featureId, (nid, oid) => {
  if (oid) pipelineStore.unsubscribe(oid)
  if (nid) pipelineStore.subscribe(nid)
  activeNodeId.value = null
}, { immediate: true })
</script>

<style scoped>
.feat-page { padding: 0; }
.feat-empty {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  height: 200px; gap: 8px;
}
.fe-ico { font-size: 1.8rem; opacity: 0.25; }
.fe-msg { font-size: 0.85rem; color: rgba(255,255,255,0.2); }
</style>
