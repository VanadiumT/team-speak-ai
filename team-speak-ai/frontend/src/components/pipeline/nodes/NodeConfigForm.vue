<template>
  <div class="config-form">
    <div v-for="field in fields" :key="field.key" class="config-field">
      <label class="field-label">{{ field.label }}</label>
      <div class="field-control">
        <!-- text -->
        <input
          v-if="field.type === 'text'"
          type="text"
          class="field-input"
          :value="config[field.key] ?? ''"
          :placeholder="field.placeholder"
          :disabled="readonly || field.disabled"
          @input="emitUpdate(field.key, $event.target.value)"
        />

        <!-- number -->
        <input
          v-else-if="field.type === 'number'"
          type="number"
          class="field-input"
          :value="config[field.key] ?? ''"
          :min="field.min"
          :max="field.max"
          :step="field.step"
          :placeholder="field.placeholder"
          :disabled="readonly || field.disabled"
          @input="emitUpdate(field.key, Number($event.target.value))"
        />

        <!-- textarea -->
        <textarea
          v-else-if="field.type === 'textarea'"
          class="field-textarea"
          :value="config[field.key] ?? ''"
          :placeholder="field.placeholder"
          :disabled="readonly || field.disabled"
          rows="4"
          @input="emitUpdate(field.key, $event.target.value)"
        />

        <!-- switch -->
        <label v-else-if="field.type === 'switch'" class="switch-toggle">
          <input
            type="checkbox"
            :checked="!!config[field.key]"
            :disabled="readonly || field.disabled"
            @change="emitUpdate(field.key, $event.target.checked)"
          />
          <span class="switch-slider" />
        </label>

        <!-- range -->
        <div v-else-if="field.type === 'range'" class="range-wrap">
          <input
            type="range"
            class="field-range"
            :value="config[field.key] ?? field.min ?? 0"
            :min="field.min ?? 0"
            :max="field.max ?? 100"
            :step="field.step ?? 1"
            :disabled="readonly || field.disabled"
            @input="emitUpdate(field.key, Number($event.target.value))"
          />
          <span class="range-value">{{ config[field.key] ?? field.min ?? 0 }}</span>
        </div>

        <!-- select -->
        <select
          v-else-if="field.type === 'select'"
          class="field-select"
          :value="config[field.key] ?? ''"
          :disabled="readonly || field.disabled"
          @change="emitUpdate(field.key, $event.target.value)"
        >
          <option v-for="opt in field.options" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>

        <!-- chip-toggle -->
        <div v-else-if="field.type === 'chip-toggle'" class="chip-toggle-group">
          <button
            v-for="opt in field.options"
            :key="opt.value"
            class="chip-btn"
            :class="{ active: config[field.key] === opt.value }"
            :disabled="readonly || field.disabled"
            @click="emitUpdate(field.key, opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>

        <!-- tags -->
        <div v-else-if="field.type === 'tags'" class="tags-wrap">
          <span v-for="(tag, i) in (config[field.key] || [])" :key="i" class="tag-item">
            {{ tag }}
            <button
              v-if="!readonly && !field.disabled"
              class="tag-remove"
              @click="removeTag(field.key, i)"
            >&times;</button>
          </span>
          <input
            v-if="!readonly && !field.disabled"
            class="tag-input"
            :placeholder="field.placeholder || '+ 添加'"
            @keydown.enter.prevent="addTag(field.key, $event)"
          />
        </div>

        <!-- checkbox-group -->
        <div v-else-if="field.type === 'checkbox-group'" class="checkbox-group">
          <label v-for="opt in field.options" :key="opt.value" class="checkbox-item">
            <input
              type="checkbox"
              :checked="(config[field.key] || []).includes(opt.value)"
              :disabled="readonly || field.disabled"
              @change="toggleCheckbox(field.key, opt.value, $event.target.checked)"
            />
            <span>{{ opt.label }}</span>
          </label>
        </div>

        <span v-if="field.description" class="field-hint">{{ field.description }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  config: { type: Object, default: () => ({}) },
  fields: { type: Array, default: () => [] },
  readonly: { type: Boolean, default: false }
})

const emit = defineEmits(['update'])

function emitUpdate(key, value) {
  emit('update', { key, value })
}

function addTag(key, event) {
  const val = event.target.value.trim()
  if (!val) return
  const arr = [...(props.config[key] || [])]
  arr.push(val)
  event.target.value = ''
  emit('update', { key, value: arr })
}

function removeTag(key, index) {
  const arr = [...(props.config[key] || [])]
  arr.splice(index, 1)
  emit('update', { key, value: arr })
}

function toggleCheckbox(key, val, checked) {
  const arr = [...(props.config[key] || [])]
  if (checked) {
    if (!arr.includes(val)) arr.push(val)
  } else {
    const idx = arr.indexOf(val)
    if (idx >= 0) arr.splice(idx, 1)
  }
  emit('update', { key, value: arr })
}
</script>

<style scoped>
.config-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.config-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 10px;
  font-weight: 500;
  font-family: 'Space Grotesk', sans-serif;
  letter-spacing: 0.05em;
  color: #8b90a0;
  text-transform: uppercase;
}

.field-input {
  height: 32px;
  padding: 0 10px;
  border-radius: 4px;
  border: 1px solid #414754;
  background: #10131b;
  color: #e0e2ed;
  font-size: 12px;
  font-family: 'Inter', sans-serif;
  outline: none;
  transition: border-color 0.15s;
}
.field-input:focus { border-color: #adc7ff; }
.field-input:disabled { opacity: 0.5; cursor: not-allowed; }

.field-textarea {
  padding: 8px 10px;
  border-radius: 4px;
  border: 1px solid #414754;
  background: #10131b;
  color: #e0e2ed;
  font-size: 12px;
  font-family: 'Inter', sans-serif;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}
.field-textarea:focus { border-color: #adc7ff; }
.field-textarea:disabled { opacity: 0.5; cursor: not-allowed; }

.field-select {
  height: 32px;
  padding: 0 8px;
  border-radius: 4px;
  border: 1px solid #414754;
  background: #10131b;
  color: #e0e2ed;
  font-size: 12px;
  font-family: 'Inter', sans-serif;
  outline: none;
  cursor: pointer;
}
.field-select:focus { border-color: #adc7ff; }
.field-select:disabled { opacity: 0.5; cursor: not-allowed; }

.switch-toggle {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  cursor: pointer;
}
.switch-toggle input { opacity: 0; width: 0; height: 0; }
.switch-slider {
  position: absolute;
  inset: 0;
  background: #31353d;
  border-radius: 11px;
  transition: background 0.2s;
}
.switch-slider::before {
  content: '';
  position: absolute;
  width: 16px; height: 16px;
  left: 3px; top: 3px;
  background: #8b90a0;
  border-radius: 50%;
  transition: transform 0.2s, background 0.2s;
}
.switch-toggle input:checked + .switch-slider { background: rgba(173, 199, 255, 0.3); }
.switch-toggle input:checked + .switch-slider::before {
  transform: translateX(18px);
  background: #adc7ff;
}
.switch-toggle input:disabled + .switch-slider { opacity: 0.4; cursor: not-allowed; }

.range-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.field-range {
  flex: 1;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: #31353d;
  border-radius: 2px;
  outline: none;
  cursor: pointer;
}
.field-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px; height: 14px;
  border-radius: 50%;
  background: #adc7ff;
  cursor: pointer;
}
.field-range:disabled { opacity: 0.4; cursor: not-allowed; }
.range-value {
  font-size: 11px;
  font-family: 'Space Grotesk', sans-serif;
  color: #c1c6d7;
  min-width: 32px;
  text-align: right;
}

.chip-toggle-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.chip-btn {
  padding: 4px 10px;
  border-radius: 9999px;
  border: 1px solid #414754;
  background: transparent;
  color: #8b90a0;
  font-size: 10px;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 500;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all 0.15s;
}
.chip-btn:hover { color: #c1c6d7; border-color: #8b90a0; }
.chip-btn.active {
  color: #adc7ff;
  border-color: #adc7ff;
  background: rgba(173, 199, 255, 0.1);
}
.chip-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}
.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  border-radius: 9999px;
  background: rgba(255, 182, 149, 0.1);
  border: 1px solid rgba(239, 103, 25, 0.3);
  color: #ffb695;
  font-size: 10px;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 500;
}
.tag-remove {
  background: none;
  border: none;
  color: #ffb695;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  opacity: 0.6;
}
.tag-remove:hover { opacity: 1; }
.tag-input {
  height: 24px;
  width: 80px;
  padding: 0 8px;
  border-radius: 9999px;
  border: 1px dashed #414754;
  background: transparent;
  color: #8b90a0;
  font-size: 10px;
  font-family: 'Inter', sans-serif;
  outline: none;
}
.tag-input:focus { border-color: #adc7ff; color: #e0e2ed; }

.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.checkbox-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-family: 'Inter', sans-serif;
  color: #c1c6d7;
  cursor: pointer;
}
.checkbox-item input { accent-color: #adc7ff; }

.field-hint {
  font-size: 9px;
  color: #64748b;
  font-family: 'Inter', sans-serif;
}
</style>
