<template>
  <div class="audio-player-body">
    <template v-if="!editMode || activeTab === 'detail'">
      <div class="status-row">
        <span class="status-dot" :class="status" />
        <span class="status-text">{{ statusLabel }}</span>
        <span class="model-tag">音频播放</span>
      </div>

      <div v-if="status === 'pending'" class="hint-text">等待音频...</div>

      <div v-if="status === 'processing'" class="proc-info">
        <span class="material-symbols-outlined proc-icon">graphic_eq</span>
        <span>{{ summary || '播放中...' }}</span>
      </div>

      <div v-if="status === 'completed'" class="done-info">
        <span class="material-symbols-outlined done-icon">check_circle</span>
        <span>{{ audioInfoText }}</span>
      </div>

      <div v-if="status === 'error'" class="error-text">{{ summary || '播放失败' }}</div>

      <div v-if="hasAudio" class="action-bar">
        <button class="action-btn" :class="{ active: isPlaying }" @click="togglePlay" :title="isPlaying ? '暂停' : '播放'">
          <span class="material-symbols-outlined">{{ isPlaying ? 'pause' : 'play_arrow' }}</span>
        </button>
        <button class="action-btn" @click="downloadAudio" title="下载音频">
          <span class="material-symbols-outlined">download</span>
        </button>
      </div>
    </template>

    <template v-if="editMode && activeTab === 'config'">
      <div class="ap-config">
        <div class="cfg-field">
          <label class="cfg-label">音量</label>
          <input type="range" min="0" max="2" step="0.1" class="cfg-range"
                 :value="cfgVolume" @input="onVolume" />
          <span class="cfg-range-val">{{ cfgVolume }}x</span>
        </div>
        <div class="cfg-field cfg-check">
          <label class="cfg-label">自动播放</label>
          <input type="checkbox" :checked="cfgAutoPlay" @change="onAutoPlay" />
        </div>
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
import NodeIODataView from './NodeIODataView.vue'
import NodeIOMgmt from './NodeIOMgmt.vue'
import NodeLogView from './NodeLogView.vue'

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

const statusLabel = computed(() => {
  const map = { pending: '等待中', processing: '播放中', completed: '已完成', error: '错误' }
  return map[props.status] || props.status
})

// ── 配置 ──
const cfgVolume = computed(() => {
  const v = (props.config || props.node?.config || {}).volume
  return v != null ? v : 1.0
})
const cfgAutoPlay = computed(() => {
  const v = (props.config || props.node?.config || {}).auto_play
  return v !== false
})

function onVolume(e) {
  const cfg = props.config || props.node?.config || {}
  editorStore.updateConfigImmediate(props.node.id, { ...cfg, volume: parseFloat(e.target.value) })
}
function onAutoPlay(e) {
  const cfg = props.config || props.node?.config || {}
  editorStore.updateConfigImmediate(props.node.id, { ...cfg, auto_play: e.target.checked })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}

// ── 音频数据解析 ──
const hasAudio = computed(() => {
  const d = props.data || {}
  if (d.audio_b64) return true
  if (d.segments && d.segments.length > 0) return true
  return false
})

const audioInfoText = computed(() => {
  const d = props.data || {}
  if (d.mode === 'stream') {
    return `${d.total || 0} 段`
  }
  if (d.size) {
    if (d.size > 1048576) return (d.size / 1048576).toFixed(1) + ' MB'
    if (d.size > 1024) return (d.size / 1024).toFixed(1) + ' KB'
    return d.size + ' B'
  }
  return ''
})

// ── 获取当前可播放的 audio_b64 ──
function getAudioB64() {
  const d = props.data || {}
  if (d.audio_b64) return d.audio_b64
  if (d.segments && d.segments.length > 0) {
    return d.segments.map(s => s.audio_b64 || '').filter(Boolean).join('')
  }
  return ''
}

// ── Web Audio 播放 ──
const isPlaying = ref(false)
let audioCtx = null
let currentSource = null

function base64ToArrayBuffer(b64) {
  const binary = atob(b64)
  const len = binary.length
  const bytes = new Uint8Array(len)
  for (let i = 0; i < len; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

async function playAudio() {
  const b64 = getAudioB64()
  if (!b64) return

  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    }
    const buffer = base64ToArrayBuffer(b64)
    const audioBuffer = await audioCtx.decodeAudioData(buffer)

    if (currentSource) {
      try { currentSource.stop() } catch (_) { /* ignore */ }
    }

    currentSource = audioCtx.createBufferSource()
    currentSource.buffer = audioBuffer

    const gainNode = audioCtx.createGain()
    gainNode.gain.value = cfgVolume.value
    currentSource.connect(gainNode)
    gainNode.connect(audioCtx.destination)

    currentSource.onended = () => {
      isPlaying.value = false
    }

    currentSource.start(0)
    isPlaying.value = true
  } catch (e) {
    console.warn('AudioPlayer: decode failed', e)
    isPlaying.value = false
  }
}

function stopAudio() {
  if (currentSource) {
    try { currentSource.stop() } catch (_) { /* ignore */ }
    currentSource = null
  }
  isPlaying.value = false
}

function togglePlay() {
  if (isPlaying.value) {
    stopAudio()
  } else {
    playAudio()
  }
}

// ── 自动播放 ──
watch(() => props.data, (newData) => {
  if (!cfgAutoPlay.value) return
  const d = newData || {}
  const hasNewAudio = d.audio_b64 || (d.segments && d.segments.length > 0)
  if (hasNewAudio && props.status === 'completed') {
    playAudio()
  }
})

// ── 下载 ──
function downloadAudio() {
  const b64 = getAudioB64()
  if (!b64) return

  const fmt = (props.data || {}).format || 'wav'
  const mime = fmt === 'mp3' ? 'audio/mpeg' : 'audio/wav'
  const arrayBuffer = base64ToArrayBuffer(b64)
  const blob = new Blob([arrayBuffer], { type: mime })
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = `audio_player_${Date.now()}.${fmt}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.audio-player-body { padding: 2px 0; }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.pending { background: #8b90a0; }
.status-dot.processing { background: #4a8eff; animation: pulse 1.5s infinite; }
.status-dot.completed { background: #4edea3; box-shadow: 0 0 6px rgba(78,222,163,0.5); }
.status-dot.error { background: #ffb4ab; }
.status-text { font-size: 11px; color: #c1c6d7; }
.model-tag {
  font-size: 8px; font-family: 'Space Grotesk', sans-serif;
  color: #adc7ff; background: rgba(173,199,255,0.08); padding: 1px 5px; border-radius: 9999px;
  margin-left: auto; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.hint-text { font-size: 10px; color: #64748b; text-align: center; padding: 8px 0; }
.error-text { font-size: 10px; color: #ffb4ab; text-align: center; padding: 8px 0; }

.proc-info { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #adc7ff; padding: 4px 0; }
.proc-icon { font-size: 14px; color: #4a8eff; }

.done-info { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #c1c6d7; padding: 4px 0; }
.done-icon { font-size: 14px; color: #4edea3; }

/* ── 播放/下载按钮 ── */
.action-bar {
  display: flex; gap: 4px; margin-top: 6px;
}
.action-btn {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 24px;
  background: #10131b; border: 1px solid #31353d; border-radius: 4px;
  color: #adc7ff; cursor: pointer; padding: 0;
  transition: background 0.15s, border-color 0.15s;
}
.action-btn:hover { background: #1a1f2b; border-color: #4a8eff; }
.action-btn.active { background: rgba(74,142,255,0.15); border-color: #4a8eff; }
.action-btn .material-symbols-outlined { font-size: 16px; }

/* ── Config Tab ── */
.ap-config { padding: 4px 0; }
.ap-config .cfg-field { margin-bottom: 8px; }
.ap-config .cfg-label { display: block; font-size: 10px; color: #8b90a0; margin-bottom: 3px; }
.ap-config .cfg-check { display: flex; align-items: center; gap: 8px; }
.ap-config .cfg-check .cfg-label { margin-bottom: 0; }
.ap-config .cfg-check input[type="checkbox"] {
  accent-color: #4a8eff; width: 14px; height: 14px; cursor: pointer;
}
.ap-config .cfg-range {
  -webkit-appearance: none; appearance: none;
  width: 100%; height: 4px; background: #31353d; border-radius: 2px; outline: none;
}
.ap-config .cfg-range::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 12px; height: 12px; border-radius: 50%; background: #4a8eff; cursor: pointer;
}
.ap-config .cfg-range-val {
  font-size: 10px; color: #8b90a0; font-family: 'Space Grotesk', sans-serif;
}
</style>
