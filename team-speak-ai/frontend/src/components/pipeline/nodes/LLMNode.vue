<template>
  <div class="llm-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span class="mode-badge">{{ isStreaming ? '流式' : '非流式' }}</span>
        <span class="model-tag">{{ displayModelName }}</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待上游上下文...</div>

      <!-- ═══ 思考过程面板 ═══ -->
      <div v-if="hasReasoning" class="thinking-panel" :class="{ collapsed: thinkingCollapsed }">
        <div class="thinking-header" @click="thinkingCollapsed = !thinkingCollapsed">
          <span class="thinking-dot"></span>
          <span class="thinking-title">思考过程</span>
          <span class="thinking-chars">{{ reasoningText.length }} 字</span>
          <span class="thinking-toggle">{{ thinkingCollapsed ? '展开' : '收起' }}</span>
        </div>
        <div v-show="!thinkingCollapsed" class="thinking-body" v-html="reasoningHtml || '<span class=thinking-empty>思考中...</span>'"></div>
      </div>

      <!-- ═══ 输出面板 ═══ -->
      <div v-if="status === 'processing'" class="output-panel">
        <div class="output-header">
          <span class="output-label">输出</span>
          <span v-if="isStreaming" class="output-chars">{{ outputText.length }} 字</span>
        </div>
        <template v-if="isStreaming">
          <div class="mini-bar-wrap">
            <div class="mini-bar"><div class="mini-bar-fill" :style="{ width: (progress ?? 0) * 100 + '%' }" /></div>
          </div>
          <div class="output-content" v-html="streamHtml || '<span class=output-placeholder>生成中...</span>'"></div>
          <span class="stream-cursor">█</span>
        </template>
        <template v-else>
          <div class="output-content batch-wrap">
            <span class="batch-spin"></span>
            <span class="batch-label">非流式生成中...</span>
          </div>
        </template>
      </div>

      <div v-if="status === 'completed'" class="output-panel completed">
        <div class="output-header">
          <span class="output-label">输出</span>
          <span class="output-chars">{{ outputText.length }} 字</span>
        </div>
        <div class="output-content" v-html="finalHtml"></div>
      </div>

      <div v-if="status === 'completed'" class="llm-meta">
        <span v-if="data?.model">模型: {{ data.model }}</span>
        <span class="trigger-hint">→ 触发下游</span>
      </div>

      <div v-if="status === 'error'" class="error-text">{{ summary || 'LLM 调用失败' }}</div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <div class="llm-config">
        <div class="cfg-field">
          <label class="cfg-label">模型</label>
          <select class="cfg-select" :value="selectedModelKey" @change="onModelChange">
            <option v-if="!selectedModelKey" value="" disabled>选择模型...</option>
            <option v-for="m in presetsStore.allModels" :key="m.platformId + '/' + m.modelId"
                    :value="m.platformId + '/' + m.modelId">
              {{ m.label }}
            </option>
          </select>
        </div>

        <details class="cfg-overrides">
          <summary class="cfg-summary">覆盖预设值 (可选)</summary>
          <div class="cfg-field">
            <label class="cfg-label">Temperature <span class="cfg-hint">(预设: {{ currentModelInfo?.temperature ?? '-' }})</span></label>
            <input class="cfg-input" type="number" :value="overrideVal('temperature')" @change="onOverride('temperature', $event.target.value)"
                   min="0" max="2" step="0.05" :placeholder="String(currentModelInfo?.temperature ?? '')" />
          </div>
          <div class="cfg-field">
            <label class="cfg-label">Max Tokens <span class="cfg-hint">(预设: {{ currentModelInfo?.maxTokens ?? '-' }})</span></label>
            <input class="cfg-input" type="number" :value="overrideVal('max_tokens')" @change="onOverride('max_tokens', $event.target.value)"
                   min="64" max="32768" :placeholder="String(currentModelInfo?.maxTokens ?? '')" />
          </div>
          <div class="cfg-field">
            <label class="cfg-label">System Prompt <span class="cfg-hint">(预设: {{ systemPromptPreview }})</span></label>
            <textarea class="cfg-input cfg-textarea" :value="overrideVal('system_prompt')" @change="onOverride('system_prompt', $event.target.value)"
                      rows="2" placeholder="留空=使用预设" />
          </div>
          <div class="cfg-field">
            <label class="cfg-label cfg-check-label" @click="onOverride('streaming', isStreaming ? false : true)">
              <input type="checkbox" :checked="isStreaming" @change="onOverride('streaming', $event.target.checked)" />
              流式输出 <span class="cfg-hint">(预设: {{ currentModelInfo?.streaming !== false ? '流式' : '非流式' }})</span>
            </label>
          </div>
        </details>
      </div>
    </template>

    <template v-if="activeTab === 'io-data'">
      <NodeIODataView :node="node" :input-ports="inputPorts" :output-ports="outputPorts" />
    </template>
    <template v-if="activeTab === 'io-mgmt' && editMode">
      <NodeIOMgmt :node="node" :edit-mode="editMode" :input-ports="inputPorts" :output-ports="outputPorts" @toggle-port="onTogglePort" />
    </template>
    <template v-if="activeTab === 'log'">
      <NodeLogView :logs="logs" />
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { usePresetsStore } from '@/stores/presets'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import NodeIODataView from './NodeIODataView.vue'
import NodeIOMgmt from './NodeIOMgmt.vue'
import NodeLogView from './NodeLogView.vue'

// ── Markdown 渲染 ──
marked.setOptions({ breaks: true, gfm: true })
function renderMd(text) {
  if (!text) return ''
  try { return DOMPurify.sanitize(marked.parse(text)) } catch { return text.replace(/</g, '&lt;') }
}

// ── Mermaid 懒加载 ──
let _mermaid = null
async function loadMermaid() {
  if (_mermaid !== null) return _mermaid
  try {
    const mod = await import('mermaid')
    _mermaid = mod.default || mod
    _mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      themeVariables: {
        primaryColor: '#adc7ff',
        primaryTextColor: '#e0e2ed',
        primaryBorderColor: '#4a8eff',
        lineColor: '#8b90a0',
        secondaryColor: '#1c2027',
        tertiaryColor: '#10131b',
        fontSize: '12px',
      },
    })
  } catch (e) {
    console.warn('[LLMNode] mermaid 加载失败:', e)
    _mermaid = false
  }
  return _mermaid || null
}

async function renderWithMermaid(text) {
  if (!text) return ''
  const html = renderMd(text)
  if (!html.includes('language-mermaid')) return html

  const m = await loadMermaid()
  if (!m) return html

  const container = document.createElement('div')
  container.innerHTML = html
  const blocks = container.querySelectorAll('pre code.language-mermaid')
  for (const block of blocks) {
    try {
      const code = block.textContent || ''
      const id = 'm-' + Math.random().toString(36).slice(2, 8)
      const { svg } = await m.render(id, code)
      const wrapper = document.createElement('div')
      wrapper.className = 'mermaid-diagram'
      wrapper.innerHTML = DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true } })
      const pre = block.closest('pre')
      if (pre) pre.replaceWith(wrapper)
    } catch {
      const pre = block.closest('pre')
      if (pre) pre.classList.add('mermaid-error')
    }
  }
  return container.innerHTML
}

const props = defineProps({
  node: { type: Object, required: true },
  status: { type: String, default: 'pending' },
  activeTab: { type: String, default: 'detail' },
  editMode: { type: Boolean, default: false },
  summary: { type: String, default: '' },
  progress: { type: Number, default: null },
  data: { type: Object, default: () => ({}) },
  config: { type: Object, default: () => ({}) },
  logs: { type: Array, default: () => [] },
  inputPorts: { type: Array, default: () => [] },
  outputPorts: { type: Array, default: () => [] }
})

const editorStore = useEditorStore()
const presetsStore = usePresetsStore()

const thinkingCollapsed = ref(false)

const statusLabel = computed(() => {
  const map = { pending: '等待中', processing: '生成中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

// ── 模型配置 ──
const selectedModelKey = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return `${cfg.platform_id}/${cfg.model_id}`
  return ''
})

const currentModelInfo = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return presetsStore.getModelInfo(cfg.platform_id, cfg.model_id)
  return null
})

const displayModelName = computed(() => {
  const cfg = props.config || props.node?.config || {}
  if (cfg.platform_id && cfg.model_id) return presetsStore.getLabel(cfg.platform_id, cfg.model_id)
  return cfg.model || 'gpt-4-turbo'
})

const isStreaming = computed(() => {
  const cfg = props.config || props.node?.config || {}
  const ov = cfg.overrides || {}
  if ('streaming' in ov) return !!ov.streaming
  return currentModelInfo.value?.streaming !== false
})
const systemPromptPreview = computed(() => {
  const sp = currentModelInfo.value?.systemPrompt
  return sp ? sp.slice(0, 30) + '...' : '(空)'
})

// ── 输出数据 ──
const outputText = computed(() => {
  const d = props.data || {}
  if (d.content_full) return d.content_full
  if (d.content) return d.content
  if (d.response) return d.response
  return ''
})

const reasoningText = computed(() => (props.data || {}).reasoning || '')

const hasReasoning = computed(() =>
  (props.status === 'processing' || props.status === 'completed') && !!reasoningText.value
)

// ── 渲染 ──
const reasoningHtml = ref('')
const streamHtml = ref('')
const finalHtml = ref('')

watch(reasoningText, (val) => {
  reasoningHtml.value = val ? renderMd(val) : ''
})

watch(outputText, (val) => {
  if (!val) { streamHtml.value = ''; finalHtml.value = ''; return }
  if (props.status === 'completed') {
    renderWithMermaid(val).then(h => { finalHtml.value = h })
  } else {
    streamHtml.value = renderMd(val)
  }
})

watch(() => props.status, (s) => {
  if (s === 'completed' && outputText.value) {
    renderWithMermaid(outputText.value).then(h => { finalHtml.value = h })
  }
})

// ── Config helpers ──
function overrideVal(key) {
  const cfg = props.config || props.node?.config || {}
  const ov = cfg.overrides || {}
  return ov[key] != null ? ov[key] : ''
}

function onOverride(key, rawVal) {
  const cfg = props.config || props.node?.config || {}
  const overrides = { ...(cfg.overrides || {}) }
  let val
  if (rawVal === '' || rawVal === undefined) {
    val = undefined
  } else if (key === 'streaming') {
    val = Boolean(rawVal)
  } else if (key === 'system_prompt') {
    val = rawVal
  } else {
    val = parseFloat(rawVal)
  }
  if (val === undefined || (typeof val === 'number' && isNaN(val))) {
    delete overrides[key]
  } else {
    overrides[key] = val
  }
  editorStore.updateConfigImmediate(props.node.id, { ...cfg, overrides })
}

function onModelChange(e) {
  const [platformId, modelId] = e.target.value.split('/')
  const cfg = props.config || props.node?.config || {}
  editorStore.updateConfigImmediate(props.node.id, {
    platform_id: platformId,
    model_id: modelId,
    overrides: cfg.overrides || {},
  })
  const info = presetsStore.getModelInfo(platformId, modelId)
  if (info) {
    const vis = new Set(props.node.config?._visible_ports || [])
    if (info.vision) vis.add('image-in'); else vis.delete('image-in')
    if (info.thinkingMode !== 'off') vis.add('meta-reasoning'); else vis.delete('meta-reasoning')
    editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
  }
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}
</script>

<style scoped>
.llm-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.status-dot.pending { background: #8b90a0; }
.status-dot.processing { background: #4a8eff; animation: pulse 0.8s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
.model-tag {
  font-size: 8px; font-family: 'Space Grotesk', sans-serif;
  color: #adc7ff; background: rgba(173,199,255,0.08); padding: 1px 5px; border-radius: 9999px;
  max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mode-badge {
  font-size: 8px; padding: 1px 5px; border-radius: 9999px; margin-left: auto;
  background: rgba(78,222,163,0.1); color: #4edea3;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }

/* ── 思考过程面板 ── */
.thinking-panel {
  border: 1px solid rgba(255,182,149,0.2);
  border-radius: 4px; margin-bottom: 6px; overflow: hidden;
  background: rgba(255,182,149,0.03);
}
.thinking-header {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 8px; cursor: pointer; user-select: none;
  transition: background 0.1s;
}
.thinking-header:hover { background: rgba(255,182,149,0.05); }
.thinking-dot {
  width: 5px; height: 5px; border-radius: 50%; background: #ffb695; flex-shrink: 0;
  animation: pulse 1.2s infinite;
}
.thinking-title {
  font-size: 10px; color: #ffb695; font-weight: 500;
  font-family: 'Space Grotesk', sans-serif; letter-spacing: 0.03em;
}
.thinking-chars {
  font-size: 8px; color: rgba(255,182,149,0.4); margin-left: auto;
}
.thinking-toggle {
  font-size: 8px; color: rgba(255,182,149,0.35);
}
.thinking-body {
  padding: 4px 8px 6px; font-size: 10px; color: rgba(255,182,149,0.8);
  line-height: 1.4; max-height: 120px; overflow-y: auto;
  border-top: 1px solid rgba(255,182,149,0.08);
}
.thinking-body :deep(p) { margin: 0 0 3px; }
.thinking-body :deep(code) {
  background: rgba(255,182,149,0.06); padding: 0 3px; border-radius: 2px;
  font-size: 9px;
}
.thinking-body :deep(pre) {
  background: rgba(0,0,0,0.25); padding: 3px 6px; border-radius: 3px;
  font-size: 8px; overflow-x: auto; margin: 3px 0;
}
.thinking-empty { color: rgba(255,182,149,0.3); }

/* ── 输出面板 ── */
.output-panel {
  border: 1px solid rgba(78,222,163,0.15);
  border-radius: 4px; overflow: hidden;
  background: rgba(78,222,163,0.02);
}
.output-panel.completed {
  border-color: rgba(78,222,163,0.2);
}
.output-header {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 8px;
  border-bottom: 1px solid rgba(78,222,163,0.08);
}
.output-label {
  font-size: 10px; color: #4edea3; font-weight: 500;
  font-family: 'Space Grotesk', sans-serif; letter-spacing: 0.03em;
}
.output-chars {
  font-size: 8px; color: rgba(78,222,163,0.4); margin-left: auto;
}
.output-content {
  padding: 6px 8px; font-size: 11px; color: #e0e2ed; line-height: 1.55;
  max-height: 220px; overflow-y: auto;
}
.output-content :deep(p) { margin: 0 0 5px; }
.output-content :deep(ul), .output-content :deep(ol) { margin: 3px 0; padding-left: 16px; }
.output-content :deep(li) { margin-bottom: 2px; }
.output-content :deep(code) {
  background: rgba(173,199,255,0.08); padding: 1px 5px; border-radius: 3px;
  font-size: 10px; font-family: 'Space Grotesk', monospace;
}
.output-content :deep(pre) {
  background: #10131b; padding: 6px 10px; border-radius: 5px;
  border: 1px solid #31353d; font-size: 10px; overflow-x: auto;
  margin: 5px 0; font-family: 'Space Grotesk', monospace;
}
.output-content :deep(pre.mermaid-error) {
  border-color: rgba(255,180,171,0.3);
}
.output-content :deep(strong) { color: #fff; }
.output-content :deep(h1), .output-content :deep(h2), .output-content :deep(h3) {
  font-size: 12px; margin: 6px 0 3px; color: #fff;
}
.output-content :deep(blockquote) {
  border-left: 2px solid #4a8eff; padding-left: 8px;
  color: #8b90a0; margin: 4px 0; font-style: italic;
}
.output-content :deep(.mermaid-diagram) {
  display: flex; justify-content: center; padding: 8px 0;
  overflow-x: auto;
}
.output-content :deep(.mermaid-diagram svg) { max-width: 100%; }
.output-placeholder { color: #64748b; }
.stream-cursor { color: #4a8eff; animation: blink 0.8s step-end infinite; }
@keyframes blink { 0%,50% { opacity: 1; } 51%,100% { opacity: 0; } }

.mini-bar-wrap { padding: 2px 8px 0; }
.mini-bar { height: 2px; background: #31353d; border-radius: 1px; overflow: hidden; }
.mini-bar-fill { height: 100%; background: #4a8eff; border-radius: 1px; transition: width 0.3s; }

.batch-wrap { padding: 8px; }
.batch-spin {
  display: inline-block; width: 10px; height: 10px;
  border: 2px solid rgba(255,182,149,0.2); border-top-color: #ffb695;
  border-radius: 50%; animation: spin 0.8s linear infinite;
  vertical-align: middle; margin-right: 5px;
}
.batch-label { font-size: 10px; color: #ffb695; vertical-align: middle; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Meta ── */
.llm-meta {
  display: flex; gap: 6px; font-size: 8px; color: #64748b;
  font-family: 'Space Grotesk', sans-serif; margin-top: 2px;
}
.trigger-hint { color: #4a8eff; }

/* ── Config Tab ── */
.llm-config { padding: 4px 0; }
.cfg-field { margin-bottom: 8px; }
.cfg-label { display: block; font-size: 10px; color: #8b90a0; margin-bottom: 3px; }
.cfg-hint { font-size: 8px; color: #64748b; }
.cfg-select, .cfg-input {
  width: 100%; padding: 5px 8px; font-size: 11px;
  background: #10131b; border: 1px solid #31353d; border-radius: 4px;
  color: #e0e2ed; font-family: inherit; outline: none;
}
.cfg-select:focus, .cfg-input:focus { border-color: #4a8eff; }
.cfg-textarea { resize: vertical; min-height: 40px; }
.cfg-check-label { display: flex !important; align-items: center; gap: 6px; cursor: pointer; }
.cfg-check-label input { width: auto; }
.cfg-overrides { margin-top: 10px; }
.cfg-summary {
  font-size: 10px; color: #adc7ff; cursor: pointer; padding: 4px 0;
  border-bottom: 1px solid rgba(65,71,84,0.2); margin-bottom: 8px;
}
</style>
