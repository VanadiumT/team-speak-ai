<!--
  ShortcutsPanel — 系统快捷键查看与修改
-->
<template>
  <div class="sc-panel">
    <div class="sc-toolbar">
      <span class="sc-subtitle">共 {{ bindings.length }} 个快捷键</span>
      <button class="sc-btn-reset" @click="onResetAll">恢复默认</button>
    </div>

    <div class="sc-table-wrap">
      <table class="sc-table">
        <thead>
          <tr>
            <th class="col-cat">分类</th>
            <th class="col-label">操作</th>
            <th class="col-key">快捷键</th>
            <th class="col-act"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in bindings" :key="b.id">
            <td class="col-cat">
              <span class="sc-cat-badge">{{ b.category }}</span>
            </td>
            <td class="col-label">{{ b.label }}</td>
            <td class="col-key">
              <kbd v-if="editingId !== b.id" class="sc-kbd">{{ formatShortcut(b) }}</kbd>
              <div v-else class="sc-record-wrap">
                <kbd class="sc-kbd recording" :class="{ waiting: !recordedKeys }">
                  {{ recordedKeys || '按下新快捷键...' }}
                </kbd>
                <button class="sc-rec-cancel" @click="cancelEdit">取消</button>
              </div>
            </td>
            <td class="col-act">
              <template v-if="editingId === b.id">
                <button class="sc-act-btn sc-act-clear" @click="onClear(b)">清除</button>
              </template>
              <template v-else>
                <button class="sc-act-btn" @click="startEdit(b)">编辑</button>
                <button class="sc-act-btn sc-act-reset" @click="onReset(b)">默认</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Conflict warning -->
    <div v-if="conflictMsg" class="sc-conflict">{{ conflictMsg }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useKeybindings, formatShortcut, parseKeyEvent } from '@/keybindings.js'

const { bindings, updateBinding, resetBinding, resetAll } = useKeybindings()

const editingId = ref(null)
const recordedKeys = ref('')
const conflictMsg = ref('')

function startEdit(binding) {
  editingId.value = binding.id
  recordedKeys.value = ''
  conflictMsg.value = ''
}

function cancelEdit() {
  editingId.value = null
  recordedKeys.value = ''
  conflictMsg.value = ''
}

function onClear(binding) {
  // 设置为无快捷键 (key 为空表示禁用)
  updateBinding(binding.id, { ctrl: false, shift: false, alt: false, key: '' })
  editingId.value = null
  recordedKeys.value = ''
}

function onReset(binding) {
  resetBinding(binding.id)
}

function onResetAll() {
  resetAll()
  editingId.value = null
  recordedKeys.value = ''
  conflictMsg.value = ''
}

function onKeydown(e) {
  if (!editingId.value) return

  // 允许 Escape 取消
  if (e.key === 'Escape') {
    cancelEdit()
    return
  }

  e.preventDefault()
  e.stopPropagation()

  const parsed = parseKeyEvent(e)
  if (!parsed) return

  // 检查冲突
  const conflict = bindings.value.find(
    (b) => b.id !== editingId.value
      && b.key === parsed.key
      && (b.ctrl || false) === parsed.ctrl
      && (b.shift || false) === parsed.shift
      && (b.alt || false) === parsed.alt
  )
  if (conflict) {
    conflictMsg.value = `与「${conflict.label}」冲突，已覆盖`
  }

  recordedKeys.value = formatShortcut(parsed)
  updateBinding(editingId.value, parsed)
  editingId.value = null
}

onMounted(() => window.addEventListener('keydown', onKeydown, true))
onUnmounted(() => window.removeEventListener('keydown', onKeydown, true))
</script>

<style scoped>
.sc-panel {
  display: flex; flex-direction: column;
}
.sc-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.sc-subtitle { font-size: 12px; color: #8b90a0; }
.sc-btn-reset {
  background: none; border: 1px solid #414754;
  color: #8b90a0; font-size: 11px; padding: 4px 12px;
  border-radius: 4px; cursor: pointer; transition: all 0.15s;
}
.sc-btn-reset:hover { border-color: #ffb4ab; color: #ffb4ab; }

.sc-table-wrap { border: 1px solid rgba(65, 71, 84, 0.4); border-radius: 8px; overflow: hidden; }
.sc-table { width: 100%; border-collapse: collapse; }
.sc-table th {
  text-align: left; padding: 10px 14px;
  font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase;
  border-bottom: 1px solid rgba(65, 71, 84, 0.3);
  background: rgba(173, 199, 255, 0.03);
}
.sc-table td { padding: 12px 14px; border-bottom: 1px solid rgba(65, 71, 84, 0.15); vertical-align: middle; }
.sc-table tr:last-child td { border-bottom: none; }

.col-cat { width: 80px; }
.col-label { font-size: 13px; color: #e0e2ed; }
.col-key { width: 200px; }
.col-act { width: 100px; text-align: right; }

.sc-cat-badge {
  font-size: 10px; padding: 2px 8px; border-radius: 10px;
  background: rgba(173, 199, 255, 0.1); color: #adc7ff;
}

.sc-kbd {
  display: inline-block; padding: 4px 10px; font-size: 12px;
  font-family: 'Space Grotesk', monospace; font-weight: 600;
  color: #e0e2ed; background: #1a1e2b;
  border: 1px solid #414754; border-radius: 4px;
  min-width: 60px; text-align: center;
}
.sc-kbd.waiting { color: #64748b; border-style: dashed; animation: pulse 1.2s ease-in-out infinite; }
.sc-kbd.recording { border-color: #4a8eff; box-shadow: 0 0 8px rgba(74, 142, 255, 0.3); }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.sc-record-wrap { display: flex; align-items: center; gap: 8px; }
.sc-rec-cancel {
  background: none; border: none; color: #8b90a0; font-size: 11px;
  cursor: pointer; padding: 2px 6px;
}
.sc-rec-cancel:hover { color: #ffb4ab; }

.sc-act-btn {
  background: none; border: 1px solid #414754; color: #8b90a0;
  font-size: 11px; padding: 3px 10px; border-radius: 4px;
  cursor: pointer; transition: all 0.15s; margin-left: 4px;
}
.sc-act-btn:hover { border-color: #adc7ff; color: #adc7ff; }
.sc-act-reset:hover { border-color: #ffb695; color: #ffb695; }
.sc-act-clear { color: #ffb4ab; border-color: transparent; }
.sc-act-clear:hover { background: rgba(255, 180, 171, 0.1); }

.sc-conflict {
  margin-top: 12px; padding: 8px 14px; border-radius: 6px;
  background: rgba(255, 180, 171, 0.08); border: 1px solid rgba(255, 180, 171, 0.25);
  font-size: 12px; color: #ffb4ab;
}
</style>
