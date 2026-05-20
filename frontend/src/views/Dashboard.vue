<script setup>
import { ref, onMounted } from 'vue'
import { listBodyMetrics, listDietMeals, listWorkouts } from '../services/api.js'
import WeightChart from '../components/WeightChart.vue'

const trend = ref({ dates: [], weights: [], body_fats: [], weight_change: 0, avg_weight: 0 })
const nutrition = ref({ avg_daily_calories: 0, avg_daily_protein: 0, avg_daily_fat: 0, avg_daily_carbs: 0 })
const workoutStats = ref({ total_sessions: 0, frequency_per_week: 0, volume_trend: [], volume_change_pct: 0 })
const loading = ref(true)

onMounted(async () => {
  try {
    const [bodyData, dietData, workoutData] = await Promise.all([
      listBodyMetrics(90),
      listDietMeals(),
      listWorkouts(),
    ])
    if (bodyData.trend) trend.value = bodyData.trend
    if (dietData.daily_summaries?.length) {
      const recent = dietData.daily_summaries.slice(-7)
      const n = recent.length
      nutrition.value = {
        avg_daily_calories: Math.round(recent.reduce((s, d) => s + d.total_calories, 0) / n),
        avg_daily_protein: Math.round(recent.reduce((s, d) => s + d.total_protein, 0) / n * 10) / 10,
        avg_daily_fat: Math.round(recent.reduce((s, d) => s + d.total_fat, 0) / n * 10) / 10,
        avg_daily_carbs: Math.round(recent.reduce((s, d) => s + d.total_carbs, 0) / n),
      }
    }
    if (workoutData.length) {
      const sess = workoutData
      const vols = sess.map(s => s.total_volume).filter(v => v > 0)
      workoutStats.value = {
        total_sessions: sess.length,
        frequency_per_week: Math.round(sess.length / 4 * 10) / 10,
        volume_trend: vols,
        volume_change_pct: vols.length >= 2 ? Math.round((vols[vols.length - 1] - vols[0]) / vols[0] * 100) : 0,
      }
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard">
    <h2 class="page-title">仪表盘</h2>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else class="cards">
      <div class="card">
        <h3>体重趋势</h3>
        <WeightChart :dates="trend.dates" :weights="trend.weights" />
        <div class="card-stats">
          <span>平均 {{ trend.avg_weight }}kg</span>
          <span :class="trend.weight_change >= 0 ? 'up' : 'down'">
            {{ trend.weight_change >= 0 ? '+' : '' }}{{ trend.weight_change }}kg
          </span>
        </div>
      </div>

      <div class="card">
        <h3>本周营养</h3>
        <div class="stat-grid">
          <div class="stat"><span class="label">热量</span><span class="value">{{ nutrition.avg_daily_calories }} kcal</span></div>
          <div class="stat"><span class="label">蛋白质</span><span class="value">{{ nutrition.avg_daily_protein }}g</span></div>
          <div class="stat"><span class="label">脂肪</span><span class="value">{{ nutrition.avg_daily_fat }}g</span></div>
          <div class="stat"><span class="label">碳水</span><span class="value">{{ nutrition.avg_daily_carbs }}g</span></div>
        </div>
      </div>

      <div class="card">
        <h3>本周训练</h3>
        <div class="stat-grid">
          <div class="stat"><span class="label">次数</span><span class="value">{{ workoutStats.total_sessions }}</span></div>
          <div class="stat"><span class="label">频率</span><span class="value">{{ workoutStats.frequency_per_week }}次/周</span></div>
          <div class="stat">
            <span class="label">容量趋势</span>
            <span class="value" :class="workoutStats.volume_change_pct >= 0 ? 'up' : 'down'">
              {{ workoutStats.volume_change_pct >= 0 ? '+' : '' }}{{ workoutStats.volume_change_pct }}%
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard { padding: 24px; max-width: 960px; margin: 0 auto; height: 100%; overflow-y: auto; }
.page-title { font-size: 1.3rem; font-weight: 700; margin-bottom: 20px; }
.loading { text-align: center; color: var(--text-muted); padding: 40px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.card {
  background: var(--white); border-radius: var(--radius); padding: 18px;
  box-shadow: var(--shadow-sm);
}
.card h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 12px; color: var(--text); }
.card-stats { display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.85rem; color: var(--text-muted); }
.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat .label { font-size: 0.75rem; color: var(--text-muted); }
.stat .value { font-size: 1.1rem; font-weight: 700; }
.up { color: var(--coral); }
.down { color: var(--green-500); }
</style>
