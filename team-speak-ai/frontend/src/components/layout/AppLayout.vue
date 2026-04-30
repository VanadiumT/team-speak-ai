<template>
  <div class="layout">
    <!-- ═══ Header ═══ -->
    <header class="header">
      <div class="h-left">
        <span class="material-symbols-outlined h-logo" style="font-size: 22px;">smart_toy</span>
        <span class="h-title">TeamSpeak AI</span>
        <span class="h-version">v2.4.0-Stable</span>
        <template v-if="activeFlowId">
          <span class="h-sep">|</span>
          <span class="h-flow-name">{{ editorStore.flowMeta.name || '' }}</span>
        </template>
      </div>
      <div class="h-right">
        <!-- 流程模式（默认）: [流程设置] -->
        <template v-if="activeFlowId && !editorStore.editMode">
          <button class="top-btn primary-btn" @click="editorStore.enterEditMode()">
            <span class="material-symbols-outlined">tune</span> 流程设置
          </button>
        </template>
        <!-- 编辑模式: [流程模式] [保存] [撤销] [重做] -->
        <template v-if="activeFlowId && editorStore.editMode">
          <button class="top-btn ghost-btn" @click="editorStore.exitEditMode()">
            <span class="material-symbols-outlined">visibility</span> 流程模式
          </button>
          <span class="save-indicator" :class="saveState">{{ saveLabel }}</span>
          <button class="top-btn ghost-btn" :disabled="!editorStore.canUndo" @click="editorStore.undo()">
            <span class="material-symbols-outlined">undo</span>
          </button>
          <button class="top-btn ghost-btn" :disabled="!editorStore.canRedo" @click="editorStore.redo()">
            <span class="material-symbols-outlined">redo</span>
          </button>
        </template>
        <!-- 画布设置（编辑模式下右键画布或空面板打开） -->
        <button v-if="activeFlowId && editorStore.editMode" class="top-btn ghost-btn" @click="showCanvasSettings = true" title="画布设置">
          <span class="material-symbols-outlined">aspect_ratio</span>
        </button>
        <NotificationBell />
      </div>
    </header>

    <!-- ═══ Body ═══ -->
    <div class="body">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div v-if="sidebarTree.length === 0" class="sb-loading">加载中...</div>
        <nav class="sb-nav" v-else>
          <template v-for="section in sidebarTree" :key="section.id">
            <div class="sb-section">
              <div class="sb-section-row">
                <button class="sb-section-btn" @click="toggleSection(section.id)">
                  <span class="material-symbols-outlined sb-section-icon">{{ section.icon }}</span>
                  <span class="sb-section-name">{{ section.name }}</span>
                  <span class="material-symbols-outlined sb-chevron" :class="{ expanded: isExpanded(section.id) }">chevron_right</span>
                </button>
                <button class="sb-more-btn" @click.stop="openSidebarMenu($event, section)" title="更多操作">
                  <span class="material-symbols-outlined">more_vert</span>
                </button>
              </div>
              <div class="sb-children" v-if="isExpanded(section.id)">
                <template v-for="child in section.children" :key="child.id">
                  <!-- Flow ref -->
                  <div v-if="child.type === 'flow_ref'" class="sb-item-row">
                    <button
                      class="sb-item"
                      :class="{ active: activeFlowId === child.flow_id }"
                      @click="selectFlow(child.flow_id)"
                    >
                      <span class="material-symbols-outlined sb-item-icon">{{ child.icon }}</span>
                      <span class="sb-item-name">{{ child.name }}</span>
                      <span class="sb-run" v-if="isFlowRunning(child.flow_id)"></span>
                    </button>
                    <button class="sb-more-btn sb-more-sm" @click.stop="openSidebarMenu($event, child)" title="更多操作">
                      <span class="material-symbols-outlined">more_vert</span>
                    </button>
                  </div>
                  <!-- Sub group -->
                  <div v-else-if="child.type === 'group'" class="sb-subgroup">
                    <div class="sb-section-row sb-sub-row">
                      <button class="sb-section-btn sb-sub-btn" @click="toggleSection(child.id)">
                        <span class="material-symbols-outlined sb-section-icon">{{ child.icon }}</span>
                        <span class="sb-section-name">{{ child.name }}</span>
                        <span class="material-symbols-outlined sb-chevron" :class="{ expanded: isExpanded(child.id) }">chevron_right</span>
                      </button>
                      <button class="sb-more-btn sb-more-sm" @click.stop="openSidebarMenu($event, child)" title="更多操作">
                        <span class="material-symbols-outlined">more_vert</span>
                      </button>
                    </div>
                    <div class="sb-children sb-sub" v-if="isExpanded(child.id)">
                      <div v-for="gc in child.children" :key="gc.id" class="sb-item-row">
                        <button
                          v-if="gc.type === 'flow_ref'"
                          class="sb-item"
                          :class="{ active: activeFlowId === gc.flow_id }"
                          @click="selectFlow(gc.flow_id)"
                        >
                          <span class="material-symbols-outlined sb-item-icon">{{ gc.icon }}</span>
                          <span class="sb-item-name">{{ gc.name }}</span>
                        </button>
                        <button class="sb-more-btn sb-more-sm" @click.stop="openSidebarMenu($event, gc)" title="更多操作">
                          <span class="material-symbols-outlined">more_vert</span>
                        </button>
                      </div>
                    </div>
                  </div>
                  <!-- Action -->
                  <button
                    v-else-if="child.type === 'action'"
                    class="sb-item sb-action"
                    @click="onAction(child.id)"
                  >
                    <span class="material-symbols-outlined sb-item-icon">{{ child.icon }}</span>
                    <span class="sb-item-name">{{ child.name }}</span>
                  </button>
                </template>
              </div>
            </div>
          </template>
        </nav>

        <!-- Recent -->
        <div class="sb-recent">
          <div class="sb-recent-title">
            <div class="sb-recent-bar"></div>
            <span>最近访问</span>
          </div>
          <div class="sb-recent-list">
            <div v-for="r in recentFlows" :key="r.id" class="sb-recent-item" @click="selectFlow(r.id)">
              <span class="material-symbols-outlined" style="font-size:16px">{{ r.icon }}</span>
              <span>{{ r.name }}</span>
            </div>
            <div v-if="recentFlows.length === 0" class="sb-recent-empty">无最近记录</div>
          </div>
        </div>
      </aside>

      <!-- Content -->
      <main class="content">
        <!-- Floating Node Palette (edit mode only) -->
        <NodePalette v-if="activeFlowId && editorStore.editMode" />

        <PipelineView
          v-if="activeFlowId"
          :key="activeFlowId"
          :editMode="editorStore.editMode"
          :detailPanelOpen="!!selectedNode && editorStore.editMode"
          @select-node="onSelectNode"
        />
        <div v-else class="no-flow">
          <span class="material-symbols-outlined" style="font-size: 48px; opacity: 0.2;">account_tree</span>
          <p>选择左侧工作流以开始</p>
          <button class="new-flow-btn" @click="showFlowCreate = true">
            <span class="material-symbols-outlined">add</span> 新建工作流
          </button>
        </div>
      </main>

      <!-- Detail panel (edit mode only) -->
      <aside v-if="selectedNode && editorStore.editMode" class="detail-panel" id="detail-panel">
        <DynamicPanel :node="selectedNode" @close="selectedNode = null" />
      </aside>
    </div>

    <!-- ═══ Sidebar context menu ═══ -->
    <div v-if="contextMenu.visible" class="context-menu-overlay" @click="closeContextMenu"></div>
    <div v-if="contextMenu.visible" class="context-menu" :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }">
      <template v-for="item in contextMenu.items" :key="item.label">
        <div v-if="item.separator" class="ctx-sep"></div>
        <button v-else class="ctx-item" :class="{ danger: item.danger }" @click="item.action(); closeContextMenu()">
          <span class="material-symbols-outlined ctx-icon">{{ item.icon }}</span>
          {{ item.label }}
        </button>
      </template>
    </div>

    <!-- ═══ Flow Create Modal ═══ -->
    <div v-if="showFlowCreate" class="modal-overlay" @click.self="showFlowCreate = false">
      <div class="modal-card">
        <h3 class="modal-title"><span class="material-symbols-outlined">add_circle</span> 新建工作流</h3>
        <div class="modal-field">
          <label>名称 <span class="required">*</span></label>
          <input v-model="flowForm.name" class="modal-input" placeholder="例如：暗区锦标赛" maxlength="50" @keyup.enter="doCreateFlow" />
        </div>
        <div class="modal-field">
          <label>分组 <span class="hint">（用 / 分隔层级，如 游戏/暗区）</span></label>
          <input v-model="flowForm.group" class="modal-input" placeholder="留空为默认分组" maxlength="100" />
        </div>
        <div class="modal-field">
          <label>图标</label>
          <div class="icon-grid">
            <span v-for="ic in iconOptions" :key="ic" class="icon-option" :class="{ selected: flowForm.icon === ic }" @click="flowForm.icon = ic">
              <span class="material-symbols-outlined">{{ ic }}</span>
            </span>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showFlowCreate = false">取消</button>
          <button class="btn-save" @click="doCreateFlow" :disabled="!flowForm.name.trim()">创建并编辑</button>
        </div>
      </div>
    </div>

    <!-- ═══ Canvas Settings Modal ═══ -->
    <div v-if="showCanvasSettings" class="modal-overlay" @click.self="showCanvasSettings = false">
      <div class="modal-card modal-sm">
        <h3 class="modal-title"><span class="material-symbols-outlined">aspect_ratio</span> 画布设置</h3>
        <div class="modal-field-row">
          <label>宽度 (px)</label>
          <input v-model.number="canvasForm.width" type="number" class="modal-input" min="800" max="5000" />
        </div>
        <div class="modal-field-row">
          <label>高度 (px)</label>
          <input v-model.number="canvasForm.height" type="number" class="modal-input" min="600" max="5000" />
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showCanvasSettings = false">取消</button>
          <button class="btn-save" @click="doSaveCanvas">保存</button>
        </div>
      </div>
    </div>

    <!-- ═══ Footer ═══ -->
    <BottomStatusBar />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'
import { useEditorStore } from '@/stores/editor.js'
import { useExecutionStore } from '@/stores/execution.js'
import { useNotificationsStore } from '@/stores/notifications.js'
import { useConnectionStore } from '@/stores/connection.js'
import PipelineView from '@/components/pipeline/PipelineView.vue'
import DynamicPanel from '@/components/panels/DynamicPanel.vue'
import NodePalette from '@/components/pipeline/NodePalette.vue'
import BottomStatusBar from '@/components/layout/BottomStatusBar.vue'
import NotificationBell from '@/components/layout/NotificationBell.vue'

const editorStore = useEditorStore()
const executionStore = useExecutionStore()
const notificationsStore = useNotificationsStore()
const connectionStore = useConnectionStore()

const sidebarTree = ref([])
const expandedSections = ref(new Set())
const activeFlowId = ref(null)
const selectedNode = ref(null)
const showFlowCreate = ref(false)
const showCanvasSettings = ref(false)

const flowForm = reactive({ name: '', group: '', icon: 'sports_esports' })
const canvasForm = reactive({ width: 1700, height: 1250 })

const iconOptions = [
  'sports_esports', 'account_tree', 'smart_toy', 'psychology', 'mic',
  'document_scanner', 'camera', 'headset_mic', 'record_voice_over',
  'terminal', 'hub', 'sensors', 'volume_up', 'history_edu', 'upload_file',
]

// ── Save indicator ──
const saveState = ref('saved')
const saveLabel = computed(() => {
  return { saved: '已保存', saving: '保存中...', unsaved: '未保存' }[saveState.value] || ''
})

// ── Recent flows (localStorage) ──
const recentFlows = ref([])
function updateRecent(flowId, flowName, flowIcon) {
  const stored = JSON.parse(localStorage.getItem('recent-flows') || '[]')
  const filtered = stored.filter((r) => r.id !== flowId)
  filtered.unshift({ id: flowId, name: flowName, icon: flowIcon })
  recentFlows.value = filtered.slice(0, 5)
  localStorage.setItem('recent-flows', JSON.stringify(recentFlows.value))
}

// ── Sidebar ──
function isExpanded(id) { return expandedSections.value.has(id) }
function toggleSection(id) {
  if (expandedSections.value.has(id)) {
    expandedSections.value.delete(id)
  } else {
    expandedSections.value.add(id)
  }
  expandedSections.value = new Set(expandedSections.value)
}

async function selectFlow(flowId) {
  activeFlowId.value = flowId
  selectedNode.value = null
  editorStore.exitEditMode()
  try {
    await editorStore.loadFlow(flowId)
    const meta = editorStore.flowMeta
    updateRecent(flowId, meta.name || '', meta.icon || '')
  } catch (e) {
    console.error('Failed to load flow:', e)
  }
}

function isFlowRunning(flowId) {
  return executionStore.status === 'running' && editorStore.flowId === flowId
}

function onAction(actionId) {
  if (actionId === 'action:new_flow') {
    showFlowCreate.value = true
  }
}

function onSelectNode(nodeId) {
  if (!editorStore.editMode) return
  selectedNode.value = editorStore.nodes.find((n) => n.id === nodeId) || null
}

// ── Flow Create ──
async function doCreateFlow() {
  const name = flowForm.name.trim()
  if (!name) return
  const group = flowForm.group.trim()
  const icon = flowForm.icon
  await editorStore.createFlow(name, group, icon)
  showFlowCreate.value = false
  flowForm.name = ''
  flowForm.group = ''
  flowForm.icon = 'sports_esports'
}

// ── Canvas Settings ──
function doSaveCanvas() {
  editorStore.flowMeta.canvas = { width: canvasForm.width, height: canvasForm.height }
  pipelineSocket.sendCommand(editorStore.flowId, 'flow.update', {
    canvas: { width: canvasForm.width, height: canvasForm.height },
  }).catch(() => {})
  showCanvasSettings.value = false
}

watch(() => editorStore.flowMeta.canvas, (c) => {
  if (c) { canvasForm.width = c.width; canvasForm.height = c.height }
})

// ── Sidebar ⋮ context menu ──
const contextMenu = reactive({ visible: false, x: 0, y: 0, items: [] })

function openSidebarMenu(event, node) {
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY

  const isRoot = node.type === 'section' && node.id === 'workflows'
  const isGroup = node.type === 'group'
  const isFlow = node.type === 'flow_ref'

  if (isRoot) {
    contextMenu.items = [
      { icon: 'add', label: '新建工作流', action: () => { showFlowCreate.value = true } },
      { separator: true },
      { icon: 'download', label: '导出全部', action: () => {} },
      { icon: 'upload', label: '导入工作流', action: () => {} },
    ]
  } else if (isGroup) {
    contextMenu.items = [
      { icon: 'add', label: '新建子分组', action: () => {} },
      { icon: 'edit', label: '重命名', action: () => {} },
      { separator: true },
      { icon: 'download', label: '导出该分组', action: () => {} },
      { icon: 'upload', label: '导入到该分组', action: () => {} },
    ]
  } else if (isFlow) {
    const flowId = node.flow_id
    contextMenu.items = [
      { icon: 'edit', label: '重命名', action: () => {} },
      { icon: 'content_copy', label: '复制', action: () => {} },
      { separator: true },
      { icon: 'download', label: '导出', action: () => {} },
      { icon: 'upload', label: '导入替换', action: () => {} },
      { separator: true },
      { icon: 'drive_file_move', label: '移动到分组', action: () => {} },
      { separator: true },
      { icon: 'block', label: '禁用', action: () => {} },
      { separator: true },
      { icon: 'delete', label: '删除', danger: true, action: () => { if (confirm('确认删除此工作流？此操作不可恢复。')) { pipelineSocket.sendCommand(flowId, 'flow.delete', {}) } } },
    ]
  }
  contextMenu.visible = true
}

function closeContextMenu() {
  contextMenu.visible = false
}

// ── Lifecycle ──
onMounted(() => {
  editorStore.init()
  executionStore.init()
  notificationsStore.init()
  connectionStore.init()

  pipelineSocket.on('sidebar.tree', ({ groups }) => {
    sidebarTree.value = groups || []
    groups?.forEach((s) => {
      expandedSections.value.add(s.id)
      s.children?.forEach((c) => {
        if (c.type === 'group') expandedSections.value.add(c.id)
      })
    })
  })

  pipelineSocket.on('flow.loaded', ({ flow }) => {
    editorStore.onFlowLoaded({ flow })
  })

  pipelineSocket.on('flow.created', () => {
    pipelineSocket.sendCommand('_system', 'flow.list', {})
  })

  // Load recent flows
  recentFlows.value = JSON.parse(localStorage.getItem('recent-flows') || '[]').slice(0, 5)

  // Keyboard: Delete selected node
  window.addEventListener('keydown', (e) => {
    if (!editorStore.editMode) return
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
    if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNode.value) {
      e.preventDefault()
      editorStore.deleteNode(selectedNode.value.id)
      selectedNode.value = null
    }
  })

  pipelineSocket.connect()
})

onUnmounted(() => {
  editorStore.flushPendingUpdates()
  pipelineSocket.disconnect()
})
</script>

<style scoped>
.layout {
  display: flex; flex-direction: column;
  height: 100vh;
  background: #10131b;
  color: #e0e2ed;
  font-family: 'Inter', sans-serif;
}

/* ── Header ── */
.header {
  display: flex; align-items: center; justify-content: space-between;
  height: 56px; padding: 0 24px;
  background: rgba(2, 6, 23, 0.8);
  backdrop-filter: blur(24px);
  border-bottom: 1px solid rgba(65, 71, 84, 0.5);
  z-index: 50; flex-shrink: 0;
  position: fixed; top: 0; left: 0; width: 100%;
}

.h-left { display: flex; align-items: center; gap: 12px; }
.h-logo { color: #4a8eff; }
.h-title { font-size: 18px; font-weight: 700; letter-spacing: -0.02em; }
.h-version {
  font-size: 10px; font-family: 'Space Grotesk', sans-serif;
  color: #64748b; font-weight: 500; letter-spacing: 0.05em;
  align-self: flex-end; margin-bottom: 4px; margin-left: 4px;
}
.h-sep { color: #414754; margin: 0 4px; }
.h-flow-name { font-size: 13px; color: #adc7ff; font-weight: 500; }

.h-right { display: flex; align-items: center; gap: 8px; }

/* ── Top nav buttons ── */
.top-btn {
  padding: 6px 12px; border-radius: 6px; font-size: 11px;
  font-family: 'Space Grotesk', sans-serif; font-weight: 500;
  letter-spacing: 0.05em; cursor: pointer;
  border: 1px solid transparent; transition: all 0.15s;
  display: flex; align-items: center; gap: 4px;
}
.top-btn.primary-btn { background: #adc7ff; color: #002e68; border-color: #adc7ff; }
.top-btn.primary-btn:hover { background: #d8e2ff; }
.top-btn.ghost-btn { background: transparent; color: #8b90a0; border-color: #414754; }
.top-btn.ghost-btn:hover { color: #c1c6d7; border-color: #8b90a0; }
.top-btn.ghost-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.save-indicator {
  display: flex; align-items: center; gap: 4px;
  font-size: 10px; font-family: 'Space Grotesk', sans-serif;
  letter-spacing: 0.05em; padding: 4px 8px;
}
.save-indicator.saved { color: #4edea3; }
.save-indicator.saving { color: #ffb695; }
.save-indicator.unsaved { color: #8b90a0; }

/* ── Body ── */
.body {
  display: flex; flex: 1;
  padding-top: 56px;
  overflow: hidden;
}

/* ── Sidebar ── */
.sidebar {
  width: 256px; flex-shrink: 0;
  position: fixed; left: 0; top: 56px;
  height: calc(100vh - 88px);
  background: rgba(2, 6, 23, 0.9);
  backdrop-filter: blur(40px);
  border-right: 1px solid rgba(65, 71, 84, 0.5);
  z-index: 40; overflow-y: auto;
  display: flex; flex-direction: column;
}

.sb-loading {
  padding: 24px 16px; text-align: center;
  font-size: 13px; color: #94a3b8;
}

.sb-nav { flex: 1; padding: 16px 0; }

.sb-section { margin-bottom: 4px; }

.sb-section-row {
  display: flex; align-items: center;
  padding-right: 4px;
}
.sb-sub-row { padding-left: 16px; }

.sb-section-btn {
  display: flex; align-items: center; gap: 10px;
  flex: 1; padding: 8px 12px;
  background: none; border: none;
  color: #cbd5e1; font-size: 14px; font-weight: 500;
  cursor: pointer; text-align: left;
  transition: background 0.15s;
}
.sb-section-btn:hover { background: rgba(15, 23, 42, 0.5); }

.sb-section-icon { font-size: 18px; color: #94a3b8; }
.sb-section-name { flex: 1; }

.sb-chevron {
  font-size: 16px; color: #94a3b8;
  transition: transform 0.2s ease;
}
.sb-chevron.expanded { transform: rotate(90deg); }

.sb-children { padding-left: 4px; }
.sb-sub { padding-left: 12px; }
.sb-sub-btn { padding-left: 28px; font-size: 13px; }

.sb-item-row {
  display: flex; align-items: center;
  padding-right: 4px;
}

.sb-item {
  display: flex; align-items: center; gap: 8px;
  flex: 1; padding: 8px 12px 8px 24px;
  background: none; border: none;
  color: #94a3b8; font-size: 11px;
  cursor: pointer; text-align: left;
  transition: all 0.15s;
  border-left: 2px solid transparent;
}
.sb-item:hover { background: rgba(15, 23, 42, 0.5); color: #cbd5e1; }
.sb-item.active {
  color: #adc7ff;
  border-left-color: #adc7ff;
  background: rgba(173, 199, 255, 0.05);
}

.sb-item-icon { font-size: 16px; }
.sb-item-name { flex: 1; }
.sb-action .sb-item-icon { font-size: 14px; }

.sb-more-btn {
  width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; border-radius: 4px;
  cursor: pointer; color: #64748b; flex-shrink: 0;
  opacity: 0; transition: opacity 0.15s, color 0.15s;
}
.sb-section-row:hover .sb-more-btn,
.sb-item-row:hover .sb-more-btn { opacity: 1; }
.sb-more-btn:hover { color: #cbd5e1; background: rgba(15, 23, 42, 0.5); }
.sb-more-sm { width: 20px; height: 20px; }
.sb-more-sm .material-symbols-outlined { font-size: 14px; }

.sb-run {
  width: 6px; height: 6px; border-radius: 50%;
  background: #4edea3;
  box-shadow: 0 0 8px rgba(78, 222, 163, 0.6);
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ── Recent ── */
.sb-recent {
  border-top: 1px solid rgba(65, 71, 84, 0.5);
  padding: 16px 12px;
  margin-top: auto;
}
.sb-recent-title {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px;
}
.sb-recent-bar {
  width: 4px; height: 12px; border-radius: 2px;
  background: #4a8eff;
  box-shadow: 0 0 8px rgba(74, 142, 255, 0.5);
}
.sb-recent-title span {
  font-size: 10px; font-weight: 700; font-family: 'Space Grotesk', sans-serif;
  color: rgba(173, 199, 255, 0.8);
  text-transform: uppercase; letter-spacing: 0.2em;
}
.sb-recent-item {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 8px; border-radius: 4px;
  font-size: 11px; color: #94a3b8; cursor: pointer;
  transition: all 0.15s;
}
.sb-recent-item:hover { background: rgba(15, 23, 42, 0.5); color: #cbd5e1; }
.sb-recent-empty { font-size: 10px; color: #475569; padding: 4px 8px; }

/* ── Content ── */
.content { flex: 1; overflow: hidden; position: relative; }

.no-flow {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; gap: 16px;
  color: #64748b; font-size: 14px;
}

.new-flow-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 20px; border-radius: 8px;
  background: #adc7ff; color: #002e68;
  font-size: 13px; font-weight: 600; cursor: pointer;
  border: none; transition: background 0.15s;
}
.new-flow-btn:hover { background: #d8e2ff; }

/* ── Detail Panel ── */
.detail-panel {
  width: 320px; flex-shrink: 0;
  background: #020617;
  border-left: 1px solid rgba(65, 71, 84, 0.3);
  overflow-y: auto;
  position: fixed; right: 0; top: 56px; bottom: 32px;
  z-index: 30;
}

/* ── Context Menu ── */
.context-menu-overlay {
  position: fixed; inset: 0; z-index: 90;
}
.context-menu {
  position: fixed; z-index: 100;
  background: #181c23; border: 1px solid #414754;
  border-radius: 6px; min-width: 160px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  padding: 4px 0;
}
.ctx-item {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 8px 14px;
  background: none; border: none;
  color: #c1c6d7; font-size: 11px; cursor: pointer;
  transition: background 0.1s;
}
.ctx-item:hover { background: #272a32; color: #e0e2ed; }
.ctx-item.danger { color: #ffb4ab; }
.ctx-item.danger:hover { background: rgba(255, 180, 171, 0.1); }
.ctx-icon { font-size: 14px; }
.ctx-sep { height: 1px; background: #414754; margin: 4px 0; }

/* ── Modal ── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 200;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}
.modal-card {
  background: rgba(28, 32, 39, 0.95);
  backdrop-filter: blur(12px);
  border-radius: 12px; border: 1px solid rgba(65, 71, 84, 0.5);
  padding: 24px; width: 480px; max-width: 90vw;
}
.modal-sm { width: 360px; }
.modal-title {
  font-size: 18px; font-weight: 600; color: #e0e2ed;
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 20px;
}
.modal-title .material-symbols-outlined { color: #4a8eff; }
.modal-field { margin-bottom: 14px; }
.modal-field label { display: block; font-size: 12px; color: #c1c6d7; margin-bottom: 4px; }
.modal-field .required { color: #ffb4ab; }
.modal-field .hint { color: #64748b; font-size: 10px; font-weight: 400; }
.modal-field-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.modal-field-row label { font-size: 12px; color: #c1c6d7; white-space: nowrap; }
.modal-input {
  width: 100%; padding: 8px 12px;
  background: #1c2027; border: 1px solid #414754; border-radius: 8px;
  color: #e0e2ed; font-size: 13px; outline: none;
  font-family: 'Inter', sans-serif;
}
.modal-input:focus { border-color: #adc7ff; box-shadow: 0 0 0 1px rgba(173, 199, 255, 0.3); }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.btn-cancel {
  padding: 8px 16px; border-radius: 8px;
  background: #31353d; color: #e0e2ed; border: 1px solid #414754;
  font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.15s;
}
.btn-cancel:hover { background: #3d414a; }
.btn-save {
  padding: 8px 16px; border-radius: 8px;
  background: #adc7ff; color: #002e68; border: none;
  font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.15s;
}
.btn-save:hover { background: #d8e2ff; }
.btn-save:disabled { opacity: 0.4; cursor: not-allowed; }

.icon-grid {
  display: flex; flex-wrap: wrap; gap: 6px;
}
.icon-option {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px; border: 1px solid rgba(65, 71, 84, 0.5);
  cursor: pointer; color: #94a3b8; transition: all 0.15s;
}
.icon-option:hover { background: rgba(173, 199, 255, 0.05); border-color: #adc7ff; }
.icon-option.selected { background: rgba(173, 199, 255, 0.12); border-color: #adc7ff; color: #adc7ff; }
.icon-option .material-symbols-outlined { font-size: 18px; }
</style>
