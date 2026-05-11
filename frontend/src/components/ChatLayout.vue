<script setup>
import { ref } from 'vue'
import Sidebar from './Sidebar.vue'
import ChatArea from './ChatArea.vue'
import StatsBadge from './StatsBadge.vue'

const props = defineProps({ user: Object })
const emit = defineEmits(['logout'])

const convId = ref(null)
const showSidebar = ref(true)
const showStats = ref(false)
const refreshKey = ref(0)

function onSelectConv(id) {
  convId.value = id
}

function onNewChat(id) {
  if (id) {
    convId.value = id
  } else {
    convId.value = null
    refreshKey.value++
  }
}

function onConvUpdated(id) {
  convId.value = id
}
</script>

<template>
  <div class="chat-layout">
    <Sidebar
      :active-conv-id="convId"
      :show="showSidebar"
      @select-conv="onSelectConv"
      @new-chat="onNewChat"
      @refresh-stats="showStats = true"
    />

    <div class="main-panel">
      <header class="top-bar">
        <button class="menu-btn" @click="showSidebar = !showSidebar">☰</button>
        <div class="top-title">
          <span v-if="convId">对话 #{{ convId }}</span>
          <span v-else>新对话</span>
        </div>
        <div class="top-right">
          <span class="user-tag">{{ user?.email || user?.name || '' }}</span>
          <button class="logout-btn" @click="emit('logout')">退出</button>
        </div>
      </header>

      <div class="main-content">
        <!-- Mobile sidebar overlay -->
        <div v-if="showSidebar" class="sidebar-overlay" @click="showSidebar = false"></div>

        <ChatArea
          :conv-id="convId"
          :key="refreshKey"
          @conv-updated="onConvUpdated"
        />
      </div>
    </div>

    <StatsBadge :show="showStats" @close="showStats = false" />
  </div>
</template>

<style scoped>
.chat-layout {
  width: 100%;
  height: 100%;
  display: flex;
}

.main-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
}

.top-bar {
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 56px;
  background: var(--white);
  border-bottom: 1px solid var(--border);
  gap: 16px;
  flex-shrink: 0;
}

.menu-btn {
  width: 36px;
  height: 36px;
  background: none;
  border: none;
  font-size: 1.3rem;
  cursor: pointer;
  color: var(--text);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.menu-btn:hover {
  background: var(--cream-dark);
}

.top-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text);
}

.top-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-tag {
  font-size: 0.82rem;
  color: var(--text-muted);
}

.logout-btn {
  padding: 6px 16px;
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  font-family: var(--font-body);
  color: var(--text-muted);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.logout-btn:hover {
  border-color: var(--coral);
  color: var(--coral);
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.sidebar-overlay {
  display: none;
}

@media (max-width: 768px) {
  .sidebar-overlay {
    display: block;
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.3);
    z-index: 40;
  }
}
</style>
