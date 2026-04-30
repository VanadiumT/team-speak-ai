<template>
  <div class="node-palette" :class="{ collapsed: isCollapsed }">
    <div class="np-header" @click="isCollapsed = !isCollapsed">
      <span class="np-title">工具面板</span>
      <span class="material-symbols-outlined np-toggle">{{ isCollapsed ? 'add' : 'remove' }}</span>
    </div>
    <div v-if="!isCollapsed" class="np-body">
      <template v-for="(types, category) in categorizedTypes" :key="category">
        <div class="np-cat-label">{{ category }}</div>
        <div
          v-for="nt in types" :key="nt.type"
          class="np-card"
          :style="{ borderLeftColor: colorMap[nt.color] || '#8b90a0' }"
          @mousedown.prevent="startDrag($event, nt)"
        >
          <span class="material-symbols-outlined np-icon" :style="{ color: colorMap[nt.color] }">{{ nt.icon }}</span>
          <span class="np-name">{{ nt.name }}</span>
          <span class="np-ports">{{ nt.ports?.inputs?.length || 0 }}↘{{ nt.ports?.outputs?.length || 0 }}</span>
        </div>
      </template>
    </div>

    <Teleport to="body">
      <div v-if="ghost" class="drag-ghost" :style="{ left: ghost.x + 'px', top: ghost.y + 'px' }">
        <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;margin-right:4px;">{{ ghost.icon }}</span>
        {{ ghost.name }}
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useEditorStore } from '@/stores/editor.js'

const editorStore = useEditorStore()

const isCollapsed = ref(false)
const ghost = ref(null)

const colorMap = { primary: '#adc7ff', secondary: '#4edea3', tertiary: '#ef6719', outline: '#8b90a0' }

const categoryOrder = ['输入', '处理', '音频', '输出']
const categoryMap = {
  input_image: '输入', ts_input: '输入',
  ocr: '处理', context_build: '处理', llm: '处理',
  stt_listen: '音频', stt_history: '音频',
  tts: '输出', ts_output: '输出',
}

const categorizedTypes = computed(() => {
  const cats = {}
  editorStore.nodeTypes.forEach((nt) => {
    const cat = categoryMap[nt.type] || '其他'
    if (!cats[cat]) cats[cat] = []
    cats[cat].push(nt)
  })
  const result = {}
  categoryOrder.forEach((c) => { if (cats[c]) result[c] = cats[c] })
  Object.keys(cats).forEach((c) => { if (!result[c]) result[c] = cats[c] })
  return result
})

let dragActive = false

function startDrag(e, nodeType) {
  if (dragActive) return  // 防止重复拖拽
  const nt = nodeType
  const startX = e.clientX
  const startY = e.clientY
  let hasMoved = false

  ghost.value = { x: e.clientX, y: e.clientY, icon: nt.icon, name: nt.name }

  const onMove = (ev) => {
    const dx = Math.abs(ev.clientX - startX)
    const dy = Math.abs(ev.clientY - startY)
    if (dx > 3 || dy > 3) {
      hasMoved = true
      dragActive = true
    }
    if (!hasMoved) return
    ghost.value = { ...ghost.value, x: ev.clientX, y: ev.clientY }

    const canvas = document.querySelector('.pipeline-canvas')
    if (canvas) {
      const rect = canvas.getBoundingClientRect()
      const over = ev.clientX > rect.left && ev.clientX < rect.right &&
                   ev.clientY > rect.top && ev.clientY < rect.bottom
      const el = document.querySelector('.drag-ghost')
      if (el) el.style.borderColor = over ? '#4edea3' : '#4a8eff'
    }
  }

  const onUp = (ev) => {
    if (hasMoved) {
      const canvas = document.querySelector('.pipeline-canvas')
      if (canvas) {
        const rect = canvas.getBoundingClientRect()
        const over = ev.clientX > rect.left && ev.clientX < rect.right &&
                     ev.clientY > rect.top && ev.clientY < rect.bottom
        if (over) {
          const zoom = 1.0
          const x = Math.max(32, (ev.clientX - rect.left + canvas.scrollLeft) / zoom - 110)
          const y = Math.max(32, (ev.clientY - rect.top + canvas.scrollTop) / zoom - 20)
          editorStore.createNode(nt.type, { x: Math.round(x), y: Math.round(y) })
        }
      }
    }
    ghost.value = null
    dragActive = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }

  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}
</script>

<style scoped>
.node-palette {
  position: fixed;
  left: 272px; top: 72px;
  width: 200px; z-index: 50;
  background: rgba(2, 6, 23, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(65, 71, 84, 0.5);
  border-radius: 8px;
  overflow: hidden;
}

.node-palette.collapsed { width: auto; }

.np-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; cursor: pointer;
  font-size: 12px; font-weight: 600; color: #cbd5e1;
  border-bottom: 1px solid rgba(65, 71, 84, 0.3);
}
.np-toggle { font-size: 16px; color: #94a3b8; }

.np-body { padding: 8px; max-height: calc(100vh - 200px); overflow-y: auto; }

.np-cat-label {
  font-size: 9px; font-family: 'Space Grotesk', sans-serif;
  font-weight: 500; text-transform: uppercase;
  color: rgba(139, 144, 160, 0.6);
  letter-spacing: 0.1em;
  padding: 8px 4px 4px;
}
.np-cat-label:first-child { padding-top: 0; }

.np-card {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px; border-radius: 6px;
  cursor: grab; user-select: none;
  transition: all 0.15s;
  border: 1px solid rgba(65, 71, 84, 0.3);
  border-left: 3px solid;
  background: rgba(24, 28, 35, 0.6);
  margin-bottom: 4px;
}
.np-card:hover { background: rgba(28, 32, 39, 0.9); border-color: rgba(65, 71, 84, 0.6); }
.np-card:active { cursor: grabbing; transform: scale(0.96); }

.np-icon { font-size: 16px; flex-shrink: 0; }
.np-name { flex: 1; font-size: 11px; color: #c1c6d7; }
.np-ports { font-size: 9px; color: rgba(139, 144, 160, 0.4); font-family: 'Space Grotesk', sans-serif; }

.drag-ghost {
  position: fixed; pointer-events: none; z-index: 9999;
  transform: translate(-50%, -50%);
  padding: 8px 14px; border-radius: 6px;
  font-size: 12px; font-family: 'Space Grotesk', sans-serif;
  font-weight: 500; color: #e0e2ed; white-space: nowrap;
  background: rgba(28, 32, 39, 0.95);
  border: 1px dashed #4a8eff;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}
</style>
