<template>
  <div class="dp" v-if="node">
    <!-- 头部 -->
    <div class="dp-head">
      <span class="dp-icon">{{ nodeIcon }}</span>
      <span class="dp-name">{{ node.name }}</span>
      <span class="dp-st" :class="node.status">{{ statusText }}</span>
    </div>

    <!-- 主体：按状态 + 类型 -->
    <div class="dp-body">
      <!-- Pending -->
      <template v-if="node.status === 'pending'">
        <AudioFileUploader
          v-if="node.type === 'input_image'"
          accept="image/*"
          @upload="(file) => $emit('action', 'upload', file)"
        />
        <div v-else class="dp-empty">等待上游节点完成...</div>
      </template>

      <!-- Processing -->
      <template v-else-if="node.status === 'processing'">
        <StreamingText
          v-if="node.type === 'llm'"
          :content="node.summary || node.data?.content_full || ''"
          :reasoning="node.data?.reasoning || ''"
          :streaming="true"
        />
        <StreamingText
          v-else-if="node.type === 'stt_listen'"
          :content="node.data?.accumulated || node.data?.partial_text || ''"
          :streaming="true"
        />
        <div v-else class="dp-load">
          <span class="dp-spin"></span>
          <span>{{ node.summary || '处理中...' }}</span>
        </div>
      </template>

      <!-- Completed -->
      <template v-else-if="node.status === 'completed'">
        <div v-if="node.type === 'llm' || node.type === 'ocr'" class="dp-text-area">
          <div v-if="node.data?.reasoning" class="dp-reason">
            <div class="dp-rlbl">🤔 思考过程</div>
            <div class="dp-rtxt">{{ node.data.reasoning }}</div>
          </div>
          <div class="dp-rlbl">💬 结果</div>
          <div class="dp-txt">{{ node.data?.response || node.data?.content || node.data?.text || node.summary }}</div>
        </div>

        <div v-else-if="node.type === 'context_build'" class="dp-triple">
          <div class="dp-tr" v-if="node.data?.ocr_text">
            <div class="dp-trl">📷 OCR</div>
            <div class="dp-trt">{{ node.data.ocr_text }}</div>
          </div>
          <div class="dp-tr" v-if="node.data?.stt_text">
            <div class="dp-trl">🎤 STT</div>
            <div class="dp-trt">{{ node.data.stt_text }}</div>
          </div>
          <div class="dp-tr">
            <div class="dp-trl">💡 Skill</div>
            <div class="dp-trt">{{ skillPrompt || '已加载' }}</div>
          </div>
        </div>

        <div v-else-if="node.type === 'tts'" class="dp-audio">
          <span>{{ node.data?.audio_size ? `🔊 音频已生成 (${fmtSize(node.data.audio_size)})` : '已完成' }}</span>
        </div>

        <div v-else-if="node.type === 'ts_output'" class="dp-done">
          <span>{{ node.data?.sent ? '✅ 已发送到 TeamSpeak' : '已完成' }}</span>
        </div>

        <div v-else-if="node.type === 'stt_listen'" class="dp-text-area">
          <div class="dp-txt">{{ node.data?.text || node.data?.accumulated || '已完成监听' }}</div>
          <div class="dp-kw" v-if="node.data?.trigger_keyword">🎯 触发关键词: {{ node.data.trigger_keyword }}</div>
        </div>

        <div v-else class="dp-done">
          <span>{{ node.summary || '已完成' }}</span>
        </div>
      </template>

      <!-- Error -->
      <template v-else-if="node.status === 'error'">
        <div class="dp-err">
          <span class="dp-err-ico">❌</span>
          <span>{{ node.error || '未知错误' }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AudioFileUploader from '@/components/action/AudioFileUploader.vue'
import StreamingText from '@/components/display/StreamingText.vue'

const props = defineProps({
  node: { type: Object, default: null },
  skillPrompt: { type: String, default: '' },
})

defineEmits(['action'])

const nodeIcon = computed(() => ({
  input_image: '🖼️', ocr: '📝', stt_listen: '🎙️',
  context_build: '🔗', llm: '🧠', tts: '🔊', ts_output: '📡',
}[props.node?.type] || '⚙️'))

const statusText = computed(() => ({
  pending: '待执行', processing: '执行中', completed: '已完成', error: '出错',
}[props.node?.status] || props.node?.status))

const fmtSize = (b) => {
  if (!b) return '0 B'
  if (b < 1024) return b + ' B'
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1048576).toFixed(1) + ' MB'
}
</script>

<style scoped>
.dp {
  background: rgba(15,23,42,0.4);
  border: 1px solid rgba(148,163,184,0.06);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 8px;
  backdrop-filter: blur(8px);
}

/* 头部 */
.dp-head {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px;
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.dp-icon { font-size: 0.8rem; }
.dp-name { flex: 1; font-size: 0.7rem; font-weight: 600; color: rgba(255,255,255,0.75); }
.dp-st {
  font-size: 0.55rem; padding: 1px 8px; border-radius: 8px;
  text-transform: uppercase; letter-spacing: 0.3px;
}
.dp-st.pending { background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.25); }
.dp-st.processing { background: rgba(56,189,248,0.1); color: #38bdf8; }
.dp-st.completed { background: rgba(52,211,153,0.08); color: #34d399; }
.dp-st.error { background: rgba(239,68,68,0.1); color: #ef4444; }

/* 主体 */
.dp-body { padding: 10px 14px; max-height: 180px; overflow-y: auto; }

/* 空态/加载 */
.dp-empty {
  text-align: center; padding: 16px 0;
  font-size: 0.7rem; color: rgba(255,255,255,0.15);
}
.dp-load {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; padding: 16px 0;
  font-size: 0.7rem; color: rgba(255,255,255,0.3);
}
.dp-spin {
  width: 14px; height: 14px;
  border: 1.5px solid rgba(56,189,248,0.15);
  border-top-color: #38bdf8;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 文本区 */
.dp-text-area { }
.dp-rlbl {
  font-size: 0.55rem; color: rgba(255,255,255,0.2);
  text-transform: uppercase; letter-spacing: 0.4px;
  margin-bottom: 3px; margin-top: 6px;
}
.dp-rlbl:first-child { margin-top: 0; }
.dp-txt {
  font-size: 0.72rem; color: rgba(255,255,255,0.65);
  line-height: 1.5; white-space: pre-wrap;
}
.dp-reason {
  background: rgba(0,0,0,0.15);
  border-left: 2px solid rgba(251,191,36,0.3);
  border-radius: 4px;
  padding: 6px 10px;
  margin-bottom: 8px;
}
.dp-rtxt {
  font-size: 0.65rem; color: rgba(255,255,255,0.35);
  font-style: italic; white-space: pre-wrap; line-height: 1.4;
}

/* 三列上下文 */
.dp-triple {
  display: flex; gap: 8px;
}
.dp-tr {
  flex: 1; min-width: 0;
  background: rgba(0,0,0,0.12);
  border-radius: 6px;
  padding: 6px 8px;
}
.dp-trl {
  font-size: 0.5rem; color: rgba(255,255,255,0.25);
  margin-bottom: 2px; white-space: nowrap;
}
.dp-trt {
  font-size: 0.6rem; color: rgba(255,255,255,0.5);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* 完成/音频/关键词 */
.dp-done {
  text-align: center; padding: 12px 0;
  font-size: 0.72rem; color: rgba(255,255,255,0.4);
}
.dp-audio {
  text-align: center; padding: 12px 0;
  font-size: 0.72rem; color: #34d399;
}
.dp-kw {
  margin-top: 6px; font-size: 0.62rem; color: #fbbf24;
}

/* 错误 */
.dp-err {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 0;
  font-size: 0.7rem; color: #ef4444;
}
.dp-err-ico { font-size: 1rem; }
</style>
