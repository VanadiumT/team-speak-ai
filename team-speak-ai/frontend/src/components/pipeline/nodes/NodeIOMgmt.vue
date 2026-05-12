<template>
  <div class="io-mgmt">
    <div class="mgmt-hint" v-if="editMode">点击标签可重命名 · 点击端口圆点可配置数据来源</div>

    <div class="mgmt-columns">
      <!-- 左侧: 输入端口 -->
      <div class="mgmt-col">
        <div class="mgmt-col-label">← 输入 (左侧)</div>
        <div v-if="!inputPorts.length" class="mgmt-empty">无</div>
        <template v-for="p in inputPorts" :key="p.id">
          <div class="mgmt-row"
            :class="{ ondemand: p.visibility === 'on-demand', hidden: !isPortVisible(p) }">
            <span class="mgmt-dot" :class="p.data_type === 'event' ? 'dot-event' : 'dot-data'"
              @click.stop="onPortClick(p)" />
            <!-- Editable label -->
            <input
              v-if="editingLabel === p.id"
              v-model="labelEditValue"
              class="mgmt-label-input"
              @keydown.enter="commitLabelEdit(p.id)"
              @keydown.escape="cancelLabelEdit"
              @blur="commitLabelEdit(p.id)"
              @click.stop
            />
            <span v-else class="mgmt-name" @click.stop="editMode ? startLabelEdit(p) : null"
              :class="{ editable: editMode }">{{ p.label }}</span>
            <span class="mgmt-type">{{ p.data_type }}</span>
            <template v-if="p.repeatable && p.group && editMode">
              <span class="mgmt-tag repeat">可重复</span>
              <button
                v-if="canRemoveRepeatable(p)"
                class="mgmt-remove" @click.stop="emit('removePort', p.id)" title="删除实例">&times;</button>
            </template>
            <span v-else-if="p.visibility === 'always'" class="mgmt-tag core">核心</span>
            <template v-else-if="editMode && !p.repeatable">
              <button v-if="isPortVisible(p) && !isPortConnected(p.id)"
                class="mgmt-remove" @click.stop="togglePort(p.id, false)" title="隐藏">&times;</button>
              <button v-else-if="!isPortVisible(p)"
                class="mgmt-add" @click.stop="togglePort(p.id, true)" title="添加">+</button>
              <span v-else class="mgmt-tag linked">已连线</span>
            </template>
          </div>
        </template>
        <!-- Add button for repeatable groups -->
        <div v-for="group in repeatableInputGroups" :key="'add-'+group.group"
          class="mgmt-row add-group-row">
          <button class="mgmt-add-group" @click.stop="emit('addPort', group.group)">
            + 添加{{ group.label || '端口' }}
          </button>
        </div>
      </div>

      <!-- 右侧: 输出端口 -->
      <div class="mgmt-col">
        <div class="mgmt-col-label">输出 (右侧) →</div>
        <div v-if="!outputPorts.length" class="mgmt-empty">无</div>
        <template v-for="p in outputPorts" :key="p.id">
          <div class="mgmt-row"
            :class="{ ondemand: p.visibility === 'on-demand', hidden: !isPortVisible(p) }">
            <span class="mgmt-dot" :class="p.data_type === 'event' ? 'dot-event' : 'dot-data'"
              @click.stop="onPortClick(p)" />
            <input
              v-if="editingLabel === p.id"
              v-model="labelEditValue"
              class="mgmt-label-input"
              @keydown.enter="commitLabelEdit(p.id)"
              @keydown.escape="cancelLabelEdit"
              @blur="commitLabelEdit(p.id)"
              @click.stop
            />
            <span v-else class="mgmt-name" @click.stop="editMode ? startLabelEdit(p) : null"
              :class="{ editable: editMode }">{{ p.label }}</span>
            <span class="mgmt-type">{{ p.data_type }}</span>
            <template v-if="p.repeatable && p.group && editMode">
              <span class="mgmt-tag repeat">可重复</span>
              <button
                v-if="canRemoveRepeatable(p)"
                class="mgmt-remove" @click.stop="emit('removePort', p.id)" title="删除实例">&times;</button>
            </template>
            <span v-else-if="p.visibility === 'always'" class="mgmt-tag core">核心</span>
            <template v-else-if="editMode && !p.repeatable">
              <button v-if="isPortVisible(p) && !isPortConnected(p.id)"
                class="mgmt-remove" @click.stop="togglePort(p.id, false)" title="隐藏">&times;</button>
              <button v-else-if="!isPortVisible(p)"
                class="mgmt-add" @click.stop="togglePort(p.id, true)" title="添加">+</button>
              <span v-else class="mgmt-tag linked">已连线</span>
            </template>
          </div>
        </template>
        <div v-for="group in repeatableOutputGroups" :key="'add-'+group.group"
          class="mgmt-row add-group-row">
          <button class="mgmt-add-group" @click.stop="emit('addPort', group.group)">
            + 添加{{ group.label || '端口' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useEditorStore } from '@/stores/editor'

const props = defineProps({
  node: { type: Object, required: true },
  editMode: { type: Boolean, default: false },
  inputPorts: { type: Array, default: () => [] },
  outputPorts: { type: Array, default: () => [] },
})

const emit = defineEmits(['togglePort', 'portClick', 'addPort', 'removePort'])

const editorStore = useEditorStore()

// ── Label editing state ──
const editingLabel = ref(null)
const labelEditValue = ref('')

function startLabelEdit(port) {
  editingLabel.value = port.id
  labelEditValue.value = port.label
}

function commitLabelEdit(portId) {
  if (!editingLabel.value) return
  const trimmed = labelEditValue.value.trim()
  if (trimmed) {
    editorStore.renamePortLabel(props.node.id, portId, trimmed)
  }
  editingLabel.value = null
}

function cancelLabelEdit() {
  editingLabel.value = null
}

// ── Repeatable group helpers (read from type def, not ports list) ──
function _repeatableGroups(side) {
  const tdef = editorStore.getNodeTypeDef(props.node.type)
  if (!tdef) return []
  const ports = side === 'input' ? (tdef.ports?.inputs || []) : (tdef.ports?.outputs || [])
  const seen = new Set()
  const groups = []
  for (const p of ports) {
    if (p.repeatable && p.group && !seen.has(p.group)) {
      seen.add(p.group)
      const instances = props.node.config?._repeatable_ports?.[p.group] || []
      groups.push({
        group: p.group,
        label: p.label,
        count: instances.length,
        max: p.max || 20,
      })
    }
  }
  return groups.filter(g => g.count < g.max)
}

const repeatableInputGroups = computed(() => _repeatableGroups('input'))
const repeatableOutputGroups = computed(() => _repeatableGroups('output'))

function canRemoveRepeatable(port) {
  if (!port.repeatable || !port.group) return false
  const instances = props.node.config?._repeatable_ports?.[port.group] || []
  const min = port.min != null ? port.min : 1
  return instances.length > min
}

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
.mgmt-tag.repeat { color: #ffb695; background: rgba(255,182,149,0.1); }
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
.mgmt-label-input {
  flex: 1; font-size: 10px; color: #e0e2ed;
  background: rgba(255,255,255,0.06); border: 1px solid #4a8eff;
  border-radius: 3px; padding: 1px 4px; font-family: inherit; outline: none;
  min-width: 0; height: 16px;
}
.mgmt-name.editable { cursor: text; }
.mgmt-name.editable:hover { color: #adc7ff; }
.add-group-row { justify-content: flex-start; padding: 2px 0; }
.mgmt-add-group {
  font-size: 9px; color: #8b90a0; background: none; border: 1px dashed #414754;
  border-radius: 3px; padding: 1px 8px; cursor: pointer;
  font-family: 'Space Grotesk', sans-serif; transition: all 0.15s;
}
.mgmt-add-group:hover { color: #adc7ff; border-color: #adc7ff; }
</style>
