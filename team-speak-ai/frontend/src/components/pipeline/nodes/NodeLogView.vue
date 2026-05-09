<template>
  <div class="node-log-view" ref="logContainer">
    <div v-if="!logs.length" class="log-empty">暂无日志</div>
    <div v-else class="log-lines">
      <div
        v-for="(entry, i) in displayLogs"
        :key="i"
        class="log-line"
        :class="[`log-${entry.level}`, { 'log-highlight': entry.highlight }]"
      >
        <span class="log-ts">{{ entry.timestamp }}</span>
        <span class="log-msg">{{ entry.message }}</span>
      </div>
      <div v-if="hasMore" class="log-more">... 共 {{ logs.length }} 条</div>
    </div>
    <button v-if="logs.length" class="log-clear" @click="$emit('clear')">清空日志</button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  logs: { type: Array, default: () => [] },
  limit: { type: Number, default: 50 }
})

defineEmits(['clear'])

const displayLogs = computed(() => props.logs.slice(-props.limit))
const hasMore = computed(() => props.logs.length > props.limit)
</script>

<style scoped>
.node-log-view {
  display: flex;
  flex-direction: column;
  max-height: 240px;
  overflow-y: auto;
}
.log-empty { font-size: 10px; color: #64748b; text-align: center; padding: 12px 0; }
.log-lines { display: flex; flex-direction: column; gap: 3px; }
.log-line {
  display: flex;
  gap: 6px;
  font-size: 9px;
  font-family: 'Space Grotesk', sans-serif;
  padding: 1px 2px;
  border-radius: 2px;
}
.log-ts { color: #64748b; flex-shrink: 0; }
.log-msg { color: #c1c6d7; word-break: break-all; }

.log-muted .log-msg { color: #64748b; }
.log-info .log-msg { color: #adc7ff; }
.log-success .log-msg { color: #4edea3; }
.log-warn .log-msg { color: #ef6719; }
.log-error .log-msg { color: #ffb4ab; }

.log-highlight { animation: highlightFlash 1.5s ease-out 2; }
@keyframes highlightFlash { 0%,100% { background: transparent; } 50% { background: rgba(239,103,25,0.12); } }

.log-more { font-size: 8px; color: #414754; text-align: center; padding: 4px 0; }
.log-clear {
  margin-top: 6px; padding: 3px 8px;
  border-radius: 4px; border: 1px solid #414754;
  background: transparent; color: #8b90a0;
  font-size: 9px; cursor: pointer; align-self: flex-end;
  transition: all 0.15s;
}
.log-clear:hover { color: #ffb4ab; border-color: #ffb4ab; }
</style>
