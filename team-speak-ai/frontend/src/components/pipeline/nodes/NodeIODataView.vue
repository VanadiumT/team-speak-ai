<template>
  <div class="io-data-view">
    <div v-if="!hasLiveData" class="io-empty">暂无 IO 数据</div>

    <!-- 输入端口 (左侧) -->
    <div v-if="inputEntries.length" class="io-side">
      <div class="io-side-label">← 输入端口 (左侧)</div>
      <div v-for="entry in inputEntries" :key="entry.key" class="io-entry">
        <div class="io-entry-header">
          <span class="io-port-name">{{ entry.key }}</span>
          <span class="io-port-type" v-if="entry.type">{{ entry.type }}</span>
        </div>
        <div class="io-entry-value" :class="{ 'io-pre': entry.pre }">{{ entry.value }}</div>
        <div v-if="entry.downstream" class="io-downstream">→ {{ entry.downstream }}</div>
      </div>
    </div>

    <!-- 输出端口 (右侧) -->
    <div v-if="outputEntries.length" class="io-side">
      <div class="io-side-label">输出端口 (右侧) →</div>
      <div v-for="entry in outputEntries" :key="entry.key" class="io-entry">
        <div class="io-entry-header">
          <span class="io-port-name">{{ entry.key }}</span>
          <span class="io-port-type" v-if="entry.type">{{ entry.type }}</span>
        </div>
        <div class="io-entry-value" :class="{ 'io-pre': entry.pre }">{{ entry.value }}</div>
        <div v-if="entry.downstream" class="io-downstream">→ {{ entry.downstream }}</div>
      </div>
    </div>

    <div v-if="lastExecution" class="io-footer">上次执行: {{ lastExecution }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  inputs: { type: Object, default: () => ({}) },
  outputs: { type: Object, default: () => ({}) },
  lastExecution: { type: String, default: '' },
})

const normalize = (obj) => {
  if (!obj) return []
  return Object.entries(obj).map(([key, val]) => {
    if (typeof val === 'object' && val !== null) {
      return { key, type: val.type || '', value: val.value ?? JSON.stringify(val, null, 1), downstream: val.downstream || '', pre: val.pre || false }
    }
    const str = String(val ?? '(无数据)')
    return { key, type: '', value: str, downstream: '', pre: str.length > 80 }
  })
}

const inputEntries = computed(() => normalize(props.inputs))
const outputEntries = computed(() => normalize(props.outputs))
const hasLiveData = computed(() => inputEntries.value.length > 0 || outputEntries.value.length > 0)
</script>

<style scoped>
.io-data-view { display: flex; flex-direction: column; gap: 10px; }
.io-empty { font-size: 10px; color: #64748b; text-align: center; padding: 12px 0; }

.io-side { }
.io-side-label {
  font-size: 9px; color: #8b90a0; text-transform: uppercase;
  letter-spacing: 0.06em; font-family: 'Space Grotesk', sans-serif;
  padding-bottom: 3px; border-bottom: 1px solid rgba(65,71,84,0.3);
  margin-bottom: 4px;
}
.io-entry { padding: 2px 0; }
.io-entry-header { display: flex; align-items: center; gap: 6px; margin-bottom: 1px; }
.io-port-name { font-size: 10px; color: #c1c6d7; font-weight: 500; font-family: 'Space Grotesk', sans-serif; }
.io-port-type { font-size: 8px; color: #64748b; font-family: 'Space Grotesk', sans-serif; }
.io-entry-value {
  font-size: 10px; color: #e0e2ed;
  padding: 3px 6px; background: rgba(11,14,22,0.6); border-radius: 3px;
  word-break: break-all; line-height: 1.4; max-height: 80px; overflow-y: auto;
}
.io-entry-value.io-pre { font-family: 'Space Grotesk', sans-serif; font-size: 9px; }
.io-downstream { font-size: 9px; color: #4a8eff; padding: 1px 0; }
.io-footer { font-size: 8px; color: #414754; text-align: right; font-family: 'Space Grotesk', sans-serif; margin-top: 4px; }
</style>
