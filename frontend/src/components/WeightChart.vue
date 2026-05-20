<script setup>
import { computed } from 'vue'

const props = defineProps({
  dates: { type: Array, default: () => [] },
  weights: { type: Array, default: () => [] },
})

const points = computed(() => {
  if (!props.weights.length) return ''
  const w = 260; const h = 100; const pad = 10
  const max = Math.max(...props.weights) + 2
  const min = Math.min(...props.weights) - 2
  const range = max - min || 1
  return props.weights.map((v, i) => {
    const x = pad + (i / Math.max(props.weights.length - 1, 1)) * (w - pad * 2)
    const y = h - pad - ((v - min) / range) * (h - pad * 2)
    return `${x},${y}`
  }).join(' ')
})

const hasData = computed(() => props.weights.length > 0)
</script>

<template>
  <div class="chart-wrap">
    <svg v-if="hasData" viewBox="0 0 260 100" class="chart-svg">
      <polyline :points="points" fill="none" stroke="var(--green-500)" stroke-width="2" />
    </svg>
    <div v-else class="no-data">暂无数据</div>
  </div>
</template>

<style scoped>
.chart-wrap { width: 100%; }
.chart-svg { width: 100%; height: auto; }
.no-data { text-align: center; color: var(--text-muted); padding: 20px; font-size: 0.85rem; }
</style>
