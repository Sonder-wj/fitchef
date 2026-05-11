<script setup>
import { ref, watch, nextTick, onUnmounted } from 'vue'
import { sendMessage, getMessages } from '../services/api.js'
import MessageBubble from './MessageBubble.vue'

const props = defineProps({ convId: Number, key: Number })
const emit = defineEmits(['conv-updated'])

const messages = ref([])
const input = ref('')
const sending = ref(false)
const statusMsg = ref('')
const sources = ref([])
const searchResults = ref([])  // 检索到的知识库文档
const showSearch = ref(false)  // 是否展开检索结果
let scrollEl = null
let nextMsgId = 1
let streamingMsgId = 0

async function loadHistory() {
  if (!props.convId) return
  try {
    const msgs = await getMessages(props.convId)
    messages.value = msgs.map(m => ({
      id: nextMsgId++,
      role: m.sender === 'user' ? 'user' : 'bot',
      content: m.content,
      time: m.created_at ? m.created_at.slice(11, 19) : '',
    }))
    scrollDown()
  } catch {}
}

function scrollDown() {
  nextTick(() => {
    if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight
  })
}

function send() {
  const msg = input.value.trim()
  if (!msg || sending.value) return

  const uid = nextMsgId++
  const bid = nextMsgId++
  streamingMsgId = bid
  messages.value.push({ id: uid, role: 'user', content: msg, time: now() })
  messages.value.push({ id: bid, role: 'bot', content: '', time: '', streaming: true })

  input.value = ''
  sending.value = true
  statusMsg.value = ''
  sources.value = []
  searchResults.value = []
  showSearch.value = false
  scrollDown()

  sendMessage(msg, props.convId, {
    onToken(token) {
      const idx = messages.value.findIndex(m => m.id === streamingMsgId)
      if (idx >= 0) messages.value[idx].content += token
      scrollDown()
    },
    onEvent(type, data) {
      if (type === 'sources') {
        sources.value = data.sources || []
      } else if (type === 'query_rewrite') {
        statusMsg.value = (data.keywords || '').slice(0, 50)
      } else if (type === 'search_results') {
        searchResults.value = data.results || []
        statusMsg.value = '检索到 ' + (data.total || 0) + ' 篇文档'
      } else if (type === 'rerank') {
        statusMsg.value = '重排序完成'
      } else if (type === 'off_topic') {
        const idx = messages.value.findIndex(m => m.id === streamingMsgId)
        if (idx >= 0) {
          messages.value[idx] = { ...messages.value[idx], content: data.msg, streaming: false, time: now() }
        }
        streamingMsgId = 0
      } else if (type === 'conversation_id') {
        if (data.id && !props.convId) {
          emit('conv-updated', data.id)
        }
      } else if (type === 'error') {
        const idx = messages.value.findIndex(m => m.id === streamingMsgId)
        if (idx >= 0) {
          messages.value[idx] = { ...messages.value[idx], content: 'Error: ' + (data.msg || ''), streaming: false, time: now() }
        }
        streamingMsgId = 0
      }
    },
    onDone() {
      const idx = messages.value.findIndex(m => m.id === streamingMsgId)
      if (idx >= 0) {
        messages.value[idx] = { ...messages.value[idx], streaming: false, time: now() }
      }
      streamingMsgId = 0
      sending.value = false
      statusMsg.value = ''
      scrollDown()
    },
    onError(err) {
      const idx = messages.value.findIndex(m => m.id === streamingMsgId)
      if (idx >= 0) {
        messages.value[idx] = { ...messages.value[idx], content: 'Error: ' + err, streaming: false, time: now() }
      }
      streamingMsgId = 0
      sending.value = false
      statusMsg.value = ''
      scrollDown()
    }
  })
}

function now() {
  return new Date().toTimeString().slice(0, 8)
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

watch(() => props.convId, (newVal, oldVal) => {
  if (oldVal === null && newVal && streamingMsgId !== 0) {
    return
  }
  messages.value = []
  streamingMsgId = 0
  statusMsg.value = ''
  sources.value = []
  searchResults.value = []
  showSearch.value = false
  if (newVal) loadHistory()
}, { immediate: true })

watch(() => props.key, () => {
  messages.value = []
  streamingMsgId = 0
  statusMsg.value = ''
  sources.value = []
  searchResults.value = []
  showSearch.value = false
})
</script>

<template>
  <div class="chat-area">
    <div class="chat-messages" ref="scrollEl">
      <div v-if="messages.length === 0" class="welcome">
        <div class="welcome-icon">🥗</div>
        <h2>嗨，我是 FitChef！</h2>
        <p>你的私人健身营养助手。关于吃的，尽管问我——</p>
        <div class="hints">
          <button @click="input = '鸡胸肉怎么做好吃又不柴'; send()">🍗 鸡胸肉怎么做不柴？</button>
          <button @click="input = '减脂期晚餐可以吃什么'; send()">🥬 减脂晚餐吃什么？</button>
          <button @click="input = '增肌每天需要多少蛋白质'; send()">💪 增肌需要多少蛋白质？</button>
          <button @click="input = '番茄炒蛋的热量是多少'; send()">🍳 番茄炒蛋热量？</button>
        </div>
      </div>

      <MessageBubble
        v-for="m in messages"
        :key="m.id"
        :role="m.role"
        :content="m.content"
        :time="m.time"
        :streaming="m.streaming || false"
      />

      <div v-if="statusMsg" class="status-line">{{ statusMsg }}</div>
    </div>

    <!-- 检索结果面板 -->
    <div v-if="searchResults.length" class="search-panel">
      <button class="search-toggle" @click="showSearch = !showSearch">
        📚 检索到 {{ searchResults.length }} 篇文档（点击展开/收起）
        <span class="toggle-arrow" :class="{ open: showSearch }">▾</span>
      </button>
      <div v-if="showSearch" class="search-docs">
        <div v-for="(doc, i) in searchResults" :key="i" class="search-doc">
          <div class="doc-header">
            <span class="doc-idx">[{{ i + 1 }}]</span>
            <span class="doc-score">相关度: {{ (doc.score || doc.rrf_score || 0).toFixed(3) }}</span>
          </div>
          <div class="doc-content">{{ doc.content }}</div>
        </div>
      </div>
    </div>

    <!-- Sources -->
    <div v-if="sources.length" class="sources-bar">
      <span class="sources-label">📖 参考来源：</span>
      <span v-for="s in sources" :key="s.ref" class="source-tag">[{{ s.ref }}] {{ s.name }}</span>
    </div>

    <div class="chat-input-wrap">
      <textarea
        v-model="input"
        class="chat-input"
        placeholder="输入你的问题..."
        rows="1"
        @keydown="onKeydown"
        :disabled="sending"
      ></textarea>
      <button
        class="send-btn"
        @click="send"
        :disabled="!input.trim() || sending"
      >
        <span v-if="sending">⋯</span>
        <span v-else>↑</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  background: var(--cream);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.chat-messages::-webkit-scrollbar {
  width: 5px;
}
.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.08);
  border-radius: 3px;
}

.welcome {
  text-align: center;
  padding: 60px 20px 40px;
}

.welcome-icon {
  font-size: 4rem;
  margin-bottom: 16px;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

.welcome h2 {
  font-family: var(--font-display);
  font-size: 2.5rem;
  color: var(--green-700);
  margin-bottom: 8px;
}

.welcome p {
  color: var(--text-muted);
  font-size: 1rem;
  margin-bottom: 28px;
}

.hints {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 480px;
  margin: 0 auto;
}

.hints button {
  padding: 10px 18px;
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: 20px;
  font-size: 0.85rem;
  font-family: var(--font-body);
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s;
}

.hints button:hover {
  border-color: var(--green-500);
  background: var(--green-100);
  color: var(--green-700);
}


.status-line {
  text-align: center;
  padding: 6px;
  font-size: 0.78rem;
  color: var(--text-muted);
  opacity: 0.7;
}

.search-panel {
  border-top: 2px solid var(--green-300);
  background: #FAFAF7;
}

.search-toggle {
  width: 100%;
  padding: 10px 32px;
  background: none;
  border: none;
  font-size: 0.85rem;
  font-family: var(--font-body);
  color: var(--green-700);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  transition: background 0.15s;
}

.search-toggle:hover {
  background: rgba(0,0,0,0.03);
}

.toggle-arrow {
  transition: transform 0.2s;
  font-size: 0.7rem;
}

.toggle-arrow.open {
  transform: rotate(180deg);
}

.search-docs {
  padding: 0 32px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 360px;
  overflow-y: auto;
}

.search-doc {
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background: var(--cream-dark);
  font-size: 0.78rem;
}

.doc-idx {
  font-weight: 700;
  color: var(--green-700);
}

.doc-score {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.doc-content {
  padding: 10px 14px;
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
}

.sources-bar {
  padding: 8px 32px;
  background: var(--cream-dark);
  border-top: 1px solid var(--border);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 0.8rem;
}

.sources-label {
  color: var(--text-muted);
  font-weight: 600;
}

.source-tag {
  padding: 2px 10px;
  background: var(--green-100);
  color: var(--green-700);
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 500;
}

.chat-input-wrap {
  padding: 16px 32px 20px;
  display: flex;
  gap: 10px;
  align-items: flex-end;
  background: var(--white);
  border-top: 1px solid var(--border);
}

.chat-input {
  flex: 1;
  padding: 12px 18px;
  border: 2px solid var(--border);
  border-radius: 24px;
  font-size: 0.93rem;
  font-family: var(--font-body);
  color: var(--text);
  resize: none;
  outline: none;
  max-height: 120px;
  background: var(--cream);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.chat-input:focus {
  border-color: var(--green-500);
  box-shadow: 0 0 0 3px var(--green-100);
  background: var(--white);
}

.chat-input::placeholder {
  color: var(--text-muted);
  opacity: 0.55;
}

.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--green-500);
  color: white;
  border: none;
  font-size: 1.3rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s, transform 0.15s;
}

.send-btn:hover:not(:disabled) {
  background: var(--green-700);
  transform: scale(1.05);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
