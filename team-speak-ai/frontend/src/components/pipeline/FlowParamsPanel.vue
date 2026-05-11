<!--
  FlowParamsPanel — 流程参数编辑面板
  编辑模式下显示，管理当前流程的 key-value 参数。
-->
<template>
  <div class="flow-params-panel" ref="panelEl">
    <div class="fpp-header">
      <span class="material-symbols-outlined fpp-icon">tune</span>
      <span class="fpp-title">流程参数</span>
      <button v-if="editorStore.editMode" class="fpp-add-btn" @click="addParam" title="添加参数">
        <span class="material-symbols-outlined">add</span>
      </button>
    </div>

    <div v-if="paramList.length === 0" class="fpp-empty">
      {{ editorStore.editMode ? '暂无参数，点击 + 添加' : '暂无参数' }}
    </div>

    <template v-for="(item, idx) in paramList" :key="item.key">
      <div v-if="idx > 0" class="fpp-sep"></div>
      <div class="fpp-row">
        <div class="fpp-row-inner">
          <div class="fpp-key-line">
            <textarea
              class="fpp-key"
              :value="item.key"
              placeholder="key"
              rows="1"
              :disabled="!editorStore.editMode"
              @input="onInput"
              @change="onKeyChange(item.key, $event.target.value)"
              data-fpp-textarea
            />
            <button v-if="editorStore.editMode" class="fpp-copy-btn" @click="copyRef('$param.' + item.key)" :title="copied === '$param.' + item.key ? '已复制 $param.' + item.key : '复制引用'">
              <span class="material-symbols-outlined">{{ copied === '$param.' + item.key ? 'check' : 'content_copy' }}</span>
            </button>
          </div>
          <textarea
            class="fpp-value"
            :value="item.value"
            placeholder="value"
            rows="1"
            @input="onInput"
            @change="onValueChange(item.key, $event.target.value)"
            data-fpp-textarea
          />
        </div>
        <button v-if="editorStore.editMode" class="fpp-del-btn" @click="removeParam(item.key)" title="删除">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    </template>

    <div v-if="paramList.length > 0" class="fpp-footer">
      <span class="fpp-count">{{ paramList.length }} 个参数</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick, onMounted } from 'vue'
import { useEditorStore } from '@/stores/editor'

const editorStore = useEditorStore()
const copied = ref('')
const panelEl = ref(null)

async function copyRef(refStr) {
  try {
    await navigator.clipboard.writeText(refStr)
    copied.value = refStr
    setTimeout(() => { copied.value = '' }, 2000)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = refStr; ta.style.position = 'fixed'; ta.style.opacity = '0'
    document.body.appendChild(ta); ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = refStr
    setTimeout(() => { copied.value = '' }, 2000)
  }
}

const paramList = computed(() =>
  Object.entries(editorStore.flowParams).map(([key, value]) => ({ key, value: String(value) }))
)

function addParam() {
  const key = `param_${Date.now()}`
  editorStore.updateFlowParams({ [key]: '' })
}

function autoResize(el) {
  el.style.height = 'auto'
  el.style.height = Math.max(el.scrollHeight, 26) + 'px'
}

function resizeAll() {
  if (!panelEl.value) return
  panelEl.value.querySelectorAll('[data-fpp-textarea]').forEach(autoResize)
}

function onInput(ev) {
  autoResize(ev.target)
}

onMounted(() => nextTick(resizeAll))
watch(paramList, () => nextTick(resizeAll), { deep: true })

async function onKeyChange(oldKey, newKey) {
  newKey = newKey.trim()
  if (!newKey || oldKey === newKey) return
  if (newKey in editorStore.flowParams) return
  const value = editorStore.flowParams[oldKey]
  await editorStore.deleteFlowParam(oldKey)
  await editorStore.updateFlowParams({ [newKey]: value })
}

async function onValueChange(key, newValue) {
  editorStore.updateFlowParams({ [key]: newValue })
}

async function removeParam(key) {
  editorStore.deleteFlowParam(key)
}
</script>

<style scoped>
.flow-params-panel {
  padding: 6px 8px;
  border: 1px solid #2a2e39;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
}

.fpp-header {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 6px;
}
.fpp-icon { font-size: 14px; color: #adc7ff; }
.fpp-title { font-size: 11px; font-weight: 600; color: #c1c6d7; flex: 1; }
.fpp-add-btn {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 4px;
  border: 1px solid #414754; background: transparent; color: #8b90a0;
  cursor: pointer; transition: all 0.15s;
}
.fpp-add-btn:hover { border-color: #4edea3; color: #4edea3; }
.fpp-add-btn .material-symbols-outlined { font-size: 13px; }

.fpp-empty {
  text-align: center; padding: 10px 0;
  font-size: 11px; color: #64748b;
}

/* ── Separator ── */
.fpp-sep {
  height: 1px; margin: 6px 0;
  background: rgba(65, 71, 84, 0.25);
}

/* ── Row ── */
.fpp-row {
  display: flex; gap: 4px; align-items: flex-start;
}
.fpp-row-inner {
  flex: 1; display: flex; flex-direction: column; gap: 3px; min-width: 0;
}

/* ── Key line: key input + ref inline ── */
.fpp-key-line {
  display: flex; align-items: center; gap: 4px;
}
.fpp-key {
  flex: 1; min-width: 0;
  padding: 3px 5px; border-radius: 4px;
  border: 1px solid #31353d; background: #1a1e2e;
  color: #adc7ff; font-size: 11px;
  font-family: 'Space Grotesk', monospace;
  outline: none; resize: none; overflow: hidden;
  transition: border-color 0.15s;
  line-height: 1.4; box-sizing: border-box;
}
.fpp-key:focus { border-color: #adc7ff; }
.fpp-key:disabled { opacity: 0.6; cursor: default; }

/* ── Copy button ── */
.fpp-copy-btn {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 3px; flex-shrink: 0;
  border: none; background: transparent; color: #64748b;
  cursor: pointer; transition: all 0.15s;
}
.fpp-copy-btn:hover { background: rgba(78, 222, 163, 0.12); color: #4edea3; }
.fpp-copy-btn .material-symbols-outlined { font-size: 13px; }

/* ── Value ── */
.fpp-value {
  width: 100%; padding: 3px 5px; border-radius: 4px;
  border: 1px solid #31353d; background: #1a1e2e;
  color: #c1c6d7; font-size: 11px;
  font-family: 'Space Grotesk', monospace;
  outline: none; resize: none; overflow: hidden;
  transition: border-color 0.15s;
  line-height: 1.4; box-sizing: border-box;
}
.fpp-value:focus { border-color: #adc7ff; }
.fpp-value:disabled { opacity: 0.6; cursor: default; }

.fpp-del-btn {
  display: flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 3px; margin-top: 3px;
  border: none; background: transparent; color: #64748b;
  cursor: pointer; transition: color 0.15s; flex-shrink: 0;
}
.fpp-del-btn:hover { color: #ffb4ab; }
.fpp-del-btn .material-symbols-outlined { font-size: 12px; }

.fpp-footer {
  margin-top: 4px; text-align: right;
}
.fpp-count { font-size: 9px; color: #64748b; }
</style>
