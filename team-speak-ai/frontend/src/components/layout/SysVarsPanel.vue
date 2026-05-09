<!--
  SysVarsPanel — 侧栏系统变量管理面板
  嵌入侧栏 sys_vars section 内，替代递归树渲染。
-->
<template>
  <div class="sys-vars-panel">
    <div class="svp-toolbar">
      <button class="svp-btn" @click="addVar" title="添加变量">
        <span class="material-symbols-outlined">add</span>
      </button>
      <button class="svp-btn" @click="refresh" title="刷新">
        <span class="material-symbols-outlined">refresh</span>
      </button>
    </div>

    <div v-if="varList.length === 0" class="svp-empty">
      暂无系统变量
    </div>

    <div v-for="item in varList" :key="item.key" class="svp-row">
      <span class="svp-key" :title="item.key">{{ item.key }}</span>
      <span class="svp-value" :title="String(item.value)">{{ formatValue(item.value) }}</span>
      <div class="svp-actions">
        <button class="svp-icon-btn" @click="editVar(item.key, item.value)" title="编辑">
          <span class="material-symbols-outlined">edit</span>
        </button>
        <button class="svp-icon-btn svp-icon-del" @click="removeVar(item.key)" title="删除">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    </div>

    <!-- 编辑弹层 -->
    <div v-if="editing" class="svp-edit-overlay" @click.self="cancelEdit">
      <div class="svp-edit-box">
        <div class="svp-edit-title">{{ editing.isNew ? '新增变量' : '编辑变量' }}</div>
        <input
          v-model="editing.key"
          class="svp-edit-input"
          placeholder="key"
          :disabled="!editing.isNew"
        />
        <input
          v-model="editing.value"
          class="svp-edit-input"
          placeholder="value"
          @keyup.enter="saveEdit"
        />
        <div class="svp-edit-btns">
          <button class="svp-edit-cancel" @click="cancelEdit">取消</button>
          <button class="svp-edit-save" @click="saveEdit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useSysVarsStore } from '@/stores/sysvars'

const sysVarsStore = useSysVarsStore()

const varList = computed(() =>
  Object.entries(sysVarsStore.vars).map(([key, value]) => ({ key, value }))
)

const editing = ref(null)

function addVar() {
  editing.value = { key: '', value: '', isNew: true }
}

function editVar(key, value) {
  editing.value = { key, value: String(value ?? ''), isNew: false }
}

function cancelEdit() {
  editing.value = null
}

async function saveEdit() {
  if (!editing.value || !editing.value.key) return
  await sysVarsStore.setVar(editing.value.key, editing.value.value)
  editing.value = null
}

async function removeVar(key) {
  await sysVarsStore.deleteVar(key)
}

async function refresh() {
  await sysVarsStore.fetchAll()
}

function formatValue(v) {
  if (v === null || v === undefined) return '(空)'
  if (typeof v === 'object') return JSON.stringify(v)
  const s = String(v)
  return s.length > 20 ? s.slice(0, 20) + '...' : s
}
</script>

<style scoped>
.sys-vars-panel {
  padding: 4px 8px;
}

.svp-toolbar {
  display: flex; gap: 4px; margin-bottom: 6px;
}
.svp-btn {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 4px;
  border: 1px solid #414754; background: transparent; color: #8b90a0;
  cursor: pointer; transition: all 0.15s;
}
.svp-btn:hover { border-color: #4edea3; color: #4edea3; }
.svp-btn .material-symbols-outlined { font-size: 14px; }

.svp-empty {
  text-align: center; padding: 12px 0;
  font-size: 11px; color: #64748b;
}

.svp-row {
  display: flex; align-items: center; gap: 4px;
  padding: 3px 0; border-bottom: 1px solid rgba(65, 71, 84, 0.2);
}
.svp-key {
  flex: 0.6; font-size: 10px; font-family: 'Space Grotesk', monospace;
  color: #ffb695; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.svp-value {
  flex: 1; font-size: 10px; font-family: 'Space Grotesk', monospace;
  color: #c1c6d7; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.svp-actions {
  display: flex; gap: 2px; opacity: 0; transition: opacity 0.15s;
}
.svp-row:hover .svp-actions { opacity: 1; }
.svp-icon-btn {
  display: flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 3px;
  border: none; background: transparent; color: #64748b;
  cursor: pointer; transition: color 0.15s;
}
.svp-icon-btn:hover { color: #adc7ff; }
.svp-icon-del:hover { color: #ffb4ab; }
.svp-icon-btn .material-symbols-outlined { font-size: 12px; }

/* ── 编辑弹层 ── */
.svp-edit-overlay {
  position: fixed; inset: 0; z-index: 100;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0, 0, 0, 0.5);
}
.svp-edit-box {
  width: 260px; padding: 16px; border-radius: 8px;
  background: #1a1e2e; border: 1px solid #414754;
}
.svp-edit-title {
  font-size: 13px; font-weight: 600; color: #e0e2ed; margin-bottom: 12px;
}
.svp-edit-input {
  width: 100%; padding: 6px 8px; margin-bottom: 8px; border-radius: 4px;
  border: 1px solid #31353d; background: #0f1219; color: #e0e2ed;
  font-size: 12px; font-family: 'Space Grotesk', monospace;
  outline: none; box-sizing: border-box;
}
.svp-edit-input:focus { border-color: #adc7ff; }
.svp-edit-input:disabled { opacity: 0.5; }
.svp-edit-btns { display: flex; gap: 8px; justify-content: flex-end; }
.svp-edit-cancel, .svp-edit-save {
  padding: 4px 12px; border-radius: 4px; font-size: 11px; cursor: pointer;
  border: 1px solid #414754; background: transparent;
}
.svp-edit-cancel { color: #8b90a0; }
.svp-edit-save { color: #adc7ff; border-color: #adc7ff; background: rgba(173, 199, 255, 0.1); }
.svp-edit-save:hover { background: rgba(173, 199, 255, 0.2); }
</style>
