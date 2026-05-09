<template>
  <div class="io-mgmt">
    <div class="mgmt-hint" v-if="editMode">点击端口圆点可配置数据来源</div>

    <div class="mgmt-columns">
      <!-- 左侧: 输入端口 -->
      <div class="mgmt-col">
        <div class="mgmt-col-label">← 输入 (左侧)</div>
        <div v-if="!inputPorts.length" class="mgmt-empty">无</div>
        <div v-for="p in inputPorts" :key="p.id" class="mgmt-row"
          :class="{ ondemand: p.visibility === 'on-demand', hidden: !isPortVisible(p) }"
          @click.stop="onPortClick(p)">
          <span class="mgmt-dot" :class="p.data_type === 'event' ? 'dot-event' : 'dot-data'" />
          <span class="mgmt-name">{{ p.label }}</span>
          <span class="mgmt-type">{{ p.data_type }}</span>
          <span v-if="p.visibility === 'always'" class="mgmt-tag core">核心</span>
          <template v-else-if="editMode">
            <button v-if="isPortVisible(p) && !isPortConnected(p.id)"
              class="mgmt-remove" @click.stop="togglePort(p.id, false)" title="隐藏">&times;</button>
            <button v-else-if="!isPortVisible(p)"
              class="mgmt-add" @click.stop="togglePort(p.id, true)" title="添加">+</button>
            <span v-else class="mgmt-tag linked">已连线</span>
          </template>
        </div>
      </div>

      <!-- 右侧: 输出端口 -->
      <div class="mgmt-col">
        <div class="mgmt-col-label">输出 (右侧) →</div>
        <div v-if="!outputPorts.length" class="mgmt-empty">无</div>
        <div v-for="p in outputPorts" :key="p.id" class="mgmt-row"
          :class="{ ondemand: p.visibility === 'on-demand', hidden: !isPortVisible(p) }"
          @click.stop="onPortClick(p)">
          <span class="mgmt-dot" :class="p.data_type === 'event' ? 'dot-event' : 'dot-data'" />
          <span class="mgmt-name">{{ p.label }}</span>
          <span class="mgmt-type">{{ p.data_type }}</span>
          <span v-if="p.visibility === 'always'" class="mgmt-tag core">核心</span>
          <template v-else-if="editMode">
            <button v-if="isPortVisible(p) && !isPortConnected(p.id)"
              class="mgmt-remove" @click.stop="togglePort(p.id, false)" title="隐藏">&times;</button>
            <button v-else-if="!isPortVisible(p)"
              class="mgmt-add" @click.stop="togglePort(p.id, true)" title="添加">+</button>
            <span v-else class="mgmt-tag linked">已连线</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEditorStore } from '@/stores/editor'

const props = defineProps({
  node: { type: Object, required: true },
  editMode: { type: Boolean, default: false },
  inputPorts: { type: Array, default: () => [] },
  outputPorts: { type: Array, default: () => [] },
})

const emit = defineEmits(['togglePort', 'portClick'])

const editorStore = useEditorStore()

function isPortVisible(port) {
  if (port.visibility === 'always' || !port.visibility) return true
  const vis = props.node.config?._visible_ports || []
  if (vis.includes(port.id)) return true
  return editorStore.connections.some((c) =>
    (c.from_node === props.node.id && c.from_port === port.id) ||
    (c.to_node === props.node.id && c.to_port === port.id))
}

function isPortConnected(portId) {
  return editorStore.connections.some((c) =>
    (c.from_node === props.node.id && c.from_port === portId) ||
    (c.to_node === props.node.id && c.to_port === portId))
}

function togglePort(portId, show) {
  emit('togglePort', portId, show)
}

function onPortClick(port) {
  emit('portClick', port)
}
</script>

<style scoped>
.io-mgmt { }
.mgmt-hint {
  font-size: 9px; color: #64748b; text-align: center;
  padding: 4px 0 8px; font-family: 'Space Grotesk', sans-serif;
}

.mgmt-columns { display: flex; gap: 10px; }
.mgmt-col { flex: 1; min-width: 0; }
.mgmt-col-label {
  font-size: 9px; color: #8b90a0; text-transform: uppercase;
  letter-spacing: 0.06em; font-family: 'Space Grotesk', sans-serif;
  padding-bottom: 3px; border-bottom: 1px solid rgba(65,71,84,0.3);
  margin-bottom: 4px;
}
.mgmt-empty { font-size: 9px; color: #414754; text-align: center; padding: 6px 0; }

.mgmt-row {
  display: flex; align-items: center; gap: 4px;
  padding: 3px 2px; border-radius: 3px;
  font-size: 10px; cursor: default;
  transition: background 0.1s;
}
.mgmt-row:hover { background: rgba(173,199,255,0.04); }
.mgmt-row.ondemand { }
.mgmt-row.hidden { opacity: 0.35; }

.mgmt-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-data { background: #4edea3; }
.dot-event { background: #ffb695; }
.mgmt-name { flex: 1; color: #c1c6d7; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mgmt-type { font-size: 7px; color: #64748b; font-family: 'Space Grotesk', sans-serif; }
.mgmt-tag {
  font-size: 7px; padding: 0 3px; border-radius: 9999px; font-family: 'Space Grotesk', sans-serif;
}
.mgmt-tag.core { color: #adc7ff; background: rgba(173,199,255,0.1); }
.mgmt-tag.linked { color: #4edea3; background: rgba(78,222,163,0.1); }
.mgmt-add {
  width: 16px; height: 16px; border-radius: 50%; flex-shrink: 0;
  border: 1px dashed #414754; background: transparent; color: #8b90a0;
  font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.mgmt-add:hover { border-color: #adc7ff; color: #adc7ff; }
.mgmt-remove {
  background: none; border: none; color: #8b90a0; font-size: 13px;
  cursor: pointer; padding: 0 2px; line-height: 1; flex-shrink: 0;
}
.mgmt-remove:hover { color: #ffb4ab; }
</style>
