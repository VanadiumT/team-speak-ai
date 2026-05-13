<!--
  TeamSpeakPresetsPanel — TeamSpeak Bridge 连接预设管理
  配置 Python ↔ Java Bridge 之间的 WebSocket 连接。
  TeamSpeak 服务器参数由 Java 项目管理，不在此配置。
-->
<template>
  <div class="tsb-root">
    <!-- ── Toolbar ── -->
    <div class="tsb-toolbar">
      <span class="tsb-subtitle">{{ platforms.length }} 个桥接 / {{ totalModels }} 个连接配置</span>
      <div class="tsb-tb-actions">
        <button class="tsb-btn" @click="openPlatformEdit()">+ 新建桥接</button>
        <button class="tsb-btn-reset" @click="onRefresh">刷新</button>
      </div>
    </div>

    <!-- ── 说明条 ── -->
    <div class="tsb-hint">
      <span class="material-symbols-outlined" style="font-size:12px">info</span>
      配置 Python 后端连接 Java TeamSpeak Bridge 的 WebSocket 地址。
      TeamSpeak 服务器参数（host/password/channel/nickname）在 Java 项目中配置。
    </div>

    <div class="tsb-main">
      <!-- ── 桥接实例列表 ── -->
      <div class="tsb-platforms">
        <div
          v-for="p in platforms" :key="p.id"
          class="tsb-platform-card"
          :class="{ active: selectedPlatformId === p.id }"
          @click="selectedPlatformId = p.id"
        >
          <div class="tsb-pc-header">
            <span class="tsb-pc-name">{{ p.name }}</span>
            <span class="tsb-pc-status" :class="bridgeStatus(p).cls">
              {{ bridgeStatus(p).label }}
            </span>
          </div>
          <div class="tsb-pc-url">{{ p.ws_url || '(未设置)' }}</div>
          <div class="tsb-pc-meta">{{ (p.models || []).length }} 个连接配置</div>
          <div v-if="selectedPlatformId === p.id" class="tsb-pc-actions">
            <button class="tsb-act" @click.stop="openPlatformEdit(p)">编辑</button>
            <button class="tsb-act" @click.stop="onDuplicatePlatform(p.id)">复制</button>
            <button class="tsb-act danger" @click.stop="onDeletePlatform(p.id)">删除</button>
          </div>
        </div>
      </div>

      <!-- ── 连接配置列表 ── -->
      <div class="tsb-models" v-if="selectedPlatform">
        <div class="tsb-models-header">
          <span class="tsb-models-title">{{ selectedPlatform.name }} - 连接配置</span>
          <button class="tsb-btn" @click="openModelEdit()">+ 新建配置</button>
        </div>
        <div v-for="m in selectedPlatform.models" :key="m.id" class="tsb-model-card">
          <div class="tsb-mc-main">
            <div class="tsb-mc-header">
              <span class="tsb-mc-name">{{ m.name }}</span>
              <span v-if="m.is_default" class="tsb-mc-default">默认</span>
            </div>
            <div class="tsb-mc-tags">
              <span class="tsb-tag">标识: {{ m.nickname || 'TeamSpeakAI' }}</span>
              <span class="tsb-tag" :class="{ on: m.auto_reconnect !== false }">
                {{ m.auto_reconnect !== false ? '自动重连' : '手动重连' }}
              </span>
              <span class="tsb-tag" v-if="m.auto_reconnect !== false">
                {{ m.reconnect_delay ?? 3 }}s
              </span>
              <span v-if="m.loopback" class="tsb-tag on">回环监听</span>
            </div>
          </div>
          <div class="tsb-mc-actions">
            <button class="tsb-act" @click="openModelEdit(m)">编辑</button>
            <button class="tsb-act" @click="onDuplicateModel(selectedPlatform.id, m.id)">复制</button>
            <button class="tsb-act danger" @click="onDeleteModel(selectedPlatform.id, m.id)">删除</button>
            <button class="tsb-act tsb-test-btn"
              :class="{ testing: testStates[m.id]?.loading }"
              @click="testBridge(selectedPlatform.id, m.id)"
              :disabled="testStates[m.id]?.loading">
              {{ testLabel(m.id) }}
            </button>
          </div>
          <div v-if="testStates[m.id]?.result" class="tsb-test-result"
            :class="testStates[m.id].result.success ? 'success' : 'fail'">
            {{ testStates[m.id].result.message }}
          </div>
        </div>
        <div v-if="!selectedPlatform.models?.length" class="tsb-empty">暂无连接配置</div>
      </div>
      <div v-else class="tsb-models tsb-no-select">
        <div class="tsb-empty">← 选择左侧桥接查看连接配置</div>
      </div>
    </div>

    <!-- ═══ 桥接实例编辑弹窗 ═══ -->
    <div v-if="platformModal.visible" class="tsb-overlay" @click.self="platformModal.visible = false">
      <div class="tsb-modal">
        <h3 class="tsb-modal-title">
          <span class="material-symbols-outlined" style="font-size:18px">hub</span>
          {{ platformModal.editingId ? '编辑桥接' : '新建桥接' }}
        </h3>
        <div class="tsb-field">
          <label>桥接名称 <span class="tsb-required">*</span></label>
          <input v-model="platformModal.form.name" placeholder="例如: 本地桥接、开发用桥接" />
        </div>
        <div class="tsb-field">
          <label>WebSocket 地址 <span class="tsb-required">*</span></label>
          <input v-model="platformModal.form.ws_url" placeholder="ws://localhost:8080/teamspeak/voice" />
        </div>
        <div class="tsb-field">
          <label>API Key</label>
          <input v-model="platformModal.form.api_key" placeholder="留空=无认证" type="password" />
        </div>
        <div class="tsb-modal-actions">
          <button class="tsb-btn-cancel" @click="platformModal.visible = false">取消</button>
          <button class="tsb-btn-save" @click="onSavePlatform" :disabled="!platformModal.form.name.trim() || !platformModal.form.ws_url.trim()">保存</button>
        </div>
      </div>
    </div>

    <!-- ═══ 连接配置编辑弹窗 ═══ -->
    <div v-if="modelModal.visible" class="tsb-overlay" @click.self="modelModal.visible = false">
      <div class="tsb-modal">
        <h3 class="tsb-modal-title">
          <span class="material-symbols-outlined" style="font-size:18px">settings_ethernet</span>
          {{ modelModal.editingId ? '编辑连接配置' : '新建连接配置' }}
        </h3>

        <div class="tsb-field">
          <label>配置名称 <span class="tsb-required">*</span></label>
          <input v-model="modelModal.form.name" placeholder="例如: 默认配置" />
        </div>
        <div class="tsb-field">
          <label class="tsb-check">
            <input type="checkbox" v-model="modelModal.form.is_default" />
            设为该桥接默认配置
          </label>
        </div>

        <div class="tsb-section-title">连接标识</div>
        <div class="tsb-field">
          <label>客户端标识 (nickname)</label>
          <input v-model="modelModal.form.nickname" placeholder="TeamSpeakAI" />
          <div class="tsb-field-hint">Python 后端在桥接中的显示名称，用于日志区分不同连接</div>
        </div>

        <div class="tsb-section-title">重连策略</div>
        <div class="tsb-field">
          <label class="tsb-check">
            <input type="checkbox" v-model="modelModal.form.auto_reconnect" />
            断线后自动重连
          </label>
        </div>
        <div class="tsb-field" v-if="modelModal.form.auto_reconnect">
          <label>重连间隔 (秒)</label>
          <input type="number" v-model.number="modelModal.form.reconnect_delay" min="1" max="60" step="0.5" />
        </div>

        <div class="tsb-section-title">音频策略</div>
        <div class="tsb-field">
          <label class="tsb-check">
            <input type="checkbox" v-model="modelModal.form.loopback" />
            回环监听 — 将 TTS 播放的音频同时回环到输入，让 TS 输入节点能采集到机器人自身的语音
          </label>
        </div>

        <div class="tsb-modal-actions">
          <button class="tsb-btn-cancel" @click="modelModal.visible = false">取消</button>
          <button class="tsb-btn-save" @click="onSaveModel" :disabled="!modelModal.form.name.trim()">保存</button>
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

async function testBridge(platformId, modelId) {
  testStates[modelId] = { loading: true, result: null }
  try {
    const resp = await pipelineSocket.sendCommand('_system', 'ts_preset.test', { platform_id: platformId, model_id: modelId })
    testStates[modelId] = { loading: false, result: resp.test_result }
  } catch {
    testStates[modelId] = { loading: false, result: { success: false, message: '请求超时或连接断开' } }
  }
}

const platforms = computed(() => store.tsPlatforms)
const totalModels = computed(() => platforms.value.reduce((s, p) => s + (p.models || []).length, 0))

const selectedPlatformId = ref(null)
const selectedPlatform = computed(() => platforms.value.find(p => p.id === selectedPlatformId.value))

// ── 桥接状态推断 ──
function bridgeStatus(p) {
  // 简单基于 ws_url 是否配置来判断：有 url = 已配置
  if (p.ws_url) return { label: '已配置', cls: 'ok' }
  return { label: '未配置', cls: 'warn' }
}

// ── 桥接弹窗 ──
const emptyPlatform = () => ({ name: '', ws_url: 'ws://localhost:8080/teamspeak/voice', api_key: '' })
const platformModal = ref({ visible: false, editingId: null, form: emptyPlatform() })

function openPlatformEdit(platform) {
  platformModal.value.editingId = platform?.id || null
  platformModal.value.form = platform ? { ...platform } : emptyPlatform()
  platformModal.value.visible = true
}

async function onSavePlatform() {
  const form = platformModal.value.form
  const payload = { name: form.name, ws_url: form.ws_url, api_key: form.api_key }
  if (platformModal.value.editingId) payload.id = platformModal.value.editingId
  await store.saveTsPlatform(payload)
  platformModal.value.visible = false
}

async function onDeletePlatform(id) {
  if (!confirm('删除桥接将同时删除其下所有连接配置，确认？')) return
  await store.deleteTsPlatform(id)
  if (selectedPlatformId.value === id) selectedPlatformId.value = null
}

async function onDuplicatePlatform(id) {
  await store.duplicateTsPlatform(id)
}

// ── 连接配置弹窗 ──
function emptyModel() {
  return { name: '', is_default: false, nickname: 'TeamSpeakAI', auto_reconnect: true, reconnect_delay: 3.0, loopback: false }
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
  await store.saveTsModel(selectedPlatform.value.id, payload)
  modelModal.value.visible = false
}

async function onDeleteModel(platformId, modelId) {
  if (!confirm('确认删除此连接配置？')) return
  await store.deleteTsModel(platformId, modelId)
}

async function onDuplicateModel(platformId, modelId) {
  await store.duplicateTsModel(platformId, modelId)
}

function onRefresh() {
  pipelineSocket.sendCommand('_system', 'ts_preset.list', {})
}

onMounted(() => { store.initTs() })
</script>

<style scoped>
.tsb-root { display: flex; flex-direction: column; height: 100%; }
.tsb-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.tsb-subtitle { font-size: 12px; color: #8b90a0; }
.tsb-tb-actions { display: flex; gap: 8px; }
.tsb-btn {
  background: rgba(255,182,149,0.08); border: 1px solid rgba(255,182,149,0.25);
  color: #ffb695; font-size: 11px; padding: 4px 12px; border-radius: 4px;
  cursor: pointer; transition: all 0.15s;
}
.tsb-btn:hover { background: rgba(255,182,149,0.15); }
.tsb-btn-reset {
  background: none; border: 1px solid #414754; color: #8b90a0;
  font-size: 11px; padding: 4px 12px; border-radius: 4px; cursor: pointer;
}
.tsb-btn-save:disabled { opacity: 0.3; cursor: not-allowed; }

/* ── 说明条 ── */
.tsb-hint {
  display: flex; align-items: center; gap: 6px;
  font-size: 10px; color: #64748b;
  padding: 6px 10px; margin-bottom: 12px;
  background: rgba(255,182,149,0.04); border: 1px solid rgba(255,182,149,0.08);
  border-radius: 4px; line-height: 1.4;
}

.tsb-main { display: flex; gap: 16px; flex: 1; min-height: 0; }

/* ── 桥接列表 ── */
.tsb-platforms { width: 230px; flex-shrink: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.tsb-platform-card {
  background: rgba(255,182,149,0.03); border: 1px solid rgba(65,71,84,0.3);
  border-radius: 6px; padding: 10px 12px; cursor: pointer; transition: all 0.15s;
}
.tsb-platform-card:hover { border-color: #414754; }
.tsb-platform-card.active { border-color: #ffb695; background: rgba(255,182,149,0.06); }
.tsb-pc-header { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.tsb-pc-name { font-size: 12px; font-weight: 600; color: #e0e2ed; flex: 1; }
.tsb-pc-status { font-size: 8px; padding: 1px 6px; border-radius: 10px; }
.tsb-pc-status.ok { background: rgba(78,222,163,0.1); color: #4edea3; }
.tsb-pc-status.warn { background: rgba(239,196,68,0.1); color: #efc444; }
.tsb-pc-url {
  font-size: 9px; color: #64748b; font-family: 'Space Grotesk', monospace;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.tsb-pc-meta { font-size: 10px; color: #8b90a0; margin-top: 2px; }
.tsb-pc-actions { display: flex; gap: 4px; margin-top: 6px; }

.tsb-act {
  background: none; border: none; color: #8b90a0; font-size: 9px;
  padding: 2px 6px; cursor: pointer; border-radius: 3px;
}
.tsb-act:hover { color: #ffb695; background: rgba(255,182,149,0.06); }
.tsb-act.danger:hover { color: #ffb4ab; background: rgba(255,180,171,0.08); }

/* ── 连接配置列表 ── */
.tsb-models { flex: 1; overflow-y: auto; }
.tsb-models-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px; padding-bottom: 8px;
  border-bottom: 1px solid rgba(65,71,84,0.3);
}
.tsb-models-title { font-size: 13px; font-weight: 600; color: #e0e2ed; }
.tsb-model-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-radius: 6px; border: 1px solid rgba(65,71,84,0.2);
  margin-bottom: 6px; background: rgba(255,182,149,0.02);
}
.tsb-mc-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.tsb-mc-name { font-size: 12px; font-weight: 600; color: #e0e2ed; }
.tsb-mc-default { font-size: 9px; padding: 1px 6px; border-radius: 10px; background: rgba(255,182,149,0.15); color: #ffb695; }
.tsb-mc-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.tsb-tag {
  font-size: 9px; padding: 1px 6px; border-radius: 4px;
  background: rgba(139,144,160,0.1); color: #8b90a0;
  font-family: 'Space Grotesk', monospace;
}
.tsb-tag.on { background: rgba(78,222,163,0.1); color: #4edea3; }
.tsb-mc-actions { display: flex; gap: 4px; flex-shrink: 0; align-items: center; }
.tsb-test-btn {
  color: #4edea3 !important;
  border-color: rgba(78,222,163,0.3) !important;
}
.tsb-test-btn:hover { color: #4edea3 !important; background: rgba(78,222,163,0.08) !important; }
.tsb-test-btn.testing { color: #ffb695 !important; opacity: 0.7; }
.tsb-test-result {
  font-size: 9px; margin-top: 4px; padding: 4px 8px; border-radius: 4px;
  font-family: 'Space Grotesk', monospace;
}
.tsb-test-result.success { color: #4edea3; background: rgba(78,222,163,0.06); }
.tsb-test-result.fail { color: #ffb4ab; background: rgba(255,180,171,0.06); }
.tsb-no-select { display: flex; align-items: center; justify-content: center; }
.tsb-empty { font-size: 12px; color: #64748b; padding: 40px 0; text-align: center; }

/* ── 弹窗 ── */
.tsb-overlay {
  position: fixed; inset: 0; z-index: 200; display: flex;
  align-items: center; justify-content: center;
  background: rgba(0,0,0,0.6);
}
.tsb-modal {
  background: #181c23; border: 1px solid #414754; border-radius: 10px;
  padding: 24px; width: 480px; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 12px 40px rgba(0,0,0,0.5);
}
.tsb-modal-title {
  font-size: 15px; font-weight: 600; color: #e0e2ed;
  display: flex; align-items: center; gap: 8px;
  margin: 0 0 16px;
}
.tsb-section-title {
  font-size: 11px; font-weight: 700; color: #ffb695;
  text-transform: uppercase; letter-spacing: 0.5px;
  margin: 16px 0 8px; padding-bottom: 4px;
  border-bottom: 1px solid rgba(65,71,84,0.2);
}
.tsb-field { margin-bottom: 10px; }
.tsb-field label { display: block; font-size: 11px; color: #8b90a0; margin-bottom: 4px; }
.tsb-field input, .tsb-field select, .tsb-field textarea {
  width: 100%; padding: 7px 10px; font-size: 12px;
  background: #10131b; border: 1px solid #31353d; border-radius: 5px;
  color: #e0e2ed; font-family: inherit; outline: none; resize: vertical;
}
.tsb-field input:focus, .tsb-field select:focus, .tsb-field textarea:focus { border-color: #ffb695; }
.tsb-field-hint { font-size: 9px; color: #64748b; margin-top: 2px; }
.tsb-check { display: flex !important; align-items: center; gap: 6px; cursor: pointer; }
.tsb-check input { width: auto; }
.tsb-required { color: #ffb4ab; }
.tsb-modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.tsb-btn-cancel {
  background: none; border: 1px solid #414754; color: #8b90a0;
  font-size: 12px; padding: 6px 18px; border-radius: 5px; cursor: pointer;
}
.tsb-btn-save {
  background: rgba(255,182,149,0.15); border: 1px solid #ffb695;
  color: #ffb695; font-size: 12px; padding: 6px 18px; border-radius: 5px;
  cursor: pointer; font-weight: 600;
}
.tsb-btn-save:hover:not(:disabled) { background: rgba(255,182,149,0.25); }
.tsb-btn-save:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
