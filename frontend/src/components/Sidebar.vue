<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { listConversations, createConversation, deleteConversation, getMessages } from '../services/api.js'

const props = defineProps({ activeConvId: Number, show: Boolean })
const emit = defineEmits(['select-conv', 'new-chat', 'refresh-stats'])

const convs = ref([])
const loading = ref(false)

async function loadConvs() {
  try {
    convs.value = await listConversations()
  } catch {
    convs.value = []
  }
}

async function newChat() {
  try {
    const conv = await createConversation()
    await loadConvs()
    emit('new-chat', conv.id)
  } catch {}
}

async function removeConv(id) {
  if (!confirm('确定删除这个会话？')) return
  try {
    await deleteConversation(id)
    await loadConvs()
    if (props.activeConvId === id) {
      emit('new-chat', null)
    }
  } catch {}
}

function select(conv) {
  emit('select-conv', conv.id)
}

onMounted(loadConvs)
</script>

<template>
  <aside class="sidebar" :class="{ open: show }">
    <div class="sidebar-head">
      <div class="brand">
        <span class="brand-icon">🥗</span>
        <span class="brand-name">FitChef</span>
      </div>
      <button class="btn-new" @click="newChat">＋ 新对话</button>
    </div>

    <div class="conv-list">
      <div v-if="convs.length === 0" class="empty">
        <span class="empty-icon">💬</span>
        <p>还没有对话<br>点击上方开始</p>
      </div>
      <div
        v-for="conv in convs"
        :key="conv.id"
        class="conv-item"
        :class="{ active: conv.id === activeConvId }"
        @click="select(conv)"
      >
        <div class="conv-info">
          <div class="conv-title">{{ conv.title || '新对话' }}</div>
          <div class="conv-date">{{ conv.created_at?.slice(0, 10) || '' }}</div>
        </div>
        <button class="btn-del" @click.stop="removeConv(conv.id)" title="删除">×</button>
      </div>
    </div>

    <div class="sidebar-foot">
      <button class="btn-stats" @click="emit('refresh-stats')" title="知识库统计">
        📊 知识库
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 280px;
  min-width: 280px;
  height: 100%;
  background: var(--green-900);
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255,255,255,0.05);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-head {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.brand-icon {
  font-size: 1.6rem;
}

.brand-name {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.btn-new {
  width: 100%;
  padding: 10px;
  background: var(--green-500);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-weight: 600;
  font-family: var(--font-body);
  cursor: pointer;
  transition: background 0.2s;
}

.btn-new:hover {
  background: var(--green-300);
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
}

.conv-list::-webkit-scrollbar {
  width: 4px;
}
.conv-list::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.12);
  border-radius: 2px;
}

.empty {
  text-align: center;
  padding: 40px 20px;
  color: rgba(255,255,255,0.35);
}

.empty-icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 10px;
}

.empty p {
  font-size: 0.85rem;
  line-height: 1.5;
}

.conv-item {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}

.conv-item:hover {
  background: rgba(255,255,255,0.06);
}

.conv-item.active {
  background: rgba(255,255,255,0.1);
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-title {
  color: rgba(255,255,255,0.85);
  font-size: 0.88rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-date {
  color: rgba(255,255,255,0.3);
  font-size: 0.72rem;
  margin-top: 2px;
}

.btn-del {
  width: 24px;
  height: 24px;
  background: none;
  border: none;
  color: rgba(255,255,255,0.2);
  font-size: 1.1rem;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: color 0.15s, background 0.15s;
}

.btn-del:hover {
  color: var(--coral);
  background: rgba(255,255,255,0.08);
}

.sidebar-foot {
  padding: 12px 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
}

.btn-stats {
  width: 100%;
  padding: 8px;
  background: none;
  border: 1px dashed rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.5);
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  font-family: var(--font-body);
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}

.btn-stats:hover {
  border-color: rgba(255,255,255,0.3);
  color: rgba(255,255,255,0.75);
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 50;
    transform: translateX(-100%);
  }
  .sidebar.open {
    transform: translateX(0);
    box-shadow: var(--shadow-lg);
  }
}
</style>
