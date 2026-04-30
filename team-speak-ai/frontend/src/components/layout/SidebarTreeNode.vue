<!--
  SidebarTreeNode — recursive sidebar node renderer.
  Renders flow_ref, group, and action types at any nesting depth.
-->
<template>
  <div v-if="node.type === 'flow_ref'" class="sb-item-row">
    <button
      class="sb-item"
      :class="{
        active: activeFlowId === node.flow_id,
        disabled: node.enabled === false,
      }"
      @click="$emit('select-flow', node.flow_id)"
    >
      <span class="material-symbols-outlined sb-item-icon">{{ node.icon }}</span>
      <span class="sb-item-name">{{ node.name }}</span>
      <span class="sb-status-badge" v-if="node.enabled === false">已禁用</span>
      <span class="sb-run" v-if="runningFlowIds.has(node.flow_id)"></span>
    </button>
    <button class="sb-more-btn sb-more-sm" @click.stop="$emit('menu', $event, node)" title="更多操作">
      <span class="material-symbols-outlined">more_vert</span>
    </button>
  </div>

  <div v-else-if="node.type === 'group'" class="sb-subgroup">
    <div class="sb-section-row sb-sub-row">
      <button class="sb-section-btn sb-sub-btn" @click="$emit('toggle', node.id)">
        <span class="material-symbols-outlined sb-section-icon">{{ node.icon }}</span>
        <span class="sb-section-name">{{ node.name }}</span>
        <span class="material-symbols-outlined sb-chevron" :class="{ expanded: expandedSet.has(node.id) }">chevron_right</span>
      </button>
      <button class="sb-more-btn sb-more-sm" @click.stop="$emit('menu', $event, node)" title="更多操作">
        <span class="material-symbols-outlined">more_vert</span>
      </button>
    </div>
    <div class="sb-children sb-sub" v-if="expandedSet.has(node.id)">
      <SidebarTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :activeFlowId="activeFlowId"
        :expandedSet="expandedSet"
        :runningFlowIds="runningFlowIds"
        @select-flow="(id) => $emit('select-flow', id)"
        @toggle="(id) => $emit('toggle', id)"
        @menu="(ev, n) => $emit('menu', ev, n)"
      />
    </div>
  </div>

  <button
    v-else-if="node.type === 'action'"
    class="sb-item sb-action"
    @click="$emit('action', node.id)"
  >
    <span class="material-symbols-outlined sb-item-icon">{{ node.icon }}</span>
    <span class="sb-item-name">{{ node.name }}</span>
  </button>
</template>

<script setup>
defineProps({
  node: { type: Object, required: true },
  activeFlowId: { type: String, default: null },
  expandedSet: { type: Set, default: () => new Set() },
  runningFlowIds: { type: Set, default: () => new Set() },
})

defineEmits(['select-flow', 'toggle', 'menu', 'action'])
</script>

<style scoped>
/* ── Shared with AppLayout sidebar styles ── */

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
.sb-sub-btn { padding-left: 28px; font-size: 13px; }

.sb-section-icon { font-size: 18px; color: #94a3b8; }
.sb-section-name { flex: 1; }

.sb-chevron {
  font-size: 16px; color: #94a3b8;
  transition: transform 0.2s ease;
}
.sb-chevron.expanded { transform: rotate(90deg); }

.sb-children { padding-left: 4px; }
.sb-sub { padding-left: 24px; }

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

.sb-item.disabled {
  opacity: 0.45;
}
.sb-item.disabled .sb-item-name {
  text-decoration: line-through;
}
.sb-status-badge {
  font-size: 9px; font-weight: 600;
  font-family: 'Space Grotesk', sans-serif;
  color: #64748b;
  background: rgba(100, 116, 139, 0.12);
  padding: 1px 6px; border-radius: 8px;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

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
</style>
