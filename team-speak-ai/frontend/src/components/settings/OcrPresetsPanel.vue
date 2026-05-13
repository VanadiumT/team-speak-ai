<!--
  OcrPresetsPanel — OCR 预设管理（平台 + 模型）
  本地引擎：EasyOCR / PaddleOCR，不需要 API Key 或 Base URL。
  左侧平台列表，右侧模型列表，弹窗编辑。
-->
<template>
  <div class="opp-root">
    <!-- ── Toolbar ── -->
    <div class="opp-toolbar">
      <span class="opp-subtitle">{{ platforms.length }} 个平台 / {{ totalModels }} 个模型</span>
      <div class="opp-tb-actions">
        <button class="opp-btn" @click="openPlatformEdit()">+ 新建平台</button>
        <button class="opp-btn-reset" @click="onRefresh">刷新</button>
      </div>
    </div>

    <div class="opp-main">
      <!-- ── 平台列表 ── -->
      <div class="opp-platforms">
        <div
          v-for="p in platforms" :key="p.id"
          class="opp-platform-card"
          :class="{ active: selectedPlatformId === p.id }"
          @click="selectedPlatformId = p.id"
        >
          <div class="opp-pc-header">
            <span class="opp-pc-name">{{ p.name }}</span>
            <span class="opp-pc-badge">{{ providerLabel(p.provider) }}</span>
          </div>
          <div class="opp-pc-meta">{{ (p.models || []).length }} 个预设</div>
          <div v-if="selectedPlatformId === p.id" class="opp-pc-actions">
            <button class="opp-act" @click.stop="openPlatformEdit(p)">编辑</button>
            <button class="opp-act" @click.stop="onDuplicatePlatform(p.id)">复制</button>
            <button class="opp-act danger" @click.stop="onDeletePlatform(p.id)">删除</button>
          </div>
        </div>
      </div>

      <!-- ── 模型列表 ── -->
      <div class="opp-models" v-if="selectedPlatform">
        <div class="opp-models-header">
          <span class="opp-models-title">{{ selectedPlatform.name }} - 预设配置</span>
          <button class="opp-btn" @click="openModelEdit()">+ 新建预设</button>
        </div>
        <div v-for="m in selectedPlatform.models" :key="m.id" class="opp-model-card">
          <div class="opp-mc-main">
            <div class="opp-mc-header">
              <span class="opp-mc-name">{{ m.name }}</span>
              <span v-if="m.is_default" class="opp-mc-default">默认</span>
            </div>
            <div class="opp-mc-tags">
              <span class="opp-tag">{{ gpuLabel(m.gpu) }}</span>
              <span class="opp-tag">阈值: {{ m.confidence_threshold ?? 0.3 }}</span>
              <span v-if="selectedPlatform.provider === 'easyocr'" class="opp-tag">{{ (m.lang_list || []).join(', ') }}</span>
              <span v-else class="opp-tag">lang: {{ m.lang || 'ch' }}</span>
            </div>
          </div>
          <div class="opp-mc-actions">
            <button class="opp-act" @click="openModelEdit(m)">编辑</button>
            <button class="opp-act" @click="onDuplicateModel(selectedPlatform.id, m.id)">复制</button>
            <button class="opp-act danger" @click="onDeleteModel(selectedPlatform.id, m.id)">删除</button>
            <button class="opp-act opp-test-btn"
              :class="{ testing: testStates[m.id]?.loading }"
              @click="testModel(selectedPlatform.id, m.id)"
              :disabled="testStates[m.id]?.loading">
              {{ testLabel(m.id) }}
            </button>
          </div>
          <div v-if="testStates[m.id]?.result" class="opp-test-result"
            :class="testStates[m.id].result.success ? 'success' : 'fail'">
            {{ testStates[m.id].result.message }}
          </div>
        </div>
        <div v-if="!selectedPlatform.models?.length" class="opp-empty">暂无预设</div>
      </div>
      <div v-else class="opp-models opp-no-select">
        <div class="opp-empty">← 选择左侧平台查看预设</div>
      </div>
    </div>

    <!-- ═══ 平台编辑弹窗 ═══ -->
    <div v-if="platformModal.visible" class="opp-overlay" @click.self="platformModal.visible = false">
      <div class="opp-modal">
        <h3 class="opp-modal-title">{{ platformModal.editingId ? '编辑平台' : '新建平台' }}</h3>
        <div class="opp-field">
          <label>平台名称</label>
          <input v-model="platformModal.form.name" placeholder="例如: 本地 EasyOCR" />
        </div>
        <div class="opp-field">
          <label>Provider</label>
          <select v-model="platformModal.form.provider">
            <option value="easyocr">EasyOCR — 离线中英文</option>
            <option value="paddleocr">PaddleOCR — 中文更优</option>
          </select>
        </div>
        <div v-if="platformModal.form.provider === 'paddleocr'" class="opp-section-title">PaddleOCR 模型路径</div>
        <div v-if="platformModal.form.provider === 'paddleocr'" class="opp-field">
          <label>Detection 模型目录</label>
          <input v-model="platformModal.form.det_model_dir" placeholder="留空=使用全局设置" />
        </div>
        <div v-if="platformModal.form.provider === 'paddleocr'" class="opp-field">
          <label>Recognition 模型目录</label>
          <input v-model="platformModal.form.rec_model_dir" placeholder="留空=使用全局设置" />
        </div>
        <div class="opp-modal-actions">
          <button class="opp-btn-cancel" @click="platformModal.visible = false">取消</button>
          <button class="opp-btn-save" @click="onSavePlatform">保存</button>
        </div>
      </div>
    </div>

    <!-- ═══ 模型编辑弹窗 ═══ -->
    <div v-if="modelModal.visible" class="opp-overlay" @click.self="modelModal.visible = false">
      <div class="opp-modal opp-modal-wide">
        <h3 class="opp-modal-title">{{ modelModal.editingId ? '编辑预设' : '新建预设' }}</h3>

        <div class="opp-row">
          <div class="opp-field opp-col">
            <label>预设名称</label>
            <input v-model="modelModal.form.name" placeholder="例如: 中英混合 (GPU)" />
          </div>
          <div class="opp-field opp-col">
            <label class="opp-check">
              <input type="checkbox" v-model="modelModal.form.is_default" />
              设为默认预设
            </label>
          </div>
        </div>

        <div class="opp-section-title">识别参数</div>

        <div v-if="selectedPlatform && selectedPlatform.provider === 'easyocr'">
          <div class="opp-field">
            <label>语言列表 (逗号分隔)</label>
            <input v-model="easyocrLangStr" placeholder="ch_sim, en" />
          </div>
        </div>
        <div v-else>
          <div class="opp-field">
            <label>语言</label>
            <select v-model="modelModal.form.lang">
              <option value="ch">中文</option>
              <option value="en">英文</option>
              <option value="ch_and_en">中英混合</option>
              <option value="japan">日文</option>
              <option value="korean">韩文</option>
              <option value="french">法文</option>
              <option value="german">德文</option>
            </select>
          </div>
          <div class="opp-field">
            <label class="opp-check">
              <input type="checkbox" v-model="modelModal.form.use_angle_cls" />
              启用角度分类 (use_angle_cls)
            </label>
          </div>
        </div>

        <div class="opp-row">
          <div class="opp-field opp-col">
            <label>置信度阈值 ({{ modelModal.form.confidence_threshold ?? 0.3 }})</label>
            <input type="range" v-model.number="modelModal.form.confidence_threshold" min="0" max="1" step="0.05" />
          </div>
          <div class="opp-field opp-col">
            <label class="opp-check" style="margin-top: 8px;">
              <input type="checkbox" v-model="modelModal.form.gpu" />
              使用 GPU 加速
            </label>
          </div>
        </div>

        <div class="opp-modal-actions">
          <button class="opp-btn-cancel" @click="modelModal.visible = false">取消</button>
          <button class="opp-btn-save" @click="onSaveModel">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { usePresetsStore } from '@/stores/presets.js'
import { pipelineSocket } from '@/api/pipeline.js'

const store = usePresetsStore()
const testStates = reactive({})

function testLabel(modelId) {
  const s = testStates[modelId]
  if (!s) return '测试'
  return s.loading ? '测试中...' : '测试'
}

async function testModel(platformId, modelId) {
  testStates[modelId] = { loading: true, result: null }
  try {
    const resp = await pipelineSocket.sendCommand('_system', 'ocr_preset.test', { platform_id: platformId, model_id: modelId })
    testStates[modelId] = { loading: false, result: resp.test_result }
  } catch {
    testStates[modelId] = { loading: false, result: { success: false, message: '请求超时或连接断开' } }
  }
}
const platforms = computed(() => store.ocrPlatforms || [])
const totalModels = computed(() => platforms.value.reduce((s, p) => s + ((p && p.models) || []).length, 0))

const selectedPlatformId = ref(null)
const selectedPlatform = computed(() => platforms.value.find(p => p && p.id === selectedPlatformId.value) || null)

const easyocrLangStr = ref('')

function providerLabel(p) {
  const m = { easyocr: 'EasyOCR', paddleocr: 'PaddleOCR' }
  return m[p] || p
}

function gpuLabel(gpu) {
  return gpu ? 'GPU' : 'CPU'
}

// ── 平台弹窗 ──
const emptyPlatform = () => ({ name: '', provider: 'easyocr', det_model_dir: '', rec_model_dir: '' })
const platformModal = ref({ visible: false, editingId: null, form: emptyPlatform() })

function openPlatformEdit(platform) {
  platformModal.value.editingId = platform?.id || null
  platformModal.value.form = platform ? { ...platform } : emptyPlatform()
  platformModal.value.visible = true
}

async function onSavePlatform() {
  const form = platformModal.value.form
  const payload = { name: form.name, provider: form.provider }
  if (form.provider === 'paddleocr') {
    payload.det_model_dir = form.det_model_dir || ''
    payload.rec_model_dir = form.rec_model_dir || ''
  }
  if (platformModal.value.editingId) payload.id = platformModal.value.editingId
  await store.saveOcrPlatform(payload)
  platformModal.value.visible = false
}

async function onDeletePlatform(id) {
  if (!confirm('删除平台将同时删除其下所有预设，确认？')) return
  await store.deleteOcrPlatform(id)
  if (selectedPlatformId.value === id) selectedPlatformId.value = null
}

async function onDuplicatePlatform(id) {
  await store.duplicateOcrPlatform(id)
}

// ── 模型弹窗 ──
const emptyModel = () => ({
  name: '', is_default: false,
  lang_list: ['ch_sim', 'en'],
  lang: 'ch',
  gpu: false,
  use_angle_cls: true,
  confidence_threshold: 0.3,
})
const modelModal = ref({ visible: false, editingId: null, form: emptyModel() })

function openModelEdit(model) {
  modelModal.value.editingId = model?.id || null
  modelModal.value.form = model ? { ...model } : emptyModel()
  easyocrLangStr.value = (model && model.lang_list) ? model.lang_list.join(', ') : 'ch_sim, en'
  modelModal.value.visible = true
}

async function onSaveModel() {
  if (!selectedPlatform.value) return
  const form = { ...modelModal.value.form }
  if (selectedPlatform.value.provider === 'easyocr') {
    form.lang_list = easyocrLangStr.value.split(',').map(s => s.trim()).filter(Boolean)
    if (!form.lang_list.length) form.lang_list = ['ch_sim', 'en']
  }
  if (modelModal.value.editingId) form.id = modelModal.value.editingId
  await store.saveOcrModel(selectedPlatform.value.id, form)
  modelModal.value.visible = false
}

async function onDeleteModel(platformId, modelId) {
  if (!confirm('确认删除此预设？')) return
  await store.deleteOcrModel(platformId, modelId)
}

async function onDuplicateModel(platformId, modelId) {
  await store.duplicateOcrModel(platformId, modelId)
}

function onRefresh() {
  pipelineSocket.sendCommand('_system', 'ocr_preset.list', {})
}

onMounted(() => {
  store.initOcr()
  onRefresh()
})
</script>

<style scoped>
.opp-root { display: flex; flex-direction: column; height: 100%; }
.opp-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.opp-subtitle { font-size: 12px; color: #8b90a0; }
.opp-tb-actions { display: flex; gap: 8px; }
.opp-btn {
  background: rgba(173,199,255,0.08); border: 1px solid rgba(173,199,255,0.25);
  color: #adc7ff; font-size: 11px; padding: 4px 12px; border-radius: 4px;
  cursor: pointer; transition: all 0.15s;
}
.opp-btn:hover { background: rgba(173,199,255,0.15); }
.opp-btn-reset {
  background: none; border: 1px solid #414754; color: #8b90a0;
  font-size: 11px; padding: 4px 12px; border-radius: 4px; cursor: pointer;
}

.opp-main { display: flex; gap: 16px; flex: 1; min-height: 0; }

/* ── 平台列表 ── */
.opp-platforms { width: 220px; flex-shrink: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.opp-platform-card {
  background: rgba(173,199,255,0.03); border: 1px solid rgba(65,71,84,0.3);
  border-radius: 6px; padding: 10px 12px; cursor: pointer; transition: all 0.15s;
}
.opp-platform-card:hover { border-color: #414754; }
.opp-platform-card.active { border-color: #adc7ff; background: rgba(173,199,255,0.06); }
.opp-pc-header { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.opp-pc-name { font-size: 12px; font-weight: 600; color: #e0e2ed; }
.opp-pc-badge { font-size: 9px; padding: 1px 6px; border-radius: 10px; background: rgba(78,222,163,0.1); color: #4edea3; }
.opp-pc-meta { font-size: 10px; color: #8b90a0; margin-top: 2px; }
.opp-pc-actions { display: flex; gap: 4px; margin-top: 6px; }

.opp-act {
  background: none; border: none; color: #8b90a0; font-size: 9px;
  padding: 2px 6px; cursor: pointer; border-radius: 3px;
}
.opp-act:hover { color: #adc7ff; background: rgba(173,199,255,0.06); }
.opp-act.danger:hover { color: #ffb4ab; background: rgba(255,180,171,0.08); }

/* ── 模型列表 ── */
.opp-models { flex: 1; overflow-y: auto; }
.opp-models-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px; padding-bottom: 8px;
  border-bottom: 1px solid rgba(65,71,84,0.3);
}
.opp-models-title { font-size: 13px; font-weight: 600; color: #e0e2ed; }
.opp-model-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-radius: 6px; border: 1px solid rgba(65,71,84,0.2);
  margin-bottom: 6px; background: rgba(173,199,255,0.02);
}
.opp-mc-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.opp-mc-name { font-size: 12px; font-weight: 600; color: #e0e2ed; }
.opp-mc-default { font-size: 9px; padding: 1px 6px; border-radius: 10px; background: rgba(255,182,149,0.15); color: #ffb695; }
.opp-mc-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.opp-tag {
  font-size: 9px; padding: 1px 6px; border-radius: 4px;
  background: rgba(139,144,160,0.1); color: #8b90a0;
  font-family: 'Space Grotesk', monospace;
}
.opp-mc-actions { display: flex; gap: 4px; flex-shrink: 0; align-items: center; }
.opp-test-btn {
  color: #4edea3 !important;
  border-color: rgba(78,222,163,0.3) !important;
}
.opp-test-btn:hover { color: #4edea3 !important; background: rgba(78,222,163,0.08) !important; }
.opp-test-btn.testing { color: #ffb695 !important; opacity: 0.7; }
.opp-test-result {
  font-size: 9px; margin-top: 4px; padding: 4px 8px; border-radius: 4px;
  font-family: 'Space Grotesk', monospace;
}
.opp-test-result.success { color: #4edea3; background: rgba(78,222,163,0.06); }
.opp-test-result.fail { color: #ffb4ab; background: rgba(255,180,171,0.06); }
.opp-no-select { display: flex; align-items: center; justify-content: center; }
.opp-empty { font-size: 12px; color: #64748b; padding: 40px 0; text-align: center; }

/* ── 弹窗 ── */
.opp-overlay {
  position: fixed; inset: 0; z-index: 200; display: flex;
  align-items: center; justify-content: center;
  background: rgba(0,0,0,0.6);
}
.opp-modal {
  background: #181c23; border: 1px solid #414754; border-radius: 10px;
  padding: 24px; width: 480px; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 12px 40px rgba(0,0,0,0.5);
}
.opp-modal-wide { width: 560px; }
.opp-modal-title { font-size: 16px; font-weight: 600; color: #e0e2ed; margin: 0 0 16px; }
.opp-section-title {
  font-size: 11px; font-weight: 700; color: #adc7ff;
  text-transform: uppercase; letter-spacing: 0.5px;
  margin: 16px 0 8px; padding-bottom: 4px;
  border-bottom: 1px solid rgba(65,71,84,0.2);
}
.opp-field { margin-bottom: 10px; }
.opp-field label { display: block; font-size: 11px; color: #8b90a0; margin-bottom: 4px; }
.opp-field input, .opp-field select, .opp-field textarea {
  width: 100%; padding: 7px 10px; font-size: 12px;
  background: #10131b; border: 1px solid #31353d; border-radius: 5px;
  color: #e0e2ed; font-family: inherit; outline: none; resize: vertical;
}
.opp-field input:focus, .opp-field select:focus, .opp-field textarea:focus { border-color: #4a8eff; }
.opp-field input[type="range"] { padding: 4px 0; }
.opp-row { display: flex; gap: 10px; }
.opp-col { flex: 1; }
.opp-check { display: flex !important; align-items: center; gap: 6px; cursor: pointer; }
.opp-check input { width: auto; }
.opp-modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.opp-btn-cancel {
  background: none; border: 1px solid #414754; color: #8b90a0;
  font-size: 12px; padding: 6px 18px; border-radius: 5px; cursor: pointer;
}
.opp-btn-save {
  background: rgba(173,199,255,0.15); border: 1px solid #adc7ff;
  color: #adc7ff; font-size: 12px; padding: 6px 18px; border-radius: 5px;
  cursor: pointer; font-weight: 600;
}
.opp-btn-save:hover { background: rgba(173,199,255,0.25); }
</style>
