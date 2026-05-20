<script setup>
import { ref } from 'vue'
import Sidebar from './Sidebar.vue'
import ChatArea from './ChatArea.vue'
import StatsBadge from './StatsBadge.vue'

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
      <div class="main-content">
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
