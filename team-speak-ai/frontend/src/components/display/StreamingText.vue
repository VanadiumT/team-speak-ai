<template>
  <div class="stream">
    <div class="st-reason" v-if="reasoning">
      <div class="st-rlbl">🤔 思考过程</div>
      <div class="st-rtxt">{{ reasoning }}</div>
    </div>
    <div class="st-body">
      <div class="st-lbl">{{ label }}</div>
      <span class="st-txt">{{ content }}</span>
      <span v-if="streaming" class="st-cur">▊</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  content: { type: String, default: '' },
  reasoning: { type: String, default: '' },
  streaming: { type: Boolean, default: false },
  label: { type: String, default: '' },
})
</script>

<style scoped>
.stream { line-height: 1.5; }

.st-reason {
  background: rgba(0,0,0,0.12);
  border-left: 2px solid rgba(251,191,36,0.25);
  border-radius: 4px;
  padding: 6px 10px;
  margin-bottom: 8px;
}
.st-rlbl { font-size: 0.55rem; color: rgba(255,255,255,0.2); margin-bottom: 3px; }
.st-rtxt { font-size: 0.65rem; color: rgba(255,255,255,0.35); font-style: italic; white-space: pre-wrap; }

.st-body { }
.st-lbl { font-size: 0.55rem; color: rgba(255,255,255,0.2); margin-bottom: 2px; }
.st-txt {
  font-size: 0.72rem; color: rgba(255,255,255,0.65);
  white-space: pre-wrap; word-break: break-word;
}
.st-cur {
  color: #e94560;
  animation: blink 0.9s step-end infinite;
  margin-left: 1px;
}
@keyframes blink { 50% { opacity: 0; } }
</style>
