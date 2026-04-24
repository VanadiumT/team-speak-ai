<template>
  <div class="imp-panel" :class="{ folded: collapsed }">
    <div class="imp-head" @click="collapsed = !collapsed">
      <span class="imp-htitle">📋 重要信息</span>
      <span class="imp-badge" v-if="events.length">{{ events.length }}</span>
      <span class="imp-tgl">{{ collapsed ? '▸' : '▾' }}</span>
    </div>
    <div class="imp-body" v-if="!collapsed">
      <div v-for="evt in events" :key="evt.id" class="imp-item" :class="evt.type">
        <span class="imp-ico">{{ icons[evt.type] || 'ℹ️' }}</span>
        <div class="imp-main">
          <div class="imp-ttl">{{ evt.title }}</div>
          <div class="imp-msg">{{ evt.content }}</div>
        </div>
        <span class="imp-time">{{ format(evt.timestamp) }}</span>
      </div>
      <div v-if="events.length === 0" class="imp-empty">暂无事件</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  events: { type: Array, default: () => [] },
})

const collapsed = ref(false)
const icons = { result: '✅', status: '🔵', error: '❌', info: 'ℹ️' }
const format = (ts) => ts ? new Date(ts).toLocaleTimeString() : ''
</script>

<style scoped>
.imp-panel {
  background: rgba(15,23,42,0.3);
  border: 1px solid rgba(148,163,184,0.04);
  border-radius: 8px;
  overflow: hidden;
  backdrop-filter: blur(6px);
}
.imp-head {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px;
  background: rgba(255,255,255,0.015);
  cursor: pointer; user-select: none;
  font-size: 0.65rem; color: rgba(255,255,255,0.35);
  transition: color 0.15s;
}
.imp-head:hover { color: rgba(255,255,255,0.55); }
.imp-htitle { }
.imp-badge {
  font-size: 0.5rem;
  background: rgba(233,69,96,0.12);
  color: #e94560;
  padding: 0 6px; border-radius: 8px;
}
.imp-tgl { margin-left: auto; color: rgba(255,255,255,0.15); font-size: 0.6rem; }

.imp-body {
  max-height: 180px; overflow-y: auto;
  padding: 6px 14px;
}
.imp-item {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 5px 0;
  border-bottom: 1px solid rgba(255,255,255,0.02);
  font-size: 0.65rem;
}
.imp-item:last-child { border-bottom: none; }
.imp-ico { font-size: 0.7rem; flex-shrink: 0; margin-top: 1px; }
.imp-main { flex: 1; min-width: 0; }
.imp-ttl { font-weight: 600; color: rgba(255,255,255,0.55); }
.imp-msg { color: rgba(255,255,255,0.25); margin-top: 1px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.imp-time { color: rgba(255,255,255,0.1); font-size: 0.55rem; white-space: nowrap; flex-shrink: 0; font-family: ui-monospace, monospace; }

.imp-item.error .imp-ttl { color: #ef4444; }
.imp-item.result .imp-ttl { color: #34d399; }

.imp-empty {
  text-align: center; padding: 14px 0;
  color: rgba(255,255,255,0.08); font-size: 0.65rem;
}
</style>
