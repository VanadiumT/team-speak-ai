<template>
  <div class="text-input">
    <textarea
      v-model="text"
      :placeholder="placeholder"
      rows="4"
      class="input-area"
    ></textarea>
    <button class="send-btn" :disabled="!text.trim()" @click="doSend">
      发送
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  placeholder: { type: String, default: '输入文本...' },
})

const emit = defineEmits(['submit'])

const text = ref('')

const doSend = () => {
  if (!text.value.trim()) return
  emit('submit', text.value.trim())
  text.value = ''
}
</script>

<style scoped>
.text-input { max-width: 500px; }
.input-area {
  width: 100%;
  padding: 12px;
  background: #0f3460;
  border: 1px solid #1a1a2e;
  border-radius: 8px;
  color: #eaeaea;
  font-size: 0.9rem;
  resize: vertical;
  font-family: inherit;
}
.input-area:focus { outline: none; border-color: #e94560; }
.send-btn {
  margin-top: 10px;
  padding: 8px 20px;
  background: #e94560;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
}
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
