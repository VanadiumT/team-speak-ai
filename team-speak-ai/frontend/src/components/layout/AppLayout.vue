<template>
  <div class="layout">
    <!-- ═══ Header ═══ -->
    <header class="header">
      <div class="h-left">
        <span class="material-symbols-outlined h-logo" style="font-size: 22px;">smart_toy</span>
        <span class="h-title">TeamSpeak AI</span>
        <span class="h-version">v2.4.0-Stable</span>
      </div>
      <div class="h-right">
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
              <button class="sb-section-btn" @click="toggleSection(section.id)">
                <span class="material-symbols-outlined sb-section-icon">{{ section.icon }}</span>
                <span class="sb-section-name">{{ section.name }}</span>
                <span class="material-symbols-outlined sb-chevron" :class="{ expanded: isExpanded(section.id) }">chevron_right</span>
              </button>
              <div class="sb-children" v-if="isExpanded(section.id)">
                <template v-for="child in section.children" :key="child.id">
                  <button
                    v-if="child.type === 'flow_ref'"
                    class="sb-item"
                    :class="{ active: activeFlowId === child.flow_id }"
                    @click="selectFlow(child.flow_id)"
                  >
                    <span class="material-symbols-outlined sb-item-icon">{{ child.icon }}</span>
                    <span class="sb-item-name">{{ child.name }}</span>
                    <span class="sb-run" v-if="isFlowRunning(child.flow_id)"></span>
                  </button>
                  <div v-else-if="child.type === 'group'" class="sb-subgroup">
                    <button class="sb-section-btn sb-sub-btn" @click="toggleSection(child.id)">
                      <span class="material-symbols-outlined sb-section-icon">{{ child.icon }}</span>
                      <span class="sb-section-name">{{ child.name }}</span>
                      <span class="material-symbols-outlined sb-chevron" :class="{ expanded: isExpanded(child.id) }">chevron_right</span>
                    </button>
                    <div class="sb-children sb-sub" v-if="isExpanded(child.id)">
                      <button
                        v-for="gc in child.children" :key="gc.id"
                        class="sb-item"
                        :class="{ active: activeFlowId === gc.flow_id }"
                        @click="selectFlow(gc.flow_id)"
                      >
                        <span class="material-symbols-outlined sb-item-icon">{{ gc.icon }}</span>
                        <span class="sb-item-name">{{ gc.name }}</span>
                      </button>
                    </div>
                  </div>
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
      </aside>

      <!-- Content -->
      <main class="content">
        <PipelineView
          v-if="activeFlowId"
          :key="activeFlowId"
          @select-node="onSelectNode"
        />
        <div v-else class="no-flow">
          <span class="material-symbols-outlined" style="font-size: 48px; opacity: 0.2;">account_tree</span>
          <p>选择左侧工作流以开始</p>
        </div>
      </main>

      <!-- Detail panel (right) -->
      <aside v-if="selectedNode" class="detail-panel" id="detail-panel">
        <DynamicPanel :node="selectedNode" @close="selectedNode = null" />
      </aside>
    </div>

    <!-- ═══ Footer ═══ -->
    <BottomStatusBar />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'
import { useEditorStore } from '@/stores/editor.js'
import { useExecutionStore } from '@/stores/execution.js'
import { useNotificationsStore } from '@/stores/notifications.js'
import { useConnectionStore } from '@/stores/connection.js'
import PipelineView from '@/components/pipeline/PipelineView.vue'
import DynamicPanel from '@/components/panels/DynamicPanel.vue'
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

// ── Sidebar ──
function isExpanded(id) { return expandedSections.value.has(id) }
function toggleSection(id) {
  if (expandedSections.value.has(id)) {
    expandedSections.value.delete(id)
  } else {
    expandedSections.value.add(id)
  }
  // trigger reactivity
  expandedSections.value = new Set(expandedSections.value)
}

async function selectFlow(flowId) {
  activeFlowId.value = flowId
  selectedNode.value = null
  try {
    await editorStore.loadFlow(flowId)
  } catch (e) {
    console.error('Failed to load flow:', e)
  }
}

function isFlowRunning(flowId) {
  return executionStore.status === 'running' && editorStore.flowId === flowId
}

function onAction(actionId) {
  if (actionId === 'action:new_flow') {
    const name = prompt('流程名称：')
    if (name) {
      pipelineSocket.sendCommand('_system', 'flow.create', { name, group: '', icon: 'account_tree' })
    }
  }
}

function onSelectNode(nodeId) {
  selectedNode.value = editorStore.nodes.find((n) => n.id === nodeId) || null
}

// ── Lifecycle ──
onMounted(() => {
  // Init stores
  editorStore.init()
  executionStore.init()
  notificationsStore.init()
  connectionStore.init()

  // Sidebar events
  pipelineSocket.on('sidebar.tree', ({ groups }) => {
    sidebarTree.value = groups || []
    // Auto-expand all sections
    groups?.forEach((s) => {
      expandedSections.value.add(s.id)
      s.children?.forEach((c) => {
        if (c.type === 'group') expandedSections.value.add(c.id)
      })
    })
  })

  // Handle flow loaded
  pipelineSocket.on('flow.loaded', ({ flow }) => {
    editorStore.onFlowLoaded({ flow })
  })

  // Handle flow created
  pipelineSocket.on('flow.created', () => {
    // Re-request sidebar tree
    pipelineSocket.sendCommand('_system', 'flow.list', {})
  })

  // Connect
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

.h-right { display: flex; align-items: center; gap: 16px; }

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
  z-index: 40;
  overflow-y: auto;
  padding: 16px 0;
}

.sb-loading {
  padding: 24px 16px; text-align: center;
  font-size: 13px; color: #94a3b8;
}

.sb-nav { display: flex; flex-direction: column; }

.sb-section { margin-bottom: 4px; }

.sb-section-btn {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 8px 12px;
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
.sb-sub-btn { padding-left: 16px; font-size: 13px; }

.sb-item {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 8px 12px 8px 24px;
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

/* ── Content ── */
.content { flex: 1; overflow: hidden; position: relative; }

.no-flow {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; gap: 16px;
  color: #64748b; font-size: 14px;
}

/* ── Detail Panel ── */
.detail-panel {
  width: 320px; flex-shrink: 0;
  background: #020617;
  border-left: 1px solid rgba(65, 71, 84, 0.3);
  overflow-y: auto;
}
</style>
