<!--
  LlmPresetsPanel — LLM 预设管理（平台 + 模型）
  左侧平台列表，右侧模型列表，弹窗编辑。
-->
<template>
  <div class="lpp-root">
    <!-- ── Toolbar ── -->
    <div class="lpp-toolbar">
      <span class="lpp-subtitle">{{ platforms.length }} 个平台 / {{ totalModels }} 个模型</span>
      <div class="lpp-tb-actions">
        <button class="lpp-btn" @click="openPlatformEdit()">+ 新建平台</button>
        <button class="lpp-btn-reset" @click="onRefresh">刷新</button>
      </div>
    </div>

    <div class="lpp-main">
      <!-- ── 平台列表 ── -->
      <div class="lpp-platforms">
        <div
          v-for="p in platforms" :key="p.id"
          class="lpp-platform-card"
          :class="{ active: selectedPlatformId === p.id }"
          @click="selectedPlatformId = p.id"
        >
          <div class="lpp-pc-header">
            <span class="lpp-pc-name">{{ p.name }}</span>
            <span class="lpp-pc-badge">{{ p.provider }}</span>
          </div>
          <div class="lpp-pc-info">{{ p.base_url || '(默认地址)' }}</div>
          <div class="lpp-pc-meta">{{ (p.models || []).length }} 个模型</div>
          <div v-if="selectedPlatformId === p.id" class="lpp-pc-actions">
            <button class="lpp-act" @click.stop="openPlatformEdit(p)">编辑</button>
            <button class="lpp-act" @click.stop="onDuplicatePlatform(p.id)">复制</button>
            <button class="lpp-act danger" @click.stop="onDeletePlatform(p.id)">删除</button>
          </div>
        </div>
      </div>

      <!-- ── 模型列表 ── -->
      <div class="lpp-models" v-if="selectedPlatform">
        <div class="lpp-models-header">
          <span class="lpp-models-title">{{ selectedPlatform.name }} - 模型</span>
          <button class="lpp-btn" @click="openModelEdit()">+ 新建模型</button>
        </div>
        <div v-for="m in selectedPlatform.models" :key="m.id" class="lpp-model-card">
          <div class="lpp-mc-main">
            <div class="lpp-mc-header">
              <span class="lpp-mc-name">{{ m.name }}</span>
              <span v-if="m.is_default" class="lpp-mc-default">默认</span>
            </div>
            <div class="lpp-mc-tags">
              <span class="lpp-tag">temp: {{ m.temperature ?? 0.7 }}</span>
              <span class="lpp-tag">{{ m.streaming !== false ? '流式' : '非流式' }}</span>
              <span class="lpp-tag">{{ thinkingLabel(m.thinking_mode) }}</span>
              <span class="lpp-tag" :class="{ on: m.vision }">{{ m.vision ? 'vision: on' : 'vision: off' }}</span>
            </div>
          </div>
          <div class="lpp-mc-actions">
            <button class="lpp-act" @click="openModelEdit(m)">编辑</button>
            <button class="lpp-act" @click="onDuplicateModel(selectedPlatform.id, m.id)">复制</button>
            <button class="lpp-act danger" @click="onDeleteModel(selectedPlatform.id, m.id)">删除</button>
            <button class="lpp-act lpp-test-btn"
              :class="{ testing: testStates[m.id]?.loading }"
              @click="testModel(selectedPlatform.id, m.id)"
              :disabled="testStates[m.id]?.loading">
              {{ testLabel(m.id) }}
            </button>
          </div>
          <div v-if="testStates[m.id]?.result" class="lpp-test-result"
            :class="testStates[m.id].result.success ? 'success' : 'fail'">
            {{ testStates[m.id].result.message }}
          </div>
        </div>
        <div v-if="!selectedPlatform.models?.length" class="lpp-empty">暂无模型</div>
      </div>
      <div v-else class="lpp-models lpp-no-select">
        <div class="lpp-empty">← 选择左侧平台查看模型</div>
      </div>
    </div>

    <!-- ═══ 平台编辑弹窗 ═══ -->
    <div v-if="platformModal.visible" class="lpp-overlay" @click.self="platformModal.visible = false">
      <div class="lpp-modal">
        <h3 class="lpp-modal-title">{{ platformModal.editingId ? '编辑平台' : '新建平台' }}</h3>
        <div class="lpp-field">
          <label>平台名称</label>
          <input v-model="platformModal.form.name" placeholder="例如: MiniMax 平台" />
        </div>
        <div class="lpp-field">
          <label>Provider</label>
          <select v-model="platformModal.form.provider">
            <option value="openai">OpenAI 兼容</option>
          </select>
        </div>
        <div class="lpp-field">
          <label>Base URL</label>
          <input v-model="platformModal.form.base_url" placeholder="留空=默认地址" />
        </div>
        <div class="lpp-field">
          <label>API Key</label>
          <input v-model="platformModal.form.api_key" placeholder="留空=使用全局 KEY" type="password" />
        </div>
        <div class="lpp-modal-actions">
          <button class="lpp-btn-cancel" @click="platformModal.visible = false">取消</button>
          <button class="lpp-btn-save" @click="onSavePlatform">保存</button>
        </div>
      </div>
    </div>

    <!-- ═══ 模型编辑弹窗 ═══ -->
    <div v-if="modelModal.visible" class="lpp-overlay" @click.self="modelModal.visible = false">
      <div class="lpp-modal lpp-modal-wide">
        <h3 class="lpp-modal-title">{{ modelModal.editingId ? '编辑模型' : '新建模型' }}</h3>

        <div class="lpp-field">
          <label>模型名称</label>
          <input v-model="modelModal.form.name" placeholder="例如: MiniMax-M2.7" />
        </div>
        <div class="lpp-field">
          <label class="lpp-check">
            <input type="checkbox" v-model="modelModal.form.is_default" />
            设为该平台默认模型
          </label>
        </div>

        <div class="lpp-section-title">生成参数</div>
        <div class="lpp-row">
          <div class="lpp-field lpp-col">
            <label>Temperature</label>
            <input type="number" v-model.number="modelModal.form.temperature" min="0" max="2" step="0.05" />
          </div>
          <div class="lpp-field lpp-col">
            <label>Max Tokens</label>
            <input type="number" v-model.number="modelModal.form.max_tokens" min="64" max="32768" />
          </div>
          <div class="lpp-field lpp-col">
            <label>Top P</label>
            <input type="number" v-model.number="modelModal.form.top_p" min="0" max="1" step="0.05" />
          </div>
        </div>

        <div class="lpp-section-title">输出模式</div>
        <div class="lpp-field">
          <label class="lpp-check">
            <input type="checkbox" v-model="modelModal.form.streaming" />
            流式输出 (streaming)
          </label>
        </div>

        <div class="lpp-section-title">思考层级</div>
        <div class="lpp-field">
          <select v-model="modelModal.form.thinking_mode">
            <option value="off">off — 不启用思考</option>
            <option value="separate">separate — 分离思考面板</option>
            <option value="inline">inline — 内联思考（解析 response 标签）</option>
          </select>
        </div>

        <div class="lpp-section-title">视觉/多模态</div>
        <div class="lpp-row">
          <div class="lpp-field lpp-col">
            <label class="lpp-check">
              <input type="checkbox" v-model="modelModal.form.vision" />
              启用 Vision
            </label>
          </div>
          <div class="lpp-field lpp-col" v-if="modelModal.form.vision">
            <label>图片详情</label>
            <select v-model="modelModal.form.image_detail">
              <option value="auto">auto</option>
              <option value="low">low</option>
              <option value="high">high</option>
            </select>
          </div>
          <div class="lpp-field lpp-col" v-if="modelModal.form.vision">
            <label>最大图片数</label>
            <input type="number" v-model.number="modelModal.form.max_images" min="1" max="20" />
          </div>
        </div>

        <div class="lpp-section-title">上下文</div>
        <div class="lpp-field">
          <label>System Prompt</label>
          <textarea v-model="modelModal.form.system_prompt" rows="3" placeholder="留空=使用上游上下文" />
        </div>
        <div class="lpp-field">
          <label>最大上下文 Token 数 (0=不限制)</label>
          <input type="number" v-model.number="modelModal.form.max_context_tokens" min="0" />
        </div>

        <div class="lpp-section-title">输出控制</div>
        <div class="lpp-row">
          <div class="lpp-field lpp-col">
            <label>Response Format</label>
            <select v-model="modelModal.form.response_format">
              <option value="text">text</option>
              <option value="json_object">json_object</option>
            </select>
          </div>
        </div>

        <div class="lpp-modal-actions">
          <button class="lpp-btn-cancel" @click="modelModal.visible = false">取消</button>
          <button class="lpp-btn-save" @click="onSaveModel">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { usePresetsStore } from '@/stores/presets'
import { pipelineSocket } from '@/api/pipeline'

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
    const resp = await pipelineSocket.sendCommand('_system', 'preset.test_llm', { platform_id: platformId, model_id: modelId })
    testStates[modelId] = { loading: false, result: resp.test_result }
  } catch {
    testStates[modelId] = { loading: false, result: { success: false, message: '请求超时或连接断开' } }
  }
}
const platforms = computed(() => store.platforms)
const totalModels = computed(() => platforms.value.reduce((s, p) => s + (p.models || []).length, 0))

const selectedPlatformId = ref(null)
const selectedPlatform = computed(() => platforms.value.find(p => p.id === selectedPlatformId.value))

function thinkingLabel(mode) {
  const m = { off: 'think:off', separate: 'think:分离', inline: 'think:内联' }
  return m[mode] || mode
}

// ── 平台弹窗 ──
const emptyPlatform = () => ({ name: '', provider: 'openai', base_url: '', api_key: '' })
const platformModal = ref({ visible: false, editingId: null, form: emptyPlatform() })

function openPlatformEdit(platform) {
  platformModal.value.editingId = platform?.id || null
  platformModal.value.form = platform ? { ...platform } : emptyPlatform()
  platformModal.value.visible = true
}

async function onSavePlatform() {
  const form = platformModal.value.form
  const payload = { name: form.name, provider: form.provider, base_url: form.base_url, api_key: form.api_key }
  if (platformModal.value.editingId) payload.id = platformModal.value.editingId
  await store.savePlatform(payload)
  platformModal.value.visible = false
}

async function onDeletePlatform(id) {
  if (!confirm('删除平台将同时删除其下所有模型，确认？')) return
  await store.deletePlatform(id)
  if (selectedPlatformId.value === id) selectedPlatformId.value = null
}

async function onDuplicatePlatform(id) {
  await store.duplicatePlatform(id)
}

// ── 模型弹窗 ──
function emptyModel() { return { name: '', is_default: false, temperature: 0.7, max_tokens: 4096, top_p: 1.0, streaming: true, thinking_mode: 'off', vision: false, image_detail: 'auto', max_images: 4, system_prompt: '', max_context_tokens: 0, response_format: 'text', stop: [], extra: {} } }
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
  await store.saveModel(selectedPlatform.value.id, payload)
  modelModal.value.visible = false
}

async function onDeleteModel(platformId, modelId) {
  if (!confirm('确认删除此模型？')) return
  await store.deleteModel(platformId, modelId)
}

async function onDuplicateModel(platformId, modelId) {
  await store.duplicateModel(platformId, modelId)
}

function onRefresh() {
  pipelineSocket.sendCommand('_system', 'preset.list', {})
}

onMounted(() => { store.init() })
</script>

<style scoped>
.lpp-root { display: flex; flex-direction: column; height: 100%; }
.lpp-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.lpp-subtitle { font-size: 12px; color: #8b90a0; }
.lpp-tb-actions { display: flex; gap: 8px; }
.lpp-btn {
  background: rgba(173,199,255,0.08); border: 1px solid rgba(173,199,255,0.25);
  color: #adc7ff; font-size: 11px; padding: 4px 12px; border-radius: 4px;
  cursor: pointer; transition: all 0.15s;
}
.lpp-btn:hover { background: rgba(173,199,255,0.15); }
.lpp-btn-reset {
  background: none; border: 1px solid #414754; color: #8b90a0;
  font-size: 11px; padding: 4px 12px; border-radius: 4px; cursor: pointer;
}

.lpp-main { display: flex; gap: 16px; flex: 1; min-height: 0; }

/* ── 平台列表 ── */
.lpp-platforms { width: 220px; flex-shrink: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.lpp-platform-card {
  background: rgba(173,199,255,0.03); border: 1px solid rgba(65,71,84,0.3);
  border-radius: 6px; padding: 10px 12px; cursor: pointer; transition: all 0.15s;
}
.lpp-platform-card:hover { border-color: #414754; }
.lpp-platform-card.active { border-color: #adc7ff; background: rgba(173,199,255,0.06); }
.lpp-pc-header { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.lpp-pc-name { font-size: 12px; font-weight: 600; color: #e0e2ed; }
.lpp-pc-badge { font-size: 9px; padding: 1px 6px; border-radius: 10px; background: rgba(78,222,163,0.1); color: #4edea3; }
.lpp-pc-info { font-size: 10px; color: #64748b; font-family: 'Space Grotesk', monospace; }
.lpp-pc-meta { font-size: 10px; color: #8b90a0; margin-top: 2px; }
.lpp-pc-actions { display: flex; gap: 4px; margin-top: 6px; }

.lpp-act {
  background: none; border: none; color: #8b90a0; font-size: 9px;
  padding: 2px 6px; cursor: pointer; border-radius: 3px;
}
.lpp-act:hover { color: #adc7ff; background: rgba(173,199,255,0.06); }
.lpp-act.danger:hover { color: #ffb4ab; background: rgba(255,180,171,0.08); }

/* ── 模型列表 ── */
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
  margin-bottom: 6px; background: rgba(173,199,255,0.02);
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
.lpp-tag.on { background: rgba(78,222,163,0.1); color: #4edea3; }
.lpp-mc-actions { display: flex; gap: 4px; flex-shrink: 0; align-items: center; }
.lpp-test-btn {
  color: #4edea3 !important;
  border-color: rgba(78,222,163,0.3) !important;
}
.lpp-test-btn:hover { color: #4edea3 !important; background: rgba(78,222,163,0.08) !important; }
.lpp-test-btn.testing { color: #ffb695 !important; opacity: 0.7; }
.lpp-test-result {
  font-size: 9px; margin-top: 4px; padding: 4px 8px; border-radius: 4px;
  font-family: 'Space Grotesk', monospace;
}
.lpp-test-result.success { color: #4edea3; background: rgba(78,222,163,0.06); }
.lpp-test-result.fail { color: #ffb4ab; background: rgba(255,180,171,0.06); }
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
  padding: 24px; width: 480px; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 12px 40px rgba(0,0,0,0.5);
}
.lpp-modal-wide { width: 620px; }
.lpp-modal-title { font-size: 16px; font-weight: 600; color: #e0e2ed; margin: 0 0 16px; }
.lpp-section-title {
  font-size: 11px; font-weight: 700; color: #adc7ff;
  text-transform: uppercase; letter-spacing: 0.5px;
  margin: 16px 0 8px; padding-bottom: 4px;
  border-bottom: 1px solid rgba(65,71,84,0.2);
}
.lpp-field { margin-bottom: 10px; }
.lpp-field label { display: block; font-size: 11px; color: #8b90a0; margin-bottom: 4px; }
.lpp-field input, .lpp-field select, .lpp-field textarea {
  width: 100%; padding: 7px 10px; font-size: 12px;
  background: #10131b; border: 1px solid #31353d; border-radius: 5px;
  color: #e0e2ed; font-family: inherit; outline: none; resize: vertical;
}
.lpp-field input:focus, .lpp-field select:focus, .lpp-field textarea:focus { border-color: #4a8eff; }
.lpp-row { display: flex; gap: 10px; }
.lpp-col { flex: 1; }
.lpp-check { display: flex !important; align-items: center; gap: 6px; cursor: pointer; }
.lpp-check input { width: auto; }
.lpp-modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.lpp-btn-cancel {
  background: none; border: 1px solid #414754; color: #8b90a0;
  font-size: 12px; padding: 6px 18px; border-radius: 5px; cursor: pointer;
}
.lpp-btn-save {
  background: rgba(173,199,255,0.15); border: 1px solid #adc7ff;
  color: #adc7ff; font-size: 12px; padding: 6px 18px; border-radius: 5px;
  cursor: pointer; font-weight: 600;
}
.lpp-btn-save:hover { background: rgba(173,199,255,0.25); }
</style>
