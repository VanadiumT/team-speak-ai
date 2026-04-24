<template>
  <div class="pipeline-graph">
    <!-- 空态 -->
    <div class="graph-empty" v-if="!hasLayout">
      <span class="emp-ico">⚡</span>
      加载中...
    </div>

    <!-- 图表 -->
    <div class="graph-scroll" v-else>
      <div class="graph-inner" :style="{ width: svgW + 'px', height: svgH + 'px' }">
        <!-- SVG 箭头 -->
        <svg class="g-svg" :width="svgW" :height="svgH" :viewBox="`0 0 ${svgW} ${svgH}`">
          <defs>
            <marker id="a" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
              <polygon points="0 0,7 2.5,0 5" fill="rgba(148,163,184,0.35)"/>
            </marker>
            <marker id="a-live" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
              <polygon points="0 0,7 2.5,0 5" fill="#38bdf8"/>
            </marker>
            <marker id="a-ok" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
              <polygon points="0 0,7 2.5,0 5" fill="#34d399"/>
            </marker>
          </defs>
          <g class="arrow-layer">
            <path
              v-for="(ap,i) in arrowPaths" :key="i"
              :d="ap.d" fill="none"
              :class="['arrow', arrowStatus(ap.from, ap.to), ap.type]"
              :marker-end="arrowMrk(ap.from, ap.to)"
            />
          </g>
        </svg>

        <!-- 节点 -->
        <div
          v-for="pos in nodePosList" :key="pos.id"
          class="node-place"
          :style="{ left: pos.x + 'px', top: pos.y + 'px', width: pos.w + 'px' }"
        >
          <PipelineNode
            :node="getNode(pos.id)"
            :active="pos.id === activeNodeId"
            @select="$emit('select-node', pos.id)"
          />
        </div>

        <!-- 技能提示标签 (非节点，标注在 context 附近) -->
        <div v-if="skillBadge" class="skill-badge">
          💡 Skill
        </div>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="g-toolbar" v-if="hasRestart">
      <button class="btn-rst" @click="$emit('restart')">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 8a6 6 0 0 1 10.47-4M14 8a6 6 0 0 1-10.47 4"/><path d="M13 2v3h-3M3 14v-3h3"/></svg>
        重新开始
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import PipelineNode from './PipelineNode.vue'
import { computePipelineLayout } from '@/utils/layout.js'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  activeNodeId: { type: String, default: null },
  skillPrompt: { type: String, default: '' },
})
const emit = defineEmits(['select-node', 'restart'])

const positionsMap = ref({})
const arrowPaths = ref([])
const svgW = ref(0)
const svgH = ref(0)
const mergeNode = ref(null)

watch(() => props.nodes, (nodes) => {
  const l = computePipelineLayout(nodes)
  positionsMap.value = l.positions || {}
  arrowPaths.value = l.arrowPaths || []
  svgW.value = l.svgW || 200
  svgH.value = l.svgH || 100
  mergeNode.value = l.mergeNode
}, { immediate: true })

const hasLayout = computed(() => Object.keys(positionsMap.value).length > 0)
const nodePosList = computed(() => Object.values(positionsMap.value).sort((a, b) => a.row - b.row || a.col - b.col))

const getNode = (id) => props.nodes.find((n) => n.id === id) || { id, type: '?', name: id, status: 'pending' }
const nStatus = (id) => getNode(id).status

const arrowStatus = (from, to) => {
  const f = nStatus(from), t = nStatus(to)
  if (f === 'completed') return 'ok'
  if (f === 'processing' || t === 'processing') return 'live'
  return ''
}
const arrowMrk = (from, to) => {
  const f = nStatus(from), t = nStatus(to)
  if (f === 'completed') return 'url(#a-ok)'
  if (f === 'processing' || t === 'processing') return 'url(#a-live)'
  return 'url(#a)'
}

const hasRestart = computed(() => props.nodes.some((n) => n.status === 'completed' || n.status === 'error'))

// Skill badge position: near merge node
const skillBadge = computed(() => {
  if (!props.skillPrompt || !mergeNode.value) return null
  const mp = positionsMap.value[mergeNode.value]
  if (!mp) return null
  return {
    left: mp.x - 60 + 'px',
    top: mp.y - 20 + 'px',
  }
})
</script>

<style scoped>
.pipeline-graph {
  margin-bottom: 10px;
}
.graph-empty {
  display: flex; align-items: center; justify-content: center;
  gap: 6px; min-height: 50px;
  font-size: 0.72rem; color: rgba(255,255,255,0.15);
}
.emp-ico { font-size: 0.9rem; }
.graph-scroll {
  overflow-x: auto; overflow-y: hidden;
  padding-bottom: 4px;
}
.graph-inner {
  position: relative;
  min-width: 100%;
}

/* SVG */
.g-svg {
  position: absolute; top:0; left:0;
  pointer-events: none; z-index: 1;
  overflow: visible;
}
.arrow {
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: stroke 0.4s, stroke-width 0.3s;
}
.arrow.trigger {
  stroke: rgba(148,163,184,0.25);
  stroke-width: 1.3;
}
.arrow.data {
  stroke: rgba(148,163,184,0.15);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}
.arrow.live {
  stroke: #38bdf8;
  stroke-width: 1.6;
}
.arrow.live.trigger {
  animation: flowDash 0.6s linear infinite;
}
.arrow.live.data {
  stroke-dasharray: 3 3;
  animation: flowDash 0.6s linear infinite;
}
.arrow.ok {
  stroke: #34d399;
  stroke-width: 1.4;
}
@keyframes flowDash {
  to { stroke-dashoffset: -20; }
}
.arrow.trigger.live { stroke-dasharray: 5 3; }
.arrow.trigger.ok { stroke-dasharray: none; }

/* 节点占位 */
.node-place {
  position: absolute;
  z-index: 2;
}

/* 技能标签 */
.skill-badge {
  position: absolute;
  font-size: 0.55rem;
  padding: 1px 6px;
  border-radius: 6px;
  background: rgba(251,191,36,0.08);
  border: 1px solid rgba(251,191,36,0.15);
  color: rgba(251,191,36,0.5);
}

/* 工具栏 */
.g-toolbar {
  display: flex; justify-content: flex-end;
  padding: 4px 0 0;
}
.btn-rst {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 10px;
  background: rgba(239,68,68,0.06);
  border: 1px solid rgba(239,68,68,0.12);
  border-radius: 6px;
  color: rgba(255,255,255,0.3);
  font-size: 0.65rem;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-rst:hover {
  background: rgba(239,68,68,0.12);
  border-color: rgba(239,68,68,0.25);
  color: #ef4444;
}
</style>
