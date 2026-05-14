<!--
  VadPresetsPanel — WebRTC VAD 预设管理
  管理 VAD 分句参数：vad_mode, frame_duration, hangover, sample_rate, min_speech
-->
<template>
  <div class="lpp-root">
    <!-- ── Toolbar ── -->
    <div class="lpp-toolbar">
      <span class="lpp-subtitle">{{ platforms.length }} 个引擎 / {{ totalModels }} 个预设</span>
      <div class="lpp-tb-actions">
        <button class="lpp-btn" @click="openPlatformEdit()">+ 新建引擎</button>
        <button class="lpp-btn-reset" @click="onRefresh">刷新</button>
      </div>
    </div>

    <div class="lpp-main">
      <!-- ── 引擎列表 ── -->
      <div class="lpp-platforms">
        <div
          v-for="p in platforms" :key="p.id"
          class="lpp-platform-card"
          :class="{ active: selectedPlatformId === p.id }"
          @click="selectedPlatformId = p.id"
        >
          <div class="lpp-pc-header">
            <span class="lpp-pc-name">{{ p.name }}</span>
            <span class="lpp-pc-provider">{{ p.provider }}</span>
          </div>
          <div class="lpp-pc-meta">{{ (p.models || []).length }} 个预设</div>
          <div v-if="selectedPlatformId === p.id" class="lpp-pc-actions">
            <button class="lpp-act" @click.stop="openPlatformEdit(p)">编辑</button>
            <button class="lpp-act" @click.stop="onDuplicatePlatform(p.id)">复制</button>
            <button class="lpp-act danger" @click.stop="onDeletePlatform(p.id)">删除</button>
          </div>
        </div>
      </div>

      <!-- ── 预设列表 ── -->
      <div class="lpp-models" v-if="selectedPlatform">
        <div class="lpp-models-header">
          <span class="lpp-models-title">{{ selectedPlatform.name }} - 预设</span>
          <button class="lpp-btn" @click="openModelEdit()">+ 新建预设</button>
        </div>
        <div v-for="m in selectedPlatform.models" :key="m.id" class="lpp-model-card">
          <div class="lpp-mc-main">
            <div class="lpp-mc-header">
              <span class="lpp-mc-name">{{ m.name }}</span>
              <span v-if="m.is_default" class="lpp-mc-default">默认</span>
            </div>
            <div class="lpp-mc-tags">
              <span class="lpp-tag">Mode: {{ m.vad_mode ?? 3 }}</span>
              <span class="lpp-tag">{{ m.sample_rate ?? 16000 }} Hz</span>
              <span class="lpp-tag">Hangover: {{ m.hangover_ms ?? 600 }}ms</span>
              <span class="lpp-tag">Min: {{ m.min_speech_ms ?? 300 }}ms</span>
            </div>
          </div>
          <div class="lpp-mc-actions">
            <button class="lpp-act" @click="openModelEdit(m)">编辑</button>
            <button class="lpp-act" @click="onDuplicateModel(selectedPlatform.id, m.id)">复制</button>
            <button class="lpp-act danger" @click="onDeleteModel(selectedPlatform.id, m.id)">删除</button>
          </div>
        </div>
        <div v-if="!selectedPlatform.models?.length" class="lpp-empty">暂无预设</div>
      </div>
      <div v-else class="lpp-models lpp-no-select">
        <div class="lpp-empty">← 选择左侧引擎查看预设</div>
      </div>
    </div>

    <!-- ═══ 引擎编辑弹窗 ═══ -->
    <div v-if="platformModal.visible" class="lpp-overlay" @click.self="platformModal.visible = false">
      <div class="lpp-modal">
        <h3 class="lpp-modal-title">
          <span class="material-symbols-outlined" style="font-size:18px">voice_selection</span>
          {{ platformModal.editingId ? '编辑引擎' : '新建引擎' }}
        </h3>
        <div class="lpp-field">
          <label>引擎名称 <span class="lpp-required">*</span></label>
          <input v-model="platformModal.form.name" placeholder="例如: 默认 WebRTC VAD" />
        </div>
        <div class="lpp-field">
          <label>Provider</label>
          <input :value="'webrtcvad'" disabled />
          <div class="lpp-field-hint">VAD 仅支持 WebRTC VAD 引擎</div>
        </div>
        <div class="lpp-modal-actions">
          <button class="lpp-btn-cancel" @click="platformModal.visible = false">取消</button>
          <button class="lpp-btn-save" @click="onSavePlatform" :disabled="!platformModal.form.name.trim()">保存</button>
        </div>
      </div>
    </div>

    <!-- ═══ 预设编辑弹窗 ═══ -->
    <div v-if="modelModal.visible" class="lpp-overlay" @click.self="modelModal.visible = false">
      <div class="lpp-modal">
        <h3 class="lpp-modal-title">
          <span class="material-symbols-outlined" style="font-size:18px">tune</span>
          {{ modelModal.editingId ? '编辑预设' : '新建预设' }}
        </h3>

        <div class="lpp-field">
          <label>预设名称 <span class="lpp-required">*</span></label>
          <input v-model="modelModal.form.name" placeholder="例如: 默认 (Mode 3)" />
        </div>
        <div class="lpp-field">
          <label class="lpp-check">
            <input type="checkbox" v-model="modelModal.form.is_default" />
            设为该引擎默认预设
          </label>
        </div>

        <div class="lpp-section-title">VAD 参数</div>

        <div class="lpp-field">
          <label>VAD 模式 (0=宽松 ~ 3=最激进)</label>
          <select v-model.number="modelModal.form.vad_mode">
            <option :value="0">0 — 宽松 (更多语音)</option>
            <option :value="1">1 — 中等</option>
            <option :value="2">2 — 激进</option>
            <option :value="3">3 — 最激进 (更少误判)</option>
          </select>
        </div>

        <div class="lpp-field">
          <label>帧时长 (ms)</label>
          <select v-model.number="modelModal.form.frame_duration_ms">
            <option :value="10">10 ms</option>
            <option :value="20">20 ms</option>
            <option :value="30">30 ms</option>
          </select>
        </div>

        <div class="lpp-field">
          <label>静音超时 Hangover (ms)</label>
          <input type="number" v-model.number="modelModal.form.hangover_ms" min="100" max="3000" step="50" />
          <div class="lpp-field-hint">连续静音多久后判定句子结束，建议 400~800</div>
        </div>

        <div class="lpp-field">
          <label>最短语音时长 (ms)</label>
          <input type="number" v-model.number="modelModal.form.min_speech_ms" min="50" max="2000" step="50" />
          <div class="lpp-field-hint">最短多长的语音才算有效句子，过滤噪音</div>
        </div>

        <div class="lpp-field">
          <label>采样率 (Hz)</label>
          <select v-model.number="modelModal.form.sample_rate">
            <option :value="8000">8000</option>
            <option :value="16000">16000</option>
            <option :value="32000">32000</option>
            <option :value="48000">48000</option>
          </select>
        </div>

        <div class="lpp-modal-actions">
          <button class="lpp-btn-cancel" @click="modelModal.visible = false">取消</button>
          <button class="lpp-btn-save" @click="onSaveModel" :disabled="!modelModal.form.name.trim()">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePresetsStore } from '@/stores/presets'
import { pipelineSocket } from '@/api/pipeline'

const store = usePresetsStore()

const platforms = computed(() => store.vadPlatforms)
const totalModels = computed(() => platforms.value.reduce((s, p) => s + (p.models || []).length, 0))

const selectedPlatformId = ref(null)
const selectedPlatform = computed(() => platforms.value.find(p => p.id === selectedPlatformId.value))

// ── 引擎弹窗 ──
const emptyPlatform = () => ({ name: '', provider: 'webrtcvad' })
const platformModal = ref({ visible: false, editingId: null, form: emptyPlatform() })

function openPlatformEdit(platform) {
  platformModal.value.editingId = platform?.id || null
  platformModal.value.form = platform ? { ...platform } : emptyPlatform()
  platformModal.value.visible = true
}

async function onSavePlatform() {
  const form = platformModal.value.form
  const payload = { name: form.name, provider: 'webrtcvad' }
  if (platformModal.value.editingId) payload.id = platformModal.value.editingId
  await store.saveVadPlatform(payload)
  platformModal.value.visible = false
}

async function onDeletePlatform(id) {
  if (!confirm('删除引擎将同时删除其下所有预设，确认？')) return
  await store.deleteVadPlatform(id)
  if (selectedPlatformId.value === id) selectedPlatformId.value = null
}

async function onDuplicatePlatform(id) {
  await store.duplicateVadPlatform(id)
}

// ── 预设弹窗 ──
function emptyModel() {
  return { name: '', is_default: false, vad_mode: 3, frame_duration_ms: 20, hangover_ms: 600, sample_rate: 16000, min_speech_ms: 300 }
}
const modelModal = ref({ visible: false, editingId: null, form: emptyModel() })

function openModelEdit(model) {
  modelModal.value.editingId = model?.id || null
  modelModal.value.form = model ? { ...model } : emptyModel()
  modelModal.value.visible = true
}

async function onSaveModel() {
  if (!selectedPlatform.value) return
  const form = modelModal.value.form
  const payload = { ...form }
  if (modelModal.value.editingId) payload.id = modelModal.value.editingId
  await store.saveVadModel(selectedPlatform.value.id, payload)
  modelModal.value.visible = false
}

async function onDeleteModel(platformId, modelId) {
  if (!confirm('确认删除此预设？')) return
  await store.deleteVadModel(platformId, modelId)
}

async function onDuplicateModel(platformId, modelId) {
  await store.duplicateVadModel(platformId, modelId)
}

function onRefresh() {
  pipelineSocket.sendCommand('_system', 'vad_preset.list', {})
}

onMounted(() => { store.initVad() })
</script>

<style scoped>
.lpp-root { display: flex; flex-direction: column; height: 100%; }
.lpp-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.lpp-subtitle { font-size: 12px; color: #8b90a0; }
.lpp-tb-actions { display: flex; gap: 8px; }
.lpp-btn {
  background: rgba(255,182,149,0.08); border: 1px solid rgba(255,182,149,0.25);
  color: #ffb695; font-size: 11px; padding: 4px 12px; border-radius: 4px;
  cursor: pointer; transition: all 0.15s;
}
.lpp-btn:hover { background: rgba(255,182,149,0.15); }
.lpp-btn-reset {
  background: none; border: 1px solid #414754; color: #8b90a0;
  font-size: 11px; padding: 4px 12px; border-radius: 4px; cursor: pointer;
}

.lpp-main { display: flex; gap: 16px; flex: 1; min-height: 0; }

/* ── 引擎列表 ── */
.lpp-platforms { width: 220px; flex-shrink: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.lpp-platform-card {
  background: rgba(255,182,149,0.03); border: 1px solid rgba(65,71,84,0.3);
  border-radius: 6px; padding: 10px 12px; cursor: pointer; transition: all 0.15s;
}
.lpp-platform-card:hover { border-color: #414754; }
.lpp-platform-card.active { border-color: #ffb695; background: rgba(255,182,149,0.06); }
.lpp-pc-header { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.lpp-pc-name { font-size: 12px; font-weight: 600; color: #e0e2ed; flex: 1; }
.lpp-pc-provider { font-size: 8px; padding: 1px 6px; border-radius: 10px; background: rgba(78,222,163,0.1); color: #4edea3; }
.lpp-pc-meta { font-size: 10px; color: #8b90a0; margin-top: 2px; }
.lpp-pc-actions { display: flex; gap: 4px; margin-top: 6px; }

.lpp-act {
  background: none; border: none; color: #8b90a0; font-size: 9px;
  padding: 2px 6px; cursor: pointer; border-radius: 3px;
}
.lpp-act:hover { color: #ffb695; background: rgba(255,182,149,0.06); }
.lpp-act.danger:hover { color: #ffb4ab; background: rgba(255,180,171,0.08); }

/* ── 预设列表 ── */
.lpp-models { flex: 1; overflow-y: auto; }
.lpp-models-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px; padding-bottom: 8px;
  border-bottom: 1px solid rgba(65,71,84,0.3);
}
.lpp-models-title { font-size: 13px; font-weight: 600; color: #e0e2ed; }
.lpp-model-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-radius: 6px; border: 1px solid rgba(65,71,84,0.2);
  margin-bottom: 6px; background: rgba(255,182,149,0.02);
}
.lpp-mc-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.lpp-mc-name { font-size: 12px; font-weight: 600; color: #e0e2ed; }
.lpp-mc-default { font-size: 9px; padding: 1px 6px; border-radius: 10px; background: rgba(255,182,149,0.15); color: #ffb695; }
.lpp-mc-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.lpp-tag {
  font-size: 9px; padding: 1px 6px; border-radius: 4px;
  background: rgba(139,144,160,0.1); color: #8b90a0;
  font-family: 'Space Grotesk', monospace;
}
.lpp-mc-actions { display: flex; gap: 4px; flex-shrink: 0; }
.lpp-no-select { display: flex; align-items: center; justify-content: center; }
.lpp-empty { font-size: 12px; color: #64748b; padding: 40px 0; text-align: center; }

/* ── 弹窗 ── */
.lpp-overlay {
  position: fixed; inset: 0; z-index: 200; display: flex;
  align-items: center; justify-content: center;
  background: rgba(0,0,0,0.6);
}
.lpp-modal {
  background: #181c23; border: 1px solid #414754; border-radius: 10px;
  padding: 24px; width: 460px; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 12px 40px rgba(0,0,0,0.5);
}
.lpp-modal-title {
  font-size: 15px; font-weight: 600; color: #e0e2ed;
  display: flex; align-items: center; gap: 8px;
  margin: 0 0 16px;
}
.lpp-section-title {
  font-size: 11px; font-weight: 700; color: #ffb695;
  text-transform: uppercase; letter-spacing: 0.5px;
  margin: 16px 0 8px; padding-bottom: 4px;
  border-bottom: 1px solid rgba(65,71,84,0.2);
}
.lpp-field { margin-bottom: 10px; }
.lpp-field label { display: block; font-size: 11px; color: #8b90a0; margin-bottom: 4px; }
.lpp-field input, .lpp-field select {
  width: 100%; padding: 7px 10px; font-size: 12px;
  background: #10131b; border: 1px solid #31353d; border-radius: 5px;
  color: #e0e2ed; font-family: inherit; outline: none; resize: vertical;
}
.lpp-field input:focus, .lpp-field select:focus { border-color: #ffb695; }
.lpp-field input:disabled { opacity: 0.4; cursor: not-allowed; }
.lpp-field-hint { font-size: 9px; color: #64748b; margin-top: 2px; }
.lpp-check { display: flex !important; align-items: center; gap: 6px; cursor: pointer; }
.lpp-check input { width: auto; }
.lpp-required { color: #ffb4ab; }
.lpp-modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.lpp-btn-cancel {
  background: none; border: 1px solid #414754; color: #8b90a0;
  font-size: 12px; padding: 6px 18px; border-radius: 5px; cursor: pointer;
}
.lpp-btn-save {
  background: rgba(255,182,149,0.15); border: 1px solid #ffb695;
  color: #ffb695; font-size: 12px; padding: 6px 18px; border-radius: 5px;
  cursor: pointer; font-weight: 600;
}
.lpp-btn-save:hover:not(:disabled) { background: rgba(255,182,149,0.25); }
.lpp-btn-save:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
