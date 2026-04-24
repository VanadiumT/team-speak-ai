<template>
  <div
    class="node-chip"
    :class="[`t-${node.type}`, `s-${node.status}`, { active }]"
    :title="tooltip"
    @click="$emit('select')"
  >
    <!-- 光晕 -->
    <div class="chip-glow"></div>

    <!-- 主行 -->
    <div class="chip-bar">
      <span class="ch-icon">{{ icon }}</span>
      <span class="ch-name">{{ node.name }}</span>
      <span class="ch-dot" :class="node.status"></span>
    </div>

    <!-- 实时内容行 -->
    <div class="chip-live" v-if="showLive">
      <!-- STT 转写 -->
      <template v-if="node.type === 'stt_listen'">
        <div class="lv-line stt" v-if="node.status === 'processing'">
          <span class="lv-ico">🎤</span>
          <span class="lv-txt stream">{{ liveStt || '监听中...' }}</span>
        </div>
        <div class="lv-line stt" v-else-if="node.status === 'completed'">
          <span class="lv-ico">✅</span>
          <span class="lv-txt">{{ trim(liveStt, 24) }}</span>
        </div>
      </template>

      <!-- OCR -->
      <template v-else-if="node.type === 'ocr'">
        <div class="lv-line">
          <span class="lv-ico">📝</span>
          <span class="lv-txt">{{ trim(node.summary, 24) }}</span>
        </div>
      </template>

      <!-- 上下文构建 - 三源标签 -->
      <template v-else-if="node.type === 'context_build'">
        <div class="lv-tags">
          <span class="tg" :class="{ on: true }">📷 OCR</span>
          <span class="tg" :class="{ on: true }">🎤 STT</span>
          <span class="tg on">💡 Skill</span>
        </div>
      </template>

      <!-- LLM 流式 -->
      <template v-else-if="node.type === 'llm'">
        <div class="lv-line llm" v-if="node.status === 'processing'">
          <span class="lv-ico">🧠</span>
          <span class="lv-txt stream">{{ node.summary || '...' }}</span>
        </div>
        <div class="lv-line llm" v-else-if="node.status === 'completed'">
          <span class="lv-ico">✅</span>
          <span class="lv-txt">{{ trim(node.data?.response || node.summary, 28) }}</span>
        </div>
      </template>

      <!-- TTS -->
      <template v-else-if="node.type === 'tts'">
        <div class="lv-line">
          <span class="lv-ico">{{ node.status === 'completed' ? '✅' : '🔊' }}</span>
          <span class="lv-txt">{{ node.summary || '等待合成...' }}</span>
        </div>
      </template>

      <!-- 上传 -->
      <template v-else-if="node.type === 'input_image'">
        <div class="lv-line">
          <span class="lv-ico">{{ node.status === 'completed' ? '✅' : '🖼️' }}</span>
          <span class="lv-txt">{{ node.summary || '等待上传' }}</span>
        </div>
      </template>

      <!-- 播放 -->
      <template v-else-if="node.type === 'ts_output'">
        <div class="lv-line">
          <span class="lv-ico">📡</span>
          <span class="lv-txt">{{ node.status === 'completed' ? '已发送' : node.status === 'error' ? '失败' : '等待' }}</span>
        </div>
      </template>

      <!-- 通用 -->
      <template v-else>
        <div class="lv-line">
          <span class="lv-txt">{{ trim(node.summary, 20) }}</span>
        </div>
      </template>
    </div>

    <!-- 进度底条 -->
    <div class="chip-prog" v-if="node.status === 'processing'">
      <div class="prog-bar"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  active: { type: Boolean, default: false },
})
defineEmits(['select'])

const icon = computed(() => ({
  input_image: '🖼️', ocr: '📝', stt_listen: '🎙️',
  context_build: '🔗', llm: '🧠', tts: '🔊', ts_output: '📡',
}[props.node.type] || '⚙️'))

const liveStt = computed(() => {
  const d = props.node.data
  return d?.accumulated || d?.partial_text || d?.text || ''
})

const showLive = computed(() => props.node.status !== 'pending' || props.node.type === 'stt_listen')

const tooltip = computed(() => {
  const d = props.node.data
  if (props.node.type === 'llm' && d?.response) return d.response.slice(0, 100)
  if (props.node.type === 'stt_listen') return liveStt.value
  if (props.node.type === 'context_build') return 'OCR + STT + Skill → LLM'
  return props.node.summary || props.node.name
})

const trim = (s, n) => !s ? '' : s.length > n ? s.slice(0, n) + '…' : s
</script>

<style scoped>
.node-chip {
  position: relative;
  width: 96px;
  min-height: 34px;
  background: linear-gradient(135deg, rgba(15,23,42,0.85), rgba(30,41,59,0.8));
  border: 1px solid rgba(148,163,184,0.1);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4,0,0.2,1);
  display: flex;
  flex-direction: column;
  overflow: visible;
  backdrop-filter: blur(6px);
}
.node-chip:hover {
  border-color: rgba(148,163,184,0.25);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.node-chip.active {
  border-color: rgba(56,189,248,0.4);
  box-shadow: 0 0 14px rgba(56,189,248,0.12);
}

/* 光晕 */
.chip-glow {
  position: absolute; inset: -1px;
  border-radius: 9px;
  opacity: 0; pointer-events: none;
  transition: opacity 0.4s;
}
.s-processing .chip-glow {
  opacity: 0.45;
  background: radial-gradient(ellipse at 50% 0%, rgba(56,189,248,0.12), transparent 70%);
  animation: glowP 2s ease-in-out infinite;
}
.s-completed .chip-glow {
  opacity: 0.25;
  background: radial-gradient(ellipse at 50% 0%, rgba(52,211,153,0.08), transparent 70%);
}
.s-error .chip-glow {
  opacity: 0.3;
  background: radial-gradient(ellipse at 50% 0%, rgba(239,68,68,0.1), transparent 70%);
}
@keyframes glowP { 0%,100%{opacity:0.2} 50%{opacity:0.5} }

/* 顶行 */
.chip-bar {
  display: flex; align-items: center;
  gap: 3px; padding: 3px 7px 2px;
}
.ch-icon { font-size: 0.7rem; line-height: 1; }
.ch-name {
  flex: 1;
  font-size: 0.6rem;
  font-weight: 600;
  color: rgba(255,255,255,0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ch-dot {
  width: 5px; height: 5px;
  border-radius: 50%; flex-shrink: 0;
  transition: all 0.3s;
}
.ch-dot.pending { background: rgba(255,255,255,0.15); }
.ch-dot.processing {
  background: #38bdf8;
  box-shadow: 0 0 4px rgba(56,189,248,0.5);
  animation: dotP 1.2s ease-in-out infinite;
}
.ch-dot.completed { background: #34d399; box-shadow: 0 0 3px rgba(52,211,153,0.4); }
.ch-dot.error {
  background: #ef4444;
  box-shadow: 0 0 3px rgba(239,68,68,0.4);
  animation: errD 0.5s ease-in-out infinite;
}
@keyframes dotP { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(1.3)} }
@keyframes errD { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* 实时内容 */
.chip-live {
  padding: 1px 7px 3px;
  min-height: 12px;
}
.lv-line {
  display: flex; align-items: center;
  gap: 3px;
}
.lv-ico { font-size: 0.5rem; flex-shrink: 0; }
.lv-txt {
  font-size: 0.55rem;
  color: rgba(255,255,255,0.5);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}
.lv-txt.stream {
  animation: txtFade 0.25s ease;
}
.stt .lv-txt { color: #7dd3fc; }
.llm .lv-txt { color: #c4b5fd; }
@keyframes txtFade {
  from { opacity: 0.4; }
  to { opacity: 1; }
}

/* 上下文标签 */
.lv-tags {
  display: flex; gap: 2px;
  flex-wrap: wrap;
}
.tg {
  font-size: 0.47rem;
  padding: 0 3px;
  border-radius: 3px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.25);
  line-height: 1.5;
}
.tg.on {
  background: rgba(56,189,248,0.08);
  border-color: rgba(56,189,248,0.12);
  color: rgba(255,255,255,0.55);
}

/* 进度条 */
.chip-prog {
  position: absolute; bottom: 0; left: 0; right: 0;
  height: 1.5px; overflow: hidden;
  border-radius: 0 0 8px 8px;
}
.prog-bar {
  height: 100%; width: 30%;
  background: linear-gradient(90deg, transparent, #38bdf8, transparent);
  animation: progS 1s ease-in-out infinite;
}
@keyframes progS {
  0% { transform: translateX(-80%); width: 60%; }
  100% { transform: translateX(120%); width: 60%; }
}

/* 类型风格 */
.t-stt_listen { border-left: 2px solid #38bdf8; }
.t-llm { border-left: 2px solid #a78bfa; }
.t-ocr { border-left: 2px solid #f59e0b; }
.t-tts { border-left: 2px solid #34d399; }
.t-context_build { border-left: 2px solid #f97316; }
.t-input_image { border-left: 2px solid #94a3b8; }
.t-ts_output { border-left: 2px solid #6ee7b7; }
</style>
