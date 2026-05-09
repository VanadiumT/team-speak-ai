<!--
  SysVarsPanelFull — 系统变量管理（主内容区版本）
  支持完整的增删改查操作。
-->
<template>
  <div class="svf">
    <!-- Toast 通知 -->
    <transition name="toast-fade">
      <div v-if="store.toast.show" class="svf-toast" :class="store.toast.type">
        <span class="material-symbols-outlined svf-toast-icon">
          {{ store.toast.type === 'success' ? 'check_circle' : store.toast.type === 'error' ? 'error' : 'info' }}
        </span>
        {{ store.toast.message }}
      </div>
    </transition>

    <!-- 工具栏 -->
    <div class="svf-toolbar">
      <button class="svf-btn primary" @click="startAdd">
        <span class="material-symbols-outlined">add</span> 新增变量
      </button>
      <button class="svf-btn" @click="store.fetchAll()" :disabled="store.loading">
        <span class="material-symbols-outlined" :class="{ spinning: store.loading }">refresh</span>
        刷新
      </button>
      <span class="svf-count" v-if="varList.length > 0">{{ varList.length }} 个变量</span>
    </div>

    <!-- 加载中 -->
    <div v-if="store.loading && varList.length === 0" class="svf-empty">
      <span class="material-symbols-outlined svf-spin" style="font-size: 40px; opacity: 0.3;">sync</span>
      <p>加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="varList.length === 0" class="svf-empty">
      <span class="material-symbols-outlined" style="font-size: 40px; opacity: 0.15;">data_object</span>
      <p>暂无系统变量</p>
      <button class="svf-btn primary" style="margin-top: 12px;" @click="startAdd">
        <span class="material-symbols-outlined">add</span> 创建第一个变量
      </button>
    </div>

    <!-- 变量表格 -->
    <table v-else class="svf-table">
      <thead>
        <tr>
          <th style="width: 180px;">Key</th>
          <th style="width: 200px;">引用</th>
          <th>Value</th>
          <th style="width: 56px;">类型</th>
          <th style="width: 88px;">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in varList" :key="item.key">
          <td class="svf-key" :title="item.key">{{ item.key }}</td>
          <td class="svf-ref">
            <code class="svf-ref-text">{{ '$sys.' + item.key }}</code>
            <button class="svf-copy-btn" @click="copyRef('$sys.' + item.key)" :title="copied === '$sys.' + item.key ? '已复制' : '复制引用'">
              <span class="material-symbols-outlined">{{ copied === '$sys.' + item.key ? 'check' : 'content_copy' }}</span>
            </button>
          </td>
          <td class="svf-value" :title="formatValueFull(item.value)">
            <code class="svf-val-preview">{{ formatValue(item.value) }}</code>
          </td>
          <td class="svf-type">
            <span class="svf-type-badge">{{ getTypeLabel(item.value) }}</span>
          </td>
          <td class="svf-actions">
            <button class="svf-icon-btn" @click="startEdit(item.key, item.value)" title="编辑">
              <span class="material-symbols-outlined">edit</span>
            </button>
            <button class="svf-icon-btn svf-icon-del" @click="confirmDelete(item.key)" title="删除">
              <span class="material-symbols-outlined">delete</span>
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 编辑弹层 -->
    <div v-if="editing" class="svf-overlay" @click.self="cancelEdit">
      <div class="svf-dialog">
        <h3 class="svf-dialog-title">
          <span class="material-symbols-outlined svf-dialog-icon">
            {{ editing.isNew ? 'add_circle' : 'edit' }}
          </span>
          {{ editing.isNew ? '新增变量' : '编辑变量' }}
        </h3>

        <div class="svf-field">
          <label>Key <span class="svf-required">*</span></label>
          <input
            v-model="editing.key"
            class="svf-input"
            placeholder="变量名（字母、数字、下划线）"
            :disabled="!editing.isNew"
            @keyup.enter="focusValue"
          />
          <span class="svf-hint" v-if="editing.isNew">创建后不可修改 Key</span>
          <span class="svf-ref-preview" v-if="editing.key.trim()">
            引用格式：<code>$sys.{{ editing.key.trim() }}</code>
          </span>
        </div>

        <div class="svf-field">
          <label>Value</label>
          <textarea
            ref="valueInput"
            v-model="editing.value"
            class="svf-input svf-textarea"
            placeholder="值（支持文本、数字、JSON）"
            rows="4"
            @keyup.ctrl.enter="saveEdit"
          ></textarea>
          <span class="svf-hint">Ctrl+Enter 保存</span>
        </div>

        <div class="svf-dialog-btns">
          <button class="svf-cancel-btn" @click="cancelEdit">取消</button>
          <button class="svf-save-btn" @click="saveEdit" :disabled="!editing.key.trim() || saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹层 -->
    <div v-if="deleting" class="svf-overlay" @click.self="deleting = null">
      <div class="svf-dialog svf-dialog-sm">
        <h3 class="svf-dialog-title">
          <span class="material-symbols-outlined svf-dialog-icon" style="color: #ffb4ab;">warning</span>
          确认删除
        </h3>
        <p class="svf-confirm-text">
          确定要删除变量 <strong class="svf-confirm-key">{{ deleting }}</strong> 吗？此操作不可恢复。
        </p>
        <div class="svf-dialog-btns">
          <button class="svf-cancel-btn" @click="deleting = null">取消</button>
          <button class="svf-del-btn" @click="doDelete">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, nextTick, onMounted } from 'vue'
import { useSysVarsStore } from '@/stores/sysvars'

const store = useSysVarsStore()

onMounted(() => { store.init() })

const varList = computed(() =>
  Object.entries(store.vars).map(([key, value]) => ({ key, value }))
)

const editing = ref(null)
const deleting = ref(null)
const saving = ref(false)
const copied = ref('')
const valueInput = ref(null)

async function copyRef(refStr) {
  try {
    await navigator.clipboard.writeText(refStr)
    copied.value = refStr
    setTimeout(() => { copied.value = '' }, 2000)
  } catch {
    // fallback
    const ta = document.createElement('textarea')
    ta.value = refStr; ta.style.position = 'fixed'; ta.style.opacity = '0'
    document.body.appendChild(ta); ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = refStr
    setTimeout(() => { copied.value = '' }, 2000)
  }
}

function startAdd() {
  editing.value = { key: '', value: '', isNew: true }
  nextTick(() => {
    const el = document.querySelector('.svf-dialog .svf-input')
    el?.focus()
  })
}

function startEdit(key, value) {
  const str = value === null || value === undefined ? '' : (
    typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
  )
  editing.value = { key, value: str, isNew: false }
  nextTick(() => {
    valueInput.value?.focus()
  })
}

function focusValue() {
  valueInput.value?.focus()
}

function cancelEdit() {
  editing.value = null
  saving.value = false
}

async function saveEdit() {
  if (!editing.value || !editing.value.key.trim() || saving.value) return
  const key = editing.value.key.trim()
  const rawValue = editing.value.value

  // 尝试解析 JSON
  let parsed = rawValue
  const trimmed = rawValue.trim()
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try { parsed = JSON.parse(trimmed) } catch { /* keep as string */ }
  } else if (trimmed === 'true') {
    parsed = true
  } else if (trimmed === 'false') {
    parsed = false
  } else if (trimmed === 'null') {
    parsed = null
  } else if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
    parsed = Number(trimmed)
  }

  saving.value = true
  try {
    await store.setVar(key, parsed)
    editing.value = null
  } finally {
    saving.value = false
  }
}

function confirmDelete(key) {
  deleting.value = key
}

async function doDelete() {
  if (!deleting.value) return
  const key = deleting.value
  deleting.value = null
  await store.deleteVar(key)
}

function getTypeLabel(v) {
  if (v === null || v === undefined) return 'null'
  if (Array.isArray(v)) return 'array'
  if (typeof v === 'object') return 'object'
  if (typeof v === 'boolean') return 'bool'
  if (typeof v === 'number') return 'number'
  return 'string'
}

function formatValue(v) {
  if (v === null || v === undefined) return '(空)'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

function formatValueFull(v) {
  if (v === null || v === undefined) return '(空)'
  if (typeof v === 'object') return JSON.stringify(v, null, 2)
  return String(v)
}
</script>

<style scoped>
.svf {
  position: relative;
}

/* ── Toast ── */
.svf-toast {
  position: fixed; top: 72px; right: 24px; z-index: 300;
  display: flex; align-items: center; gap: 8px;
  padding: 10px 20px; border-radius: 8px;
  font-size: 13px; font-weight: 500;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}
.svf-toast.success { background: #0d3320; color: #4edea3; border: 1px solid rgba(78, 222, 163, 0.3); }
.svf-toast.error { background: #3d1a1a; color: #ffb4ab; border: 1px solid rgba(255, 180, 171, 0.3); }
.svf-toast.info { background: #1a2540; color: #adc7ff; border: 1px solid rgba(173, 199, 255, 0.3); }
.svf-toast-icon { font-size: 18px; }

.toast-fade-enter-active, .toast-fade-leave-active { transition: all 0.25s ease; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translateX(20px); }

/* ── Toolbar ── */
.svf-toolbar {
  display: flex; align-items: center; gap: 8px; margin-bottom: 20px;
}
.svf-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 6px;
  border: 1px solid #414754; background: transparent;
  color: #c1c6d7; font-size: 13px; cursor: pointer;
  transition: all 0.15s;
}
.svf-btn:hover { border-color: #adc7ff; color: #adc7ff; }
.svf-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.svf-btn.primary {
  background: rgba(173, 199, 255, 0.1); border-color: #adc7ff; color: #adc7ff;
}
.svf-btn.primary:hover { background: rgba(173, 199, 255, 0.2); }
.svf-btn .material-symbols-outlined { font-size: 18px; }

.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.svf-count {
  margin-left: auto; font-size: 11px; color: #64748b;
}

/* ── Empty ── */
.svf-empty {
  display: flex; flex-direction: column;
  align-items: center; padding: 60px 0;
  color: #64748b;
}
.svf-empty p { margin-top: 12px; font-size: 14px; }
.svf-spin { animation: spin 1.5s linear infinite; }

/* ── Table ── */
.svf-table {
  width: 100%; border-collapse: collapse;
  table-layout: fixed;
}
.svf-table th {
  text-align: left; padding: 8px 12px;
  font-size: 11px; font-weight: 600; color: #64748b;
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid rgba(65, 71, 84, 0.4);
}
.svf-table td {
  padding: 10px 8px;
  border-bottom: 1px solid rgba(65, 71, 84, 0.15);
  vertical-align: middle;
}
.svf-table tr:hover td { background: rgba(173, 199, 255, 0.03); }

.svf-key {
  font-family: 'Space Grotesk', monospace;
  font-size: 13px; color: #ffb695;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.svf-value {
  max-width: 360px;
}
.svf-val-preview {
  font-family: 'Space Grotesk', monospace;
  font-size: 12px; color: #c1c6d7;
  background: rgba(173, 199, 255, 0.04);
  padding: 2px 8px; border-radius: 4px;
  display: inline-block; max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.svf-type { }
.svf-type-badge {
  display: inline-block; padding: 1px 5px; border-radius: 8px;
  font-size: 9px; font-family: 'Space Grotesk', monospace;
  font-weight: 600; text-transform: uppercase;
  background: rgba(173, 199, 255, 0.08);
  color: #8b90a0;
  letter-spacing: 0.04em;
}

/* ── Reference column ── */
.svf-ref {
  display: flex; align-items: center; gap: 6px;
  min-width: 0;
}
.svf-ref-text {
  font-family: 'Space Grotesk', monospace;
  font-size: 12px; color: #4edea3;
  background: rgba(78, 222, 163, 0.06);
  padding: 2px 8px; border-radius: 4px;
  user-select: all;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  flex: 1; min-width: 0;
}
.svf-copy-btn {
  display: flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 4px;
  border: none; background: transparent; color: #64748b;
  cursor: pointer; transition: all 0.15s; flex-shrink: 0;
}
.svf-copy-btn:hover { background: rgba(78, 222, 163, 0.1); color: #4edea3; }
.svf-copy-btn .material-symbols-outlined { font-size: 14px; }

/* ── Reference preview in dialog ── */
.svf-ref-preview {
  display: block; margin-top: 6px;
  font-size: 11px; color: #4edea3;
}
.svf-ref-preview code {
  font-family: 'Space Grotesk', monospace;
  background: rgba(78, 222, 163, 0.08);
  padding: 2px 6px; border-radius: 3px;
  font-size: 12px;
}

.svf-actions { display: flex; gap: 4px; }
.svf-icon-btn {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: 4px;
  border: none; background: transparent; color: #64748b;
  cursor: pointer; transition: all 0.15s;
}
.svf-icon-btn:hover { background: rgba(173, 199, 255, 0.1); color: #adc7ff; }
.svf-icon-del:hover { background: rgba(255, 180, 171, 0.1); color: #ffb4ab; }
.svf-icon-btn .material-symbols-outlined { font-size: 16px; }

/* ── Dialog ── */
.svf-overlay {
  position: fixed; inset: 0; z-index: 100;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0, 0, 0, 0.5);
}
.svf-dialog {
  width: 440px; padding: 24px; border-radius: 12px;
  background: #1a1e2e; border: 1px solid #414754;
}
.svf-dialog-sm { width: 360px; }
.svf-dialog-title {
  display: flex; align-items: center; gap: 8px;
  margin: 0 0 20px; font-size: 16px; font-weight: 600;
}
.svf-dialog-icon { color: #adc7ff; }
.svf-field { margin-bottom: 16px; }
.svf-field label {
  display: block; margin-bottom: 6px;
  font-size: 12px; color: #8b90a0;
}
.svf-required { color: #ffb4ab; }
.svf-hint {
  display: block; margin-top: 4px;
  font-size: 10px; color: #64748b;
}
.svf-input {
  width: 100%; padding: 8px 12px; border-radius: 6px;
  border: 1px solid #31353d; background: #0f1219; color: #e0e2ed;
  font-size: 13px; font-family: 'Space Grotesk', monospace;
  outline: none; box-sizing: border-box;
}
.svf-input:focus { border-color: #adc7ff; }
.svf-input:disabled { opacity: 0.5; }
.svf-textarea {
  resize: vertical; min-height: 80px;
  line-height: 1.5;
}

.svf-dialog-btns { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; }

.svf-cancel-btn, .svf-save-btn, .svf-del-btn {
  padding: 8px 20px; border-radius: 6px; font-size: 13px;
  cursor: pointer; border: 1px solid #414754; background: transparent;
}
.svf-cancel-btn { color: #8b90a0; }
.svf-cancel-btn:hover { background: rgba(139, 144, 160, 0.1); }
.svf-save-btn { color: #adc7ff; border-color: #adc7ff; background: rgba(173, 199, 255, 0.1); }
.svf-save-btn:hover { background: rgba(173, 199, 255, 0.2); }
.svf-save-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.svf-del-btn { color: #ffb4ab; border-color: #ffb4ab; background: rgba(255, 180, 171, 0.08); }
.svf-del-btn:hover { background: rgba(255, 180, 171, 0.2); }

/* ── Confirm dialog ── */
.svf-confirm-text {
  font-size: 13px; color: #94a3b8; line-height: 1.6; margin: 0;
}
.svf-confirm-key {
  color: #ffb695; font-family: 'Space Grotesk', monospace;
}
</style>
