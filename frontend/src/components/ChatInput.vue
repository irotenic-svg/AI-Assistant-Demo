<template>
  <div class="chat-input-comp">
    <!-- Writing surface -->
    <div class="input-writing-surface">
      <div class="input-accent-strip"></div>
      <textarea
        ref="taRef"
        :value="modelValue"
        class="input-textarea"
        :placeholder="placeholder"
        :disabled="disabled"
        rows="2"
        @input="onInput"
        @keydown="handleKeydown"
      ></textarea>
    </div>

    <!-- Action bar -->
    <div class="input-action-bar">
      <span class="input-keyhint">
        <kbd>Enter</kbd> 发送 · <kbd>Shift</kbd> + <kbd>Enter</kbd> 换行
      </span>
      <button
        class="send-btn"
        :class="{ loading: loading, active: modelValue?.trim() && !disabled }"
        :disabled="!modelValue?.trim() || disabled"
        @click="$emit('send')"
        :title="loading ? '检索中…' : '发送'"
      >
        <span class="send-btn-hex">
          <span class="send-btn-icon">{{ loading ? '⏳' : '↑' }}</span>
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '描述您的医学问题…' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'send'])
const taRef = ref(null)

function onInput(e) {
  emit('update:modelValue', e.target.value)
  // Auto-resize
  const el = taRef.value
  if (el) {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 180) + 'px'
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}
</script>

<style scoped>
.chat-input-comp {
  max-width: 760px;
  margin: 0 auto;
}

.input-writing-surface {
  position: relative;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: border-color var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out);
}

.input-writing-surface:focus-within {
  border-color: rgba(196, 138, 64, 0.4);
  box-shadow: 0 0 0 3px var(--accent-glow),
    inset 0 0 40px rgba(196, 138, 64, 0.02);
}

.input-accent-strip {
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  background: linear-gradient(
    180deg, transparent 0%, var(--accent) 15%, var(--accent) 85%, transparent 100%
  );
  border-radius: 0 2px 2px 0;
  opacity: 0.35;
  transition: opacity var(--duration-normal) var(--ease-out);
}

.input-writing-surface:focus-within .input-accent-strip {
  opacity: 0.7;
}

.input-textarea {
  display: block;
  width: 100%;
  min-height: 52px;
  max-height: 180px;
  padding: 14px 18px 14px 22px;
  font-family: var(--font-body);
  font-size: 14.5px;
  line-height: 1.7;
  color: var(--text-primary);
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  caret-color: var(--accent);
  letter-spacing: 0.01em;
}

.input-textarea::placeholder {
  color: var(--text-muted);
  opacity: 0.45;
  font-style: italic;
}

.input-textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.input-keyhint {
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.55;
  letter-spacing: 0.02em;
}

.input-keyhint kbd {
  display: inline-block;
  padding: 2px 6px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: 3px;
  line-height: 1.4;
  vertical-align: 1px;
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  padding: 0;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: transform 0.15s ease;
}

.send-btn:active:not(:disabled) { transform: scale(0.92); }
.send-btn:disabled { cursor: not-allowed; opacity: 0.3; }

.send-btn-hex {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
  transition: all var(--duration-normal) var(--ease-out);
}

.send-btn.active .send-btn-hex {
  background: var(--accent);
  border-color: var(--accent);
}

.send-btn.active:hover .send-btn-hex {
  background: #d49a48;
  border-color: #d49a48;
  box-shadow: 0 0 28px var(--accent-glow-strong);
  transform: scale(1.08);
}

.send-btn.loading .send-btn-hex {
  background: var(--accent);
  border-color: var(--accent);
  animation: hexPulse2 1.8s ease-in-out infinite;
}

.send-btn-icon {
  font-size: 15px;
  color: var(--text-muted);
  line-height: 1;
  transition: color 0.15s ease;
}

.send-btn.active .send-btn-icon,
.send-btn.loading .send-btn-icon { color: #fff; }

@keyframes hexPulse2 {
  0%, 100% { box-shadow: 0 0 0 0 var(--accent-glow); }
  50% { box-shadow: 0 0 0 14px transparent; }
}

@media (max-width: 640px) {
  .input-textarea {
    padding: 12px 14px 12px 18px;
    font-size: 14px;
    min-height: 46px;
  }
  .send-btn { width: 40px; height: 40px; }
  .send-btn-hex { width: 34px; height: 34px; }
}
</style>
