<script setup>
import { computed } from 'vue'

const props = defineProps({
  role: { type: String, default: 'user' },
  content: { type: String, default: '' },
  time: { type: String, default: '' },
  streaming: { type: Boolean, default: false },
})

const isUser = computed(() => props.role === 'user')
const avatar = computed(() => isUser.value ? '👤' : '🥗')

function renderMd(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
}

const html = computed(() => isUser.value ? undefined : renderMd(props.content))
</script>

<template>
  <div class="msg" :class="{ user: isUser, bot: !isUser }">
    <div class="msg-avatar">{{ avatar }}</div>
    <div class="msg-body">
      <div class="msg-text" :class="{ streaming }">
        <template v-if="isUser">{{ content }}</template>
        <span v-else v-html="html"></span>
        <span v-if="streaming" class="cursor">|</span>
      </div>
      <div v-if="time" class="msg-time">{{ time }}</div>
    </div>
  </div>
</template>

<style scoped>
.msg {
  display: flex;
  gap: 12px;
  padding: 6px 0;
  animation: fadeUp 0.35s ease;
}

.msg.user {
  flex-direction: row-reverse;
}

.msg.bot {
  flex-direction: row;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.user .msg-avatar { background: var(--coral-light); }
.bot .msg-avatar { background: var(--green-100); }

.msg-body {
  max-width: 72%;
}

.msg-text {
  padding: 12px 18px;
  border-radius: var(--radius);
  font-size: 0.93rem;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.user .msg-text {
  background: var(--green-500);
  color: white;
  border-bottom-right-radius: 4px;
}

.bot .msg-text {
  background: var(--white);
  color: var(--text);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}

.msg-text.streaming {
  border-left: 3px solid var(--green-500);
}

.cursor {
  color: var(--green-500);
  animation: blink 0.8s step-end infinite;
  font-weight: 300;
}

@keyframes blink {
  50% { opacity: 0; }
}

.msg-time {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 4px;
}
</style>
