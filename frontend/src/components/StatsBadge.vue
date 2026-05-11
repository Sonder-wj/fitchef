<script setup>
import { ref, watch } from 'vue'
import { getKnowledgeStats } from '../services/api.js'

const props = defineProps({ show: Boolean })

const stats = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    stats.value = await getKnowledgeStats()
  } catch (e) {
    error.value = e.message
    stats.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.show, (val) => {
  if (val) load()
})
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="overlay" @click.self="$emit('close')">
      <div class="stats-card">
        <div class="stats-head">
          <h3>📊 知识库统计</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>

        <div v-if="loading" class="stats-loading">加载中...</div>
        <div v-else-if="error" class="stats-error">{{ error }}</div>
        <div v-else-if="stats" class="stats-grid">
          <div class="stat-item">
            <span class="stat-num">{{ stats.ingredients || 0 }}</span>
            <span class="stat-label">食材数据</span>
          </div>
          <div class="stat-item">
            <span class="stat-num">{{ stats.recipes || 0 }}</span>
            <span class="stat-label">食谱</span>
          </div>
          <div class="stat-item">
            <span class="stat-num">{{ stats.guidelines || 0 }}</span>
            <span class="stat-label">膳食指南</span>
          </div>
          <div class="stat-item highlight">
            <span class="stat-num">{{ stats.total_chunks || 0 }}</span>
            <span class="stat-label">总文档数</span>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.stats-card {
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: 28px 32px;
  width: 360px;
  max-width: 90vw;
  box-shadow: var(--shadow-lg);
  animation: scaleUp 0.25s ease;
}

@keyframes scaleUp {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.stats-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.stats-head h3 {
  font-family: var(--font-display);
  font-size: 1.8rem;
  color: var(--green-700);
}

.close-btn {
  width: 32px;
  height: 32px;
  background: none;
  border: none;
  font-size: 1.4rem;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.close-btn:hover {
  background: var(--cream-dark);
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-item {
  background: var(--cream);
  border-radius: var(--radius);
  padding: 20px 16px;
  text-align: center;
}

.stat-item.highlight {
  background: var(--green-100);
  grid-column: span 2;
}

.stat-num {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  color: var(--green-700);
  font-family: var(--font-display);
}

.stat-label {
  display: block;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.stats-loading,
.stats-error {
  text-align: center;
  padding: 20px;
  color: var(--text-muted);
}

.stats-error {
  color: var(--coral);
}
</style>
