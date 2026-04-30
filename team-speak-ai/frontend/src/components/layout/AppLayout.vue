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
                <button v-if="section.id === 'workflows'" class="sb-more-btn" @click.stop="openSidebarMenu($event, section)" title="更多操作">
                  <span class="material-symbols-outlined">more_vert</span>
                </button>
              </div>
              <div class="sb-children" v-if="isExpanded(section.id)">
                <SidebarTreeNode
                  v-for="child in section.children"
                  :key="child.id"
                  :node="child"
                  :activeFlowId="activeFlowId"
                  :expandedSet="expandedSections"
                  :runningFlowIds="runningFlowIds"
                  @select-flow="selectFlow"
                  @toggle="toggleSection"
                  @menu="openSidebarMenu"
                  @action="onAction"
                />
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

    <!-- ═══ Rename Modal ═══ -->
    <div v-if="renameDialog.visible" class="modal-overlay" @click.self="renameDialog.visible = false">
      <div class="modal-card modal-sm">
        <h3 class="modal-title"><span class="material-symbols-outlined">edit</span> {{ renameDialog.title }}</h3>
        <div class="modal-field">
          <label>名称 <span class="required">*</span></label>
          <input v-model="renameDialog.value" class="modal-input" maxlength="50" @keyup.enter="doRename" />
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="renameDialog.visible = false">取消</button>
          <button class="btn-save" @click="doRename" :disabled="!renameDialog.value.trim()">确认</button>
        </div>
      </div>
    </div>

    <!-- ═══ Move-to-Group Modal ═══ -->
    <div v-if="moveDialog.visible" class="modal-overlay" @click.self="moveDialog.visible = false">
      <div class="modal-card modal-sm">
        <h3 class="modal-title"><span class="material-symbols-outlined">drive_file_move</span> 移动到分组</h3>
        <div class="modal-field">
          <label>目标分组 <span class="hint">（用 / 分隔层级，如 游戏/暗区）</span></label>
          <input v-model="moveDialog.groupPath" class="modal-input" placeholder="留空为默认分组" maxlength="100" @keyup.enter="doMoveToGroup" />
        </div>
        <div class="modal-field" v-if="availableGroups.length > 0">
          <label>现有分组</label>
          <div class="group-list">
            <button v-for="g in availableGroups" :key="g" class="group-chip" @click="moveDialog.groupPath = g">{{ g || '(默认)' }}</button>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="moveDialog.visible = false">取消</button>
          <button class="btn-save" @click="doMoveToGroup">移动</button>
        </div>
      </div>
    </div>

    <!-- ═══ New Group (Directory) Modal ═══ -->
    <div v-if="showGroupCreate" class="modal-overlay" @click.self="showGroupCreate = false">
      <div class="modal-card modal-sm">
        <h3 class="modal-title"><span class="material-symbols-outlined">create_new_folder</span> 新建目录</h3>
        <div class="modal-field">
          <label>目录路径 <span class="required">*</span> <span class="hint">（用 / 分隔层级，如 游戏/暗区）</span></label>
          <input v-model="groupForm.path" class="modal-input" placeholder="例如：游戏/暗区" maxlength="100" @keyup.enter="doCreateGroup" />
        </div>
        <div class="modal-field">
          <label>图标</label>
          <div class="icon-grid">
            <span v-for="ic in folderIconOptions" :key="ic" class="icon-option" :class="{ selected: groupForm.icon === ic }" @click="groupForm.icon = ic">
              <span class="material-symbols-outlined">{{ ic }}</span>
            </span>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showGroupCreate = false">取消</button>
          <button class="btn-save" @click="doCreateGroup" :disabled="!groupForm.path.trim()">创建</button>
        </div>
      </div>
    </div>

    <!-- ═══ Hidden file inputs for import ═══ -->
    <input ref="importInput" type="file" accept=".json" style="display:none" @change="onImportFile" />
    <input ref="importGroupInput" type="file" accept=".zip" style="display:none" @change="onImportGroupFile" />

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
import SidebarTreeNode from '@/components/layout/SidebarTreeNode.vue'

const editorStore = useEditorStore()
const executionStore = useExecutionStore()
const notificationsStore = useNotificationsStore()
const connectionStore = useConnectionStore()

const sidebarTree = ref([])
const expandedSections = ref(new Set())
const activeFlowId = ref(null)
const selectedNode = ref(null)
const showFlowCreate = ref(false)
const showGroupCreate = ref(false)
const showCanvasSettings = ref(false)
const importInput = ref(null)
const importGroupInput = ref(null)

const flowForm = reactive({ name: '', group: '', icon: 'sports_esports' })
const groupForm = reactive({ path: '', icon: 'folder' })
const canvasForm = reactive({ width: 1700, height: 1250 })

// Rename dialog
const renameDialog = reactive({ visible: false, title: '', value: '', flowId: '', groupPath: '' })

// Move-to-group dialog
const moveDialog = reactive({ visible: false, groupPath: '', flowId: '' })

// Import group target path
const importGroupTarget = ref('')

// Collect all available group paths from sidebar tree
const availableGroups = computed(() => {
  const paths = new Set()
  function walk(nodes, prefix = '') {
    for (const n of nodes) {
      if (n.type === 'group') {
        const path = prefix ? prefix + '/' + n.name : n.name
        paths.add(path)
        if (n.children) walk(n.children, path)
      }
    }
  }
  for (const s of sidebarTree.value) {
    if (s.children) walk(s.children)
  }
  return [...paths].sort()
})

const iconOptions = [
  'sports_esports', 'account_tree', 'smart_toy', 'psychology', 'mic',
  'document_scanner', 'camera', 'headset_mic', 'record_voice_over',
  'terminal', 'hub', 'sensors', 'volume_up', 'history_edu', 'upload_file',
]

const folderIconOptions = [
  'folder', 'folder_open', 'create_new_folder', 'topic', 'label',
  'bookmark', 'bookmarks', 'category', 'inventory_2', 'work',
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

const runningFlowIds = computed(() => {
  const ids = new Set()
  if (executionStore.status === 'running' && editorStore.flowId) {
    ids.add(editorStore.flowId)
  }
  return ids
})

function onAction(actionId) {
  // System settings actions — handled by router or future implementation
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

// ── Group Create ──
async function doCreateGroup() {
  const path = groupForm.path.trim()
  if (!path) return
  await pipelineSocket.sendCommand('_system', 'flow.create_group', { group_path: path }).catch(() => {})
  showGroupCreate.value = false
  groupForm.path = ''
  groupForm.icon = 'folder'
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

/** Get full group path for a node. Group IDs are already full paths like "游戏/暗区". */
function getGroupPath(node) {
  if (node.type === 'group') return node.id || ''
  return ''
}

function openSidebarMenu(event, node) {
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY

  const isRoot = node.type === 'section' && node.id === 'workflows'
  const isGroup = node.type === 'group'
  const isFlow = node.type === 'flow_ref'

  if (isRoot) {
    contextMenu.items = [
      { icon: 'add', label: '新建工作流', action: () => { showFlowCreate.value = true } },
      { icon: 'create_new_folder', label: '新建目录', action: () => { showGroupCreate.value = true } },
      { separator: true },
      { icon: 'download', label: '导出全部 (ZIP)', action: () => { pipelineSocket.sendCommand('_system', 'flow.export_group', {}).catch(() => {}) } },
      { icon: 'upload', label: '导入工作流 (.json)', action: () => { importInput.value?.click() } },
      { icon: 'upload', label: '导入到该分组 (.zip)', action: () => { const target = prompt('请输入目标分组路径（留空为根目录）：'); importGroupTarget.value = target || ''; importGroupInput.value?.click() } },
    ]
  } else if (isGroup) {
    const groupPath = getGroupPath(node)
    contextMenu.items = [
      { icon: 'add', label: '新建工作流', action: () => { flowForm.group = groupPath || ''; showFlowCreate.value = true } },
      { icon: 'create_new_folder', label: '新建子目录', action: () => { groupForm.path = groupPath ? groupPath + '/' : ''; showGroupCreate.value = true } },
      { icon: 'edit', label: '重命名', action: () => { renameDialog.title = '重命名分组'; renameDialog.value = node.name; renameDialog.flowId = null; renameDialog.groupPath = groupPath; renameDialog.visible = true } },
      { separator: true },
      { icon: 'download', label: '导出该分组 (ZIP)', action: () => { pipelineSocket.sendCommand('_system', 'flow.export_group', { group_path: groupPath }).catch(() => {}) } },
      { icon: 'upload', label: '导入到该分组', action: () => { importGroupTarget.value = groupPath || ''; importGroupInput.value?.click() } },
      { separator: true },
      { icon: 'delete', label: '删除分组', danger: true, action: () => { if (confirm(`确认删除「${node.name}」分组及其所有工作流？此操作不可恢复。`)) { pipelineSocket.sendCommand('_system', 'flow.delete_group', { group_path: groupPath }) } } },
    ]
  } else if (isFlow) {
    const flowId = node.flow_id
    const enabled = node.enabled !== false
    contextMenu.items = [
      { icon: 'edit', label: '重命名', action: () => { renameDialog.title = '重命名工作流'; renameDialog.value = node.name; renameDialog.flowId = flowId; renameDialog.groupPath = null; renameDialog.visible = true } },
      { icon: 'content_copy', label: '复制', action: () => { if (confirm('确认复制此工作流？')) { pipelineSocket.sendCommand(flowId, 'flow.copy', {}).catch(() => {}) } } },
      { separator: true },
      { icon: 'download', label: '导出', action: () => { pipelineSocket.sendCommand(flowId, 'flow.export', {}).then(() => {}).catch(() => {}) } },
      { icon: 'upload', label: '导入替换', action: () => { /* handled via import */ } },
      { separator: true },
      { icon: 'drive_file_move', label: '移动到分组', action: () => { moveDialog.flowId = flowId; moveDialog.groupPath = ''; moveDialog.visible = true } },
      { separator: true },
      { icon: enabled ? 'block' : 'check_circle', label: enabled ? '禁用' : '启用', action: () => { pipelineSocket.sendCommand(flowId, 'flow.toggle_enabled', {}).catch(() => {}) } },
      { separator: true },
      { icon: 'delete', label: '删除', danger: true, action: () => { if (confirm('确认删除此工作流？此操作不可恢复。')) { pipelineSocket.sendCommand(flowId, 'flow.delete', {}) } } },
    ]
  }
  contextMenu.visible = true
}

function closeContextMenu() {
  contextMenu.visible = false
}

// ── Rename ──
async function doRename() {
  const val = renameDialog.value.trim()
  if (!val) return
  if (renameDialog.flowId) {
    // Rename a single flow
    pipelineSocket.sendCommand(renameDialog.flowId, 'flow.rename', { name: val }).catch(() => {})
  } else if (renameDialog.groupPath) {
    // Rename a group: compute new path by replacing last segment
    const parts = renameDialog.groupPath.split('/')
    parts[parts.length - 1] = val
    const newPath = parts.join('/')
    pipelineSocket.sendCommand('_system', 'flow.rename_group', {
      old_path: renameDialog.groupPath,
      new_path: newPath,
    }).catch(() => {})
  }
  renameDialog.visible = false
}

// ── Move to group ──
async function doMoveToGroup() {
  if (!moveDialog.flowId) return
  pipelineSocket.sendCommand(moveDialog.flowId, 'flow.update_group', {
    group: moveDialog.groupPath.trim(),
  }).catch(() => {})
  moveDialog.visible = false
}

// ── Import / Export ──
async function onImportFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    pipelineSocket.sendCommand('_system', 'flow.import', { data, overwrite: false }).catch(() => {})
  } catch (err) {
    alert('导入失败：无效的 JSON 文件')
    console.error('Import error:', err)
  }
  if (importInput.value) importInput.value.value = ''
}

async function onImportGroupFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const buf = await file.arrayBuffer()
    const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)))
    pipelineSocket.sendCommand('_system', 'flow.import_group', {
      data_b64: b64,
      group: importGroupTarget.value,
      overwrite: false,
    }).catch(() => {})
  } catch (err) {
    alert('导入失败：无效的 ZIP 文件')
    console.error('Group import error:', err)
  }
  if (importGroupInput.value) importGroupInput.value.value = ''
  importGroupTarget.value = ''
}

function downloadBlob(base64, filename, mimeType) {
  const raw = atob(base64)
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i)
  const blob = new Blob([bytes], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function downloadFlowJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// ── Lifecycle ──
onMounted(() => {
  editorStore.init()
  executionStore.init()
  notificationsStore.init()
  connectionStore.init()

  // 以下 handler 只在 onMounted 注册一次，不会被重复添加
  pipelineSocket.on('sidebar.tree', ({ groups }) => {
    // Save currently expanded IDs so we can restore them
    const prevExpanded = new Set(expandedSections.value)
    sidebarTree.value = groups || []

    // Recursively expand all sections and groups so no flow is hidden after tree refresh.
    // Clear stale IDs first, then expand everything in the new tree.
    const fresh = new Set()
    function expandAll(nodes) {
      for (const n of nodes) {
        if (n.type === 'section' || n.type === 'group') {
          fresh.add(n.id)
          if (n.children) expandAll(n.children)
        }
      }
    }
    expandAll(groups || [])
    expandedSections.value = fresh
  })

  pipelineSocket.on('flow.loaded', ({ flow }) => {
    editorStore.onFlowLoaded({ flow })
  })

  let _pendingAutoOpen = null
  pipelineSocket.on('flow.created', ({ flow }) => {
    // Auto-open the newly created flow
    if (flow && flow.id) {
      _pendingAutoOpen = flow.id
      // sidebar.tree will arrive next; select after a short delay to let tree render
      setTimeout(() => {
        if (_pendingAutoOpen === flow.id) {
          selectFlow(flow.id)
          _pendingAutoOpen = null
        }
      }, 100)
    }
  })

  pipelineSocket.on('flow.deleted', ({ flow_id }) => {
    if (activeFlowId.value === flow_id) {
      activeFlowId.value = null
      selectedNode.value = null
      editorStore.exitEditMode()
    }
  })

  pipelineSocket.on('flow.copied', ({ flow }) => {
    // Auto-open the copied flow
    if (flow && flow.id) {
      _pendingAutoOpen = flow.id
      setTimeout(() => {
        if (_pendingAutoOpen === flow.id) {
          selectFlow(flow.id)
          _pendingAutoOpen = null
        }
      }, 100)
    }
  })

  pipelineSocket.on('flow.renamed', ({ flow_id, name }) => {
    if (editorStore.flowId === flow_id) {
      editorStore.flowMeta.name = name
    }
  })

  pipelineSocket.on('flow.enabled_toggled', ({ flow_id, enabled }) => {
    // Update sidebar tree node in place so the UI reflects the change
    function updateNode(nodes) {
      for (const n of nodes) {
        if (n.type === 'flow_ref' && n.flow_id === flow_id) {
          n.enabled = enabled
          return true
        }
        if (n.children && updateNode(n.children)) return true
      }
      return false
    }
    updateNode(sidebarTree.value)
    if (editorStore.flowId === flow_id) {
      editorStore.flowMeta.enabled = enabled
    }
  })

  pipelineSocket.on('flow.group_updated', ({ flow_id, group }) => {
    if (editorStore.flowId === flow_id) {
      editorStore.flowMeta.group = group
    }
  })

  pipelineSocket.on('flow.group_renamed', () => {
    // sidebar.tree will be broadcast by backend
  })

  pipelineSocket.on('flow.group_deleted', ({ group_path }) => {
    // Clear active flow if it was in the deleted group
    const flowGroup = editorStore.flowMeta.group || ''
    if (flowGroup === group_path || flowGroup.startsWith(group_path + '/')) {
      activeFlowId.value = null
      selectedNode.value = null
      editorStore.exitEditMode()
      editorStore.nodes = []
      editorStore.connections = []
    }
  })

  pipelineSocket.on('flow.exported', ({ flow_id, data }) => {
    downloadFlowJSON(data, `${flow_id}.json`)
  })

  pipelineSocket.on('flow.group_exported', ({ filename, data_b64 }) => {
    downloadBlob(data_b64, filename, 'application/zip')
  })

  pipelineSocket.on('flow.imported', () => {
    // sidebar.tree will be broadcast by backend
  })

  pipelineSocket.on('flow.group_imported', ({ count }) => {
    // sidebar.tree will be broadcast by backend
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

/* ── Move-to-group ── */
.group-list {
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-top: 6px;
}
.group-chip {
  padding: 4px 10px; border-radius: 12px;
  background: rgba(173, 199, 255, 0.08);
  border: 1px solid rgba(173, 199, 255, 0.2);
  color: #adc7ff; font-size: 11px; cursor: pointer;
  transition: all 0.15s;
}
.group-chip:hover {
  background: rgba(173, 199, 255, 0.16);
  border-color: rgba(173, 199, 255, 0.4);
}
</style>
