<!--
  SttPresetsPanel — STT 预设管理（平台 + 模型）
  参照 LlmPresetsPanel 结构，字段适配 STT 引擎
-->
<template>
  <div class="stp-root">
    <!-- ── Toolbar ── -->
    <div class="stp-toolbar">
      <span class="stp-subtitle">{{ platforms.length }} 个平台 / {{ totalModels }} 个模型</span>
      <div class="stp-tb-actions">
        <button class="stp-btn" @click="openPlatformEdit()">+ 新建平台</button>
        <button class="stp-btn-reset" @click="onRefresh">刷新</button>
      </div>
    </div>

    <div class="stp-main">
      <!-- ── 平台列表 ── -->
      <div class="stp-platforms">
        <div
          v-for="p in platforms" :key="p.id"
          class="stp-platform-card"
          :class="{ active: selectedPlatformId === p.id }"
          @click="selectedPlatformId = p.id"
        >
          <div class="stp-pc-header">
            <span class="stp-pc-name">{{ p.name }}</span>
            <span class="stp-pc-badge">{{ providerLabel(p.provider) }}</span>
          </div>
          <div class="stp-pc-info">{{ p.api_url || p.model_dir || '(本地)' }}</div>
          <div class="stp-pc-meta">{{ (p.models || []).length }} 个模型</div>
          <div v-if="selectedPlatformId === p.id" class="stp-pc-actions">
            <button class="stp-act" @click.stop="openPlatformEdit(p)">编辑</button>
            <button class="stp-act" @click.stop="onDuplicatePlatform(p.id)">复制</button>
            <button class="stp-act danger" @click.stop="onDeletePlatform(p.id)">删除</button>
          </div>
        </div>
      </div>

      <!-- ── 模型列表 ── -->
      <div class="stp-models" v-if="selectedPlatform">
        <div class="stp-models-header">
          <span class="stp-models-title">{{ selectedPlatform.name }} - 模型</span>
          <button class="stp-btn" @click="openModelEdit()">+ 新建模型</button>
        </div>
        <div v-for="m in selectedPlatform.models" :key="m.id" class="stp-model-card">
          <div class="stp-mc-main">
            <div class="stp-mc-header">
              <span class="stp-mc-name">{{ m.name }}</span>
              <span v-if="m.is_default" class="stp-mc-default">默认</span>
            </div>
            <div class="stp-mc-tags">
              <span class="stp-tag">{{ m.language || 'auto' }}</span>
              <span class="stp-tag">{{ m.sample_rate || 16000 }}Hz</span>
            </div>
          </div>
          <div class="stp-mc-actions">
            <button class="stp-act" @click="openModelEdit(m)">编辑</button>
            <button class="stp-act" @click="onDuplicateModel(selectedPlatform.id, m.id)">复制</button>
            <button class="stp-act danger" @click="onDeleteModel(selectedPlatform.id, m.id)">删除</button>
            <button class="stp-act stp-test-btn"
              :class="{ testing: testStates[m.id]?.loading }"
              @click="testModel(selectedPlatform.id, m.id)"
              :disabled="testStates[m.id]?.loading">
              {{ testLabel(m.id) }}
            </button>
          </div>
          <div v-if="testStates[m.id]?.result" class="stp-test-result"
            :class="testStates[m.id].result.success ? 'success' : 'fail'">
            {{ testStates[m.id].result.message }}
          </div>
        </div>
        <div v-if="!selectedPlatform.models?.length" class="stp-empty">暂无模型</div>
      </div>
      <div v-else class="stp-models stp-no-select">
        <div class="stp-empty">← 选择左侧平台查看模型</div>
      </div>
    </div>

    <!-- ═══ 平台编辑弹窗 ═══ -->
    <div v-if="platformModal.visible" class="stp-overlay" @click.self="platformModal.visible = false">
      <div class="stp-modal">
        <h3 class="stp-modal-title">{{ platformModal.editingId ? '编辑平台' : '新建平台' }}</h3>
        <div class="stp-field">
          <label>平台名称</label>
          <input v-model="platformModal.form.name" placeholder="例如: 本地 SenseVoice" />
        </div>
        <div class="stp-field">
          <label>Provider</label>
          <select v-model="platformModal.form.provider">
            <option value="sensevoice">SenseVoice (本地)</option>
            <option value="whisper">Whisper (本地)</option>
            <option value="minimax">MiniMax (云端)</option>
          </select>
        </div>
        <template v-if="platformModal.form.provider === 'minimax'">
          <div class="stp-field">
            <label>API Key</label>
            <input v-model="platformModal.form.api_key" placeholder="留空=使用全局 KEY" type="password" />
          </div>
          <div class="stp-field">
            <label>API URL</label>
            <input v-model="platformModal.form.api_url" placeholder="留空=默认 MiniMax 地址" />
          </div>
        </template>
        <template v-else>
          <div class="stp-field">
            <label>Model 目录/名称</label>
            <input v-model="platformModal.form.model_dir" placeholder="例如: iic/SenseVoiceSmall" />
          </div>
          <div class="stp-field">
            <label>Device</label>
            <select v-model="platformModal.form.device">
              <option value="cpu">cpu</option>
              <option value="cuda">cuda</option>
            </select>
          </div>
        </template>
        <div class="stp-modal-actions">
          <button class="stp-btn-cancel" @click="platformModal.visible = false">取消</button>
          <button class="stp-btn-save" @click="onSavePlatform">保存</button>
        </div>
      </div>
    </div>

    <!-- ═══ 模型编辑弹窗 ═══ -->
    <div v-if="modelModal.visible" class="stp-overlay" @click.self="modelModal.visible = false">
      <div class="stp-modal">
        <h3 class="stp-modal-title">{{ modelModal.editingId ? '编辑模型' : '新建模型' }}</h3>
        <div class="stp-field">
          <label>模型名称</label>
          <input v-model="modelModal.form.name" placeholder="例如: SenseVoiceSmall" />
        </div>
        <div class="stp-field">
          <label class="stp-check-label" @click="modelModal.form.is_default = !modelModal.form.is_default">
            <input type="checkbox" v-model="modelModal.form.is_default" />
            设为默认模型
          </label>
        </div>
        <div class="stp-field">
          <label>语言</label>
          <select v-model="modelModal.form.language">
            <option value="auto">auto (自动)</option>
            <option value="zh">zh (中文)</option>
            <option value="en">en (英文)</option>
          </select>
        </div>
        <div class="stp-field">
          <label>采样率 (Hz)</label>
          <select v-model="modelModal.form.sample_rate">
            <option :value="16000">16000</option>
            <option :value="8000">8000</option>
            <option :value="48000">48000</option>
          </select>
        </div>
        <div class="stp-modal-actions">
          <button class="stp-btn-cancel" @click="modelModal.visible = false">取消</button>
          <button class="stp-btn-save" @click="onSaveModel">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { usePresetsStore } from '@/stores/presets'
import { pipelineSocket } from '@/api/pipeline'

const presetsStore = usePresetsStore()
const store = {
  get platforms() { return presetsStore.sttPlatforms },
  get allModels() { return presetsStore.sttAllModels },
  get defaultModel() { return presetsStore.sttDefaultModel },
  getLabel: (...a) => presetsStore.getSttLabel(...a),
  getModelInfo: (...a) => presetsStore.getSttModelInfo(...a),
  savePlatform: (...a) => presetsStore.saveSttPlatform(...a),
  deletePlatform: (...a) => presetsStore.deleteSttPlatform(...a),
  duplicatePlatform: (...a) => presetsStore.duplicateSttPlatform(...a),
  saveModel: (...a) => presetsStore.saveSttModel(...a),
  deleteModel: (...a) => presetsStore.deleteSttModel(...a),
  duplicateModel: (...a) => presetsStore.duplicateSttModel(...a),
  init: () => presetsStore.initStt(),
}
const testStates = reactive({})

function testLabel(modelId) {
  const s = testStates[modelId]
  if (!s) return '测试'
  return s.loading ? '测试中...' : '测试'
}

async function testModel(platformId, modelId) {
  testStates[modelId] = { loading: true, result: null }
  try {
    const resp = await pipelineSocket.sendCommand('_system', 'stt_preset.test', { platform_id: platformId, model_id: modelId })
    testStates[modelId] = { loading: false, result: resp.test_result }
  } catch {
    testStates[modelId] = { loading: false, result: { success: false, message: '请求超时或连接断开' } }
  }
}
const platforms = computed(() => store.platforms)
const selectedPlatformId = ref(null)

const selectedPlatform = computed(() =>
  platforms.value.find(p => p.id === selectedPlatformId.value)
)

const totalModels = computed(() =>
  platforms.value.reduce((s, p) => s + (p.models || []).length, 0)
)

function providerLabel(p) {
  const map = { sensevoice: 'SenseVoice', whisper: 'Whisper', minimax: 'MiniMax' }
  return map[p] || p
}

// ── Platform modal ──
const emptyPlatform = () => ({
  name: '', provider: 'sensevoice', api_key: '', api_url: '',
  model_dir: '', device: 'cpu',
})
const platformModal = reactive({ visible: false, editingId: null, form: emptyPlatform() })

function openPlatformEdit(p) {
  platformModal.editingId = p ? p.id : null
  platformModal.form = p ? {
    name: p.name, provider: p.provider, api_key: p.api_key || '',
    api_url: p.api_url || '', model_dir: p.model_dir || '', device: p.device || 'cpu',
  } : emptyPlatform()
  platformModal.visible = true
}

async function onSavePlatform() {
  const payload = { ...platformModal.form }
  if (platformModal.editingId) payload.id = platformModal.editingId
  await store.savePlatform(payload)
  platformModal.visible = false
}

async function onDeletePlatform(id) {
  if (!confirm('确定删除此平台及其所有模型？')) return
  await store.deletePlatform(id)
  if (selectedPlatformId.value === id) selectedPlatformId.value = null
}

function onDuplicatePlatform(id) { store.duplicatePlatform(id) }

// ── Model modal ──
const emptyModel = () => ({ name: '', is_default: false, language: 'auto', sample_rate: 16000 })
const modelModal = reactive({ visible: false, editingId: null, form: emptyModel() })

function openModelEdit(m) {
  modelModal.editingId = m ? m.id : null
  modelModal.form = m ? {
    name: m.name, is_default: !!m.is_default,
    language: m.language || 'auto', sample_rate: m.sample_rate || 16000,
  } : emptyModel()
  modelModal.visible = true
}

async function onSaveModel() {
  const payload = { ...modelModal.form }
  if (modelModal.editingId) payload.id = modelModal.editingId
  await store.saveModel(selectedPlatformId.value, payload)
  modelModal.visible = false
}

function onDeleteModel(pid, mid) {
  if (!confirm('确定删除此模型？')) return
  store.deleteModel(pid, mid)
}

function onDuplicateModel(pid, mid) { store.duplicateModel(pid, mid) }

function onRefresh() {
  pipelineSocket.sendCommand('_system', 'stt_preset.list', {})
}

onMounted(() => { store.init() })
</script>

<style scoped>
.stp-root { color: #c1c6d7; font-size: 12px; }
.stp-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.stp-subtitle { color: #8b90a0; font-size: 11px; }
.stp-tb-actions { display: flex; gap: 6px; }
.stp-btn {
  font-size: 10px; padding: 3px 10px; border-radius: 4px; border: 1px solid #31353d;
  background: #1c2027; color: #adc7ff; cursor: pointer; font-family: inherit;
}
.stp-btn:hover { border-color: #4a8eff; }
.stp-btn-reset {
  font-size: 10px; padding: 3px 8px; border-radius: 4px; border: 1px solid transparent;
  background: transparent; color: #8b90a0; cursor: pointer; font-family: inherit;
}
.stp-btn-reset:hover { color: #c1c6d7; }

.stp-main { display: flex; gap: 10px; }
.stp-platforms { width: 200px; flex-shrink: 0; display: flex; flex-direction: column; gap: 4px; }
.stp-platform-card {
  padding: 6px 8px; border-radius: 4px; background: rgba(28,32,39,0.5);
  border: 1px solid rgba(65,71,84,0.3); cursor: pointer; transition: border-color 0.15s;
}
.stp-platform-card:hover { border-color: #4a8eff; }
.stp-platform-card.active { border-color: #adc7ff; background: rgba(173,199,255,0.04); }
.stp-pc-header { display: flex; align-items: center; gap: 4px; }
.stp-pc-name { font-size: 11px; color: #e0e2ed; font-weight: 500; }
.stp-pc-badge { font-size: 7px; color: #ffb695; background: rgba(255,182,149,0.1); padding: 1px 4px; border-radius: 9999px; }
.stp-pc-info { font-size: 8px; color: #64748b; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stp-pc-meta { font-size: 8px; color: #8b90a0; }
.stp-pc-actions { display: flex; gap: 4px; margin-top: 4px; }
.stp-act {
  font-size: 8px; padding: 1px 5px; border-radius: 3px; border: 1px solid #31353d;
  background: transparent; color: #8b90a0; cursor: pointer; font-family: inherit;
}
.stp-act:hover { color: #adc7ff; border-color: #4a8eff; }
.stp-act.danger:hover { color: #ffb4ab; border-color: #ffb4ab; }

.stp-models { flex: 1; }
.stp-models-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.stp-models-title { color: #8b90a0; font-size: 10px; }
.stp-model-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 5px 8px; border-radius: 3px; background: rgba(28,32,39,0.3);
  border: 1px solid rgba(65,71,84,0.15); margin-bottom: 3px;
}
.stp-mc-name { font-size: 11px; color: #e0e2ed; }
.stp-mc-default {
  font-size: 7px; color: #4edea3; background: rgba(78,222,163,0.1);
  padding: 1px 4px; border-radius: 9999px; margin-left: 4px;
}
.stp-mc-tags { display: flex; gap: 4px; margin-top: 2px; }
.stp-tag { font-size: 8px; color: #64748b; background: rgba(173,199,255,0.06); padding: 0 4px; border-radius: 2px; }
.stp-mc-actions { display: flex; gap: 3px; align-items: center; }
.stp-test-btn {
  color: #4edea3 !important;
  border-color: rgba(78,222,163,0.3) !important;
}
.stp-test-btn:hover { color: #4edea3 !important; background: rgba(78,222,163,0.08) !important; }
.stp-test-btn.testing { color: #ffb695 !important; opacity: 0.7; }
.stp-test-result {
  font-size: 8px; margin-top: 3px; padding: 3px 6px; border-radius: 3px;
  font-family: 'Space Grotesk', monospace;
}
.stp-test-result.success { color: #4edea3; background: rgba(78,222,163,0.06); }
.stp-test-result.fail { color: #ffb4ab; background: rgba(255,180,171,0.06); }
.stp-empty { font-size: 10px; color: #414754; text-align: center; padding: 20px 0; }
.stp-no-select { display: flex; align-items: center; justify-content: center; }

/* ── Modal ── */
.stp-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.stp-modal {
  background: #1c2027; border: 1px solid #31353d; border-radius: 8px;
  padding: 16px 20px; width: 380px; max-height: 80vh; overflow-y: auto;
}
.stp-modal-title { font-size: 13px; color: #e0e2ed; margin: 0 0 12px; }
.stp-field { margin-bottom: 8px; }
.stp-field label { display: block; font-size: 10px; color: #8b90a0; margin-bottom: 2px; }
.stp-field input, .stp-field select {
  width: 100%; padding: 5px 8px; font-size: 11px;
  background: #10131b; border: 1px solid #31353d; border-radius: 4px;
  color: #e0e2ed; font-family: inherit; outline: none;
}
.stp-field input:focus, .stp-field select:focus { border-color: #4a8eff; }
.stp-check-label { display: flex !important; align-items: center; gap: 6px; cursor: pointer; }
.stp-check-label input { width: auto; }
.stp-modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
.stp-btn-cancel {
  font-size: 10px; padding: 4px 12px; border-radius: 4px;
  border: 1px solid #31353d; background: transparent; color: #8b90a0; cursor: pointer;
}
.stp-btn-save {
  font-size: 10px; padding: 4px 12px; border-radius: 4px;
  border: none; background: #4a8eff; color: #fff; cursor: pointer;
}
.stp-btn-save:hover { background: #3a7eef; }
</style>
