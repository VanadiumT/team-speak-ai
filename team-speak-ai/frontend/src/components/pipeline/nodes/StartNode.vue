<!--
  StartNode — 流程开始节点 body
-->
<template>
  <div class="start-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div v-if="status === 'completed'" class="start-done">
        <span class="material-symbols-outlined start-check">check_circle</span>
        <span class="start-label">已触发</span>
        <div v-if="paramsList.length > 0" class="start-params">
          <div v-for="item in paramsList" :key="item.key" class="start-param-row">
            <span class="sp-key">{{ item.key }}</span><span class="sp-eq">=</span><span class="sp-value">{{ item.value }}</span>
          </div>
        </div>
      </div>
      <div v-else-if="status === 'processing'" class="start-running">
        <span class="start-pulse"></span>
        <span>流程已启动</span>
      </div>
      <div v-else class="start-waiting">
        <span class="material-symbols-outlined" style="font-size: 14px; color: #64748b;">play_arrow</span>
        <span>{{ config?.auto_run !== false ? '等待启动...' : '等待手动启动...' }}</span>
      </div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <div class="start-config">
        <div class="start-config-field">
          <label class="start-field-label">自动运行</label>
          <label class="switch-toggle">
            <input type="checkbox" :checked="config?.auto_run !== false" @change="onAutoRunToggle" />
            <span class="switch-slider" />
          </label>
        </div>
        <div class="start-config-field">
          <label class="start-field-label">初始化参数</label>
          <div class="init-params-editor">
            <div v-if="paramsList.length === 0" class="init-params-empty">无参数</div>
            <div v-for="item in paramsList" :key="item.key" class="init-param-row">
              <input
                class="ip-key"
                :value="item.key"
                placeholder="key"
                @change="onParamKeyChange(item.key, $event.target.value)"
              />
              <span class="ip-arrow">→</span>
              <input
                class="ip-value"
                :value="item.value"
                placeholder="value"
                @change="onParamValueChange(item.key, $event.target.value)"
              />
              <button class="ip-remove" @click="removeParam(item.key)" title="删除">
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>
            <button class="ip-add" @click="addParam">
              <span class="material-symbols-outlined">add</span>
            </button>
          </div>
        </div>
      </div>
    </template>

    <template v-if="activeTab === 'io-data'">
      <NodeIODataView :node="node" :input-ports="inputPorts" :output-ports="outputPorts" />
    </template>

    <template v-if="activeTab === 'log'">
      <NodeLogView :logs="logs" />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEditorStore } from '@/stores/editor'
import NodeIODataView from './NodeIODataView.vue'
import NodeLogView from './NodeLogView.vue'

const props = defineProps({
  node: { type: Object, required: true },
  status: { type: String, default: 'pending' },
  activeTab: { type: String, default: 'detail' },
  editMode: { type: Boolean, default: false },
  data: { type: Object, default: () => ({}) },
  config: { type: Object, default: () => ({}) },
  logs: { type: Array, default: () => [] },
  outputPorts: { type: Array, default: () => [] },
})

const editorStore = useEditorStore()

const paramsList = computed(() => {
  const params = props.config?.init_params || props.data?.params || {}
  return Object.entries(params).map(([key, value]) => ({ key, value: String(value) }))
})

function updateInitParams(changed) {
  const current = { ...(props.config?.init_params || {}) }
  Object.assign(current, changed)
  // Remove keys set to undefined
  Object.keys(current).forEach(k => { if (current[k] === undefined) delete current[k] })
  editorStore.updateConfigImmediate(props.node.id, { init_params: current })
}

function onAutoRunToggle(e) {
  editorStore.updateConfigImmediate(props.node.id, { auto_run: e.target.checked })
}

function addParam() {
  const key = `param_${Date.now()}`
  updateInitParams({ [key]: '' })
}

function onParamKeyChange(oldKey, newKey) {
  newKey = newKey.trim()
  if (!newKey || oldKey === newKey) return
  const current = { ...(props.config?.init_params || {}) }
  const value = current[oldKey]
  current[newKey] = value
  delete current[oldKey]
  editorStore.updateConfigImmediate(props.node.id, { init_params: current })
}

function onParamValueChange(key, newValue) {
  updateInitParams({ [key]: newValue })
}

function removeParam(key) {
  updateInitParams({ [key]: undefined })
}
</script>

<style scoped>
.start-body { padding: 4px 0; }

.start-waiting {
  display: flex; align-items: center; gap: 6px;
  padding: 8px; font-size: 11px; color: #64748b;
}
.start-running {
  display: flex; align-items: center; gap: 6px;
  padding: 8px; font-size: 11px; color: #4edea3;
}
.start-pulse {
  width: 8px; height: 8px; border-radius: 50%;
  background: #4edea3; animation: start-pulse 1.2s ease-in-out infinite;
}
@keyframes start-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.4); }
}

.start-done {
  display: flex; flex-direction: column; gap: 4px;
  padding: 6px 8px; font-size: 11px;
}
.start-check { font-size: 16px; color: #4edea3; }
.start-label { color: #4edea3; font-weight: 600; }

.start-params { margin-top: 2px; }
.start-param-row {
  display: flex; align-items: center; gap: 3px;
  font-size: 10px; font-family: 'Space Grotesk', monospace;
}
.sp-key { color: #adc7ff; }
.sp-eq { color: #64748b; }
.sp-value { color: #8b90a0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 120px; }

/* ── Config ── */
.start-config { display: flex; flex-direction: column; gap: 10px; }
.start-config-field { display: flex; flex-direction: column; gap: 4px; }
.start-field-label {
  font-size: 10px; font-weight: 500; color: #8b90a0;
  font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; letter-spacing: 0.05em;
}

.switch-toggle {
  position: relative; display: inline-block; width: 40px; height: 22px; cursor: pointer;
}
.switch-toggle input { opacity: 0; width: 0; height: 0; }
.switch-slider {
  position: absolute; inset: 0; background: #31353d; border-radius: 11px; transition: background 0.2s;
}
.switch-slider::before {
  content: ''; position: absolute; width: 16px; height: 16px;
  left: 3px; top: 3px; background: #8b90a0; border-radius: 50%; transition: transform 0.2s, background 0.2s;
}
.switch-toggle input:checked + .switch-slider { background: rgba(173, 199, 255, 0.3); }
.switch-toggle input:checked + .switch-slider::before { transform: translateX(18px); background: #adc7ff; }

.init-params-editor { display: flex; flex-direction: column; gap: 4px; }
.init-params-empty { font-size: 10px; color: #64748b; padding: 4px 0; }
.init-param-row { display: flex; align-items: center; gap: 4px; }
.ip-key, .ip-value {
  flex: 1; min-width: 0; height: 26px; padding: 0 6px; border-radius: 4px;
  border: 1px solid #31353d; background: #1a1e2e;
  color: #c1c6d7; font-size: 10px; font-family: 'Space Grotesk', monospace;
  outline: none; box-sizing: border-box;
}
.ip-key:focus, .ip-value:focus { border-color: #adc7ff; }
.ip-key { color: #adc7ff; }
.ip-arrow { color: #64748b; font-size: 10px; }
.ip-remove {
  display: flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 3px; flex-shrink: 0;
  border: none; background: transparent; color: #64748b; cursor: pointer;
}
.ip-remove:hover { color: #ffb4ab; }
.ip-remove .material-symbols-outlined { font-size: 12px; }
.ip-add {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 4px; align-self: flex-start;
  border: 1px solid #414754; background: transparent; color: #8b90a0; cursor: pointer;
}
.ip-add:hover { border-color: #4edea3; color: #4edea3; }
.ip-add .material-symbols-outlined { font-size: 14px; }
</style>
