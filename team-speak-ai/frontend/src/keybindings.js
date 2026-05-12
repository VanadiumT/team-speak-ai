/**
 * 快捷键集中配置
 *
 * 所有快捷键的默认定义 + localStorage 持久化的用户自定义。
 * 使用 useKeybindings() 获取合并后的有效快捷键表。
 */

import { ref, watch } from 'vue'

const STORAGE_KEY = 'team_speak_ai_keybindings'

// ── 默认快捷键定义 ──
const DEFAULT_BINDINGS = [
  { id: 'node.duplicate',   label: '复制节点',     category: '画布',  ctrl: true,   key: 'd' },
  { id: 'node.delete',      label: '删除节点',     category: '画布',  ctrl: false,  key: 'Delete' },
  { id: 'connection.delete',label: '删除连线',     category: '画布',  ctrl: false,  key: 'Delete' },
  { id: 'canvas.deselect',  label: '取消选择',     category: '画布',  ctrl: false,  key: 'Escape' },
]

// ── 格式化快捷键显示 ──
export function formatShortcut(binding) {
  const parts = []
  if (binding.ctrl) parts.push('Ctrl')
  if (binding.shift) parts.push('Shift')
  if (binding.alt) parts.push('Alt')
  if (binding.meta) parts.push('Meta')
  const key = binding.key === ' ' ? 'Space' : binding.key
  parts.push(key.length === 1 ? key.toUpperCase() : key)
  return parts.join(' + ')
}

// ── 从 event 解析快捷键 ──
export function parseKeyEvent(e) {
  if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) return null
  return {
    ctrl: e.ctrlKey || e.metaKey,
    shift: e.shiftKey,
    alt: e.altKey,
    meta: e.metaKey,
    key: e.key,
  }
}

// ── 比较两个 binding 是否相等 ──
export function bindingMatch(a, b) {
  return a.key === b.key
    && (a.ctrl || false) === (b.ctrl || false)
    && (a.shift || false) === (b.shift || false)
    && (a.alt || false) === (b.alt || false)
}

// ── 加载用户自定义 ──
function loadUserBindings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch { return {} }
}

// ── 保存用户自定义 ──
function saveUserBindings(map) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map))
}

// ── 响应式快捷键表 ──
const bindings = ref(loadBindings())

function loadBindings() {
  const userMap = loadUserBindings()
  return DEFAULT_BINDINGS.map((def) => {
    const override = userMap[def.id]
    return override ? { ...def, ...override } : { ...def }
  })
}

// ── 暴露的 composable ──
let _instance = null

export function useKeybindings() {
  if (_instance) return _instance

  // 根据 keydown event 查找匹配的 action
  function matchBinding(e) {
    const parsed = parseKeyEvent(e)
    if (!parsed) return null
    return bindings.value.find((b) => bindingMatch(b, parsed))
  }

  // 检查 event 是否匹配指定 id 的快捷键
  function matchId(e, id) {
    const b = bindings.value.find((x) => x.id === id)
    if (!b || !b.key) return false
    const parsed = parseKeyEvent(e)
    if (!parsed) return false
    return bindingMatch(b, parsed)
  }

  // 更新某个快捷键
  function updateBinding(id, newBinding) {
    const idx = bindings.value.findIndex((b) => b.id === id)
    if (idx < 0) return
    bindings.value[idx] = { ...bindings.value[idx], ...newBinding }

    // 持久化到 localStorage（只存非默认的）
    const userMap = loadUserBindings()
    const def = DEFAULT_BINDINGS.find((d) => d.id === id)
    if (def && bindingMatch(def, bindings.value[idx])) {
      delete userMap[id]
    } else {
      userMap[id] = {
        ctrl: bindings.value[idx].ctrl || false,
        shift: bindings.value[idx].shift || false,
        alt: bindings.value[idx].alt || false,
        key: bindings.value[idx].key,
      }
    }
    saveUserBindings(userMap)
  }

  // 恢复默认
  function resetBinding(id) {
    const def = DEFAULT_BINDINGS.find((d) => d.id === id)
    if (!def) return
    updateBinding(id, { ctrl: def.ctrl || false, shift: false, alt: false, key: def.key })
  }

  // 全部恢复默认
  function resetAll() {
    localStorage.removeItem(STORAGE_KEY)
    bindings.value = DEFAULT_BINDINGS.map((d) => ({ ...d }))
  }

  _instance = { bindings, matchBinding, matchId, updateBinding, resetBinding, resetAll }
  return _instance
}
