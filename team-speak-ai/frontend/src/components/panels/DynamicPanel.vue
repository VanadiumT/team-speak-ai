<template>
  <div class="dp" v-if="node">
    <!-- Header -->
    <div class="dp-head">
      <span class="material-symbols-outlined dp-icon">{{ nodeIcon }}</span>
      <span class="dp-name">{{ node.name || node.type }}</span>
      <button class="dp-close" @click="$emit('close')">
        <span class="material-symbols-outlined">close</span>
      </button>
    </div>

    <!-- Tab bar -->
    <div v-if="tabs.length > 0" class="dp-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="detail-tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >{{ tab.label }}</button>
    </div>

    <!-- Tab content -->
    <div class="dp-body">
      <!-- Detail tab: status-based rendering -->
      <div v-if="activeTab === 'detail' || tabs.length === 0">
        <!-- Pending -->
        <div v-if="nodeStatus === 'pending'" class="dp-state dp-pending">
          <span class="material-symbols-outlined dp-state-icon">schedule</span>
          <span>等待上游节点完成...</span>
        </div>

        <!-- Processing -->
        <div v-else-if="nodeStatus === 'processing'" class="dp-state dp-processing">
          <div class="dp-spin"></div>
          <span>{{ nodeState.summary || '处理中...' }}</span>
        </div>

        <!-- Completed -->
        <div v-else-if="nodeStatus === 'completed'" class="dp-done">
          <span class="material-symbols-outlined dp-ok">check_circle</span>
          <span>已完成</span>
          <div v-if="nodeState.summary" class="dp-summary">{{ nodeState.summary }}</div>
        </div>

        <!-- Error -->
        <div v-else-if="nodeStatus === 'error'" class="dp-err">
          <span>错误</span>
        </div>

        <!-- Listening -->
        <div v-else-if="nodeStatus === 'listening'" class="dp-state dp-listening">
          <span class="material-symbols-outlined dp-state-icon animate-pulse">mic</span>
          <span>监听中...</span>
        </div>
      </div>

      <!-- Config tab -->
      <div v-if="activeTab === 'config'" class="dp-config">
        <div v-if="node.config" class="config-grid">
          <div v-for="(val, key) in node.config" :key="key" class="config-row">
            <span class="config-key">{{ key }}</span>
            <span class="config-val">{{ formatConfigVal(val) }}</span>
          </div>
        </div>
        <div v-else class="dp-state dp-pending">无配置</div>
      </div>

      <!-- Log tab -->
      <div v-if="activeTab === 'log'" class="dp-log">
        <div v-if="nodeLogs.length === 0" class="dp-empty-log">暂无日志</div>
        <div v-for="(log, i) in nodeLogs" :key="i" class="log-line" :class="'log-' + log.level" :style="{ animation: log.highlight ? 'pulse 0.5s 2' : 'none' }">
          <span class="log-time">[{{ log.timestamp }}]</span>
          <span class="log-msg">{{ log.message }}</span>
        </div>
      </div>

      <!-- Fulltext tab -->
      <div v-if="activeTab === 'fulltext'" class="dp-fulltext">
        <div class="fulltext-content">{{ nodeState.data?.text || '无全文数据' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useEditorStore } from '@/stores/editor.js'
import { useExecutionStore } from '@/stores/execution.js'

const props = defineProps({
  node: { type: Object, default: null },
})

defineEmits(['close'])

const editorStore = useEditorStore()
const executionStore = useExecutionStore()

const activeTab = ref('detail')

// Reset tab when node changes
watch(() => props.node?.id, () => {
  activeTab.value = 'detail'
})

const nodeTypeDef = computed(() =>
  editorStore.nodeTypes.find((t) => t.type === props.node?.type)
)

const tabs = computed(() => nodeTypeDef.value?.tabs || [])

const nodeIcon = computed(() => nodeTypeDef.value?.icon || 'smart_toy')

const nodeState = computed(() =>
  props.node ? executionStore.getNodeStatus(props.node.id) : { status: 'pending' }
)

const nodeStatus = computed(() => nodeState.value.status)

const nodeLogs = computed(() =>
  props.node ? executionStore.getNodeLogs(props.node.id, 50) : []
)

function formatConfigVal(val) {
  if (Array.isArray(val)) return val.join(', ')
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}
</script>

<style scoped>
.dp {
  display: flex; flex-direction: column;
  height: 100%;
}

.dp-head {
  display: flex; align-items: center; gap: 8px;
  padding: 16px;
  border-bottom: 1px solid rgba(65, 71, 84, 0.5);
  flex-shrink: 0;
}

.dp-icon { font-size: 20px; color: #adc7ff; }
.dp-name { flex: 1; font-size: 16px; font-weight: 600; color: #e0e2ed; }

.dp-close {
  color: #8b90a0; background: none; border: none;
  cursor: pointer; padding: 4px;
}
.dp-close:hover { color: #e0e2ed; }

/* Tabs */
.dp-tabs {
  display: flex; border-bottom: 1px solid rgba(65, 71, 84, 0.5);
  flex-shrink: 0;
}

.detail-tab-btn {
  flex: 1; padding: 8px 0; text-align: center;
  font-size: 11px; font-family: 'Space Grotesk', sans-serif;
  letter-spacing: 0.05em; font-weight: 500;
  color: #8b90a0; cursor: pointer;
  transition: color 0.2s; border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
}

.detail-tab-btn:hover { color: #c1c6d7; }

.detail-tab-btn.active {
  color: #adc7ff;
  border-bottom-color: #adc7ff;
}

/* Body */
.dp-body { flex: 1; overflow-y: auto; padding: 16px; }

/* States */
.dp-state {
  display: flex; align-items: center; gap: 8px;
  padding: 24px 0; font-size: 13px;
  color: #c1c6d7;
}

.dp-state-icon { font-size: 20px; }

.dp-pending { color: #8b90a0; }
.dp-processing { color: #adc7ff; }
.dp-listening { color: #adc7ff; }

.dp-spin {
  width: 16px; height: 16px;
  border: 2px solid rgba(173, 199, 255, 0.15);
  border-top-color: #adc7ff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.dp-done {
  padding: 24px 0;
  display: flex; flex-direction: column;
  align-items: center; gap: 8px;
  color: #4edea3; font-size: 14px;
}

.dp-ok { font-size: 32px; }

.dp-summary {
  font-size: 12px; color: #c1c6d7;
  text-align: center; margin-top: 8px;
  padding: 8px; background: rgba(11, 14, 22, 0.5);
  border-radius: 4px; width: 100%;
}

.dp-err {
  text-align: center; padding: 24px 0;
  color: #ffb4ab; font-size: 13px;
}

/* Config */
.config-grid { display: flex; flex-direction: column; gap: 8px; }

.config-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid rgba(65, 71, 84, 0.2);
}

.config-key {
  font-size: 11px; color: #8b90a0;
  font-family: 'Space Grotesk', sans-serif;
}

.config-val {
  font-size: 11px; color: #adc7ff;
  font-family: 'Space Grotesk', sans-serif;
  max-width: 180px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}

/* Log */
.dp-log {
  font-size: 10px; font-family: 'Space Grotesk', sans-serif;
  display: flex; flex-direction: column; gap: 4px;
}

.dp-empty-log { color: #64748b; text-align: center; padding: 24px; }

.log-line { display: flex; gap: 6px; }

.log-time { color: #64748b; flex-shrink: 0; }

.log-muted .log-msg { color: #64748b; }
.log-info .log-msg { color: #adc7ff; }
.log-success .log-msg { color: #4edea3; }
.log-warn .log-msg { color: #ef6719; }
.log-error .log-msg { color: #ffb4ab; }

/* Fulltext */
.dp-fulltext { padding: 4px 0; }

.fulltext-content {
  font-size: 11px; color: #c1c6d7;
  font-family: 'Space Grotesk', sans-serif;
  line-height: 1.6; white-space: pre-wrap;
  padding: 8px; background: rgba(11, 14, 22, 0.5);
  border-radius: 4px;
}
</style>
