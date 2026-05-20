<script setup>
import { ref, onMounted } from 'vue'
import { listBodyMetrics, createBodyMetric, updateBodyMetric, deleteBodyMetric } from '../services/api.js'
import WeightChart from '../components/WeightChart.vue'

const metrics = ref([])
const trend = ref({ dates: [], weights: [], body_fats: [], weight_change: 0, avg_weight: 0 })
const showForm = ref(false)
const editData = ref(null)

const form = ref({ date: '', weight_kg: '', body_fat_pct: '', notes: '' })

async function load() {
  try {
    const data = await listBodyMetrics(90)
    metrics.value = data.metrics || []
    if (data.trend) trend.value = data.trend
  } catch {}
}

function openNew() {
  editData.value = null
  form.value = { date: new Date().toISOString().slice(0, 10), weight_kg: '', body_fat_pct: '', notes: '' }
  showForm.value = true
}

function openEdit(m) {
  editData.value = m
  form.value = { date: m.date, weight_kg: m.weight_kg, body_fat_pct: m.body_fat_pct, notes: m.notes || '' }
  showForm.value = true
}

async function onSave() {
  const payload = {
    date: form.value.date,
    weight_kg: parseFloat(form.value.weight_kg),
    body_fat_pct: form.value.body_fat_pct ? parseFloat(form.value.body_fat_pct) : null,
    notes: form.value.notes || null,
  }
  try {
    if (editData.value?.id) {
      await updateBodyMetric(editData.value.id, payload)
    } else {
      await createBodyMetric(payload)
    }
    showForm.value = false
    await load()
  } catch (e) { alert(e.message) }
}

async function onDelete(id) {
  if (!confirm('确定删除？')) return
  try { await deleteBodyMetric(id); await load() } catch {}
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h2>身体指标</h2>
      <button class="btn-primary" @click="openNew">+ 记录</button>
    </div>

    <div class="card" v-if="trend.dates.length > 0">
      <h3>体重趋势 (90天)</h3>
      <WeightChart :dates="trend.dates" :weights="trend.weights" />
      <div class="trend-stats">
        <span>平均 {{ trend.avg_weight }}kg</span>
        <span :class="trend.weight_change >= 0 ? 'up' : 'down'">
          {{ trend.weight_change >= 0 ? '+' : '' }}{{ trend.weight_change }}kg
        </span>
      </div>
    </div>

    <div v-if="metrics.length === 0" class="empty">暂无记录</div>

    <div v-for="m in metrics" :key="m.id" class="item">
      <div class="item-main">
        <span class="item-date">{{ m.date }}</span>
        <span class="item-weight">{{ m.weight_kg }}kg</span>
        <span v-if="m.body_fat_pct" class="item-fat">{{ m.body_fat_pct }}%</span>
        <span v-if="m.notes" class="item-notes">{{ m.notes }}</span>
      </div>
      <div class="item-actions">
        <button class="btn-text" @click="openEdit(m)">编辑</button>
        <button class="btn-text danger" @click="onDelete(m.id)">删除</button>
      </div>
    </div>

    <div v-if="showForm" class="form-overlay" @click.self="showForm = false">
      <div class="form-panel">
        <h3>{{ editData ? '编辑' : '记录' }}身体指标</h3>
        <label>日期 <input type="date" v-model="form.date" /></label>
        <label>体重(kg) <input type="number" v-model="form.weight_kg" step="0.1" min="0" /></label>
        <label>体脂率(%) <input type="number" v-model="form.body_fat_pct" step="0.1" min="0" max="60" /> <span class="hint">可用体脂秤，可留空</span></label>
        <label>备注 <input v-model="form.notes" placeholder="可选" /></label>
        <div class="form-actions">
          <button class="btn-save" @click="onSave">保存</button>
          <button class="btn-cancel" @click="showForm = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 640px; margin: 0 auto; height: 100%; overflow-y: auto; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-head h2 { font-size: 1.3rem; font-weight: 700; }
.btn-primary { padding: 8px 18px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.card { background: var(--white); border-radius: var(--radius); padding: 18px; margin-bottom: 16px; box-shadow: var(--shadow-sm); }
.card h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 12px; }
.trend-stats { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted); margin-top: 8px; }
.empty { text-align: center; color: var(--text-muted); padding: 40px; }
.item { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: var(--white); border-radius: var(--radius-sm); margin-bottom: 6px; box-shadow: var(--shadow-sm); }
.item-main { display: flex; gap: 14px; align-items: center; }
.item-date { font-weight: 600; font-size: 0.88rem; }
.item-weight { font-size: 1rem; font-weight: 700; }
.item-fat { font-size: 0.82rem; color: var(--text-muted); }
.item-notes { font-size: 0.8rem; color: var(--text-muted); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-actions { display: flex; gap: 8px; }
.btn-text { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.82rem; font-family: var(--font-body); }
.btn-text:hover { color: var(--text); }
.btn-text.danger:hover { color: var(--coral); }
.up { color: var(--coral); }
.down { color: var(--green-500); }
.form-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 100; display: flex; align-items: flex-start; justify-content: center; padding-top: 80px; }
.form-panel { background: var(--white); border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 400px; box-shadow: var(--shadow-lg); display: flex; flex-direction: column; gap: 12px; }
.form-panel h3 { font-size: 1.1rem; }
.form-panel label { font-size: 0.82rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; }
.form-panel input { padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.88rem; font-family: var(--font-body); }
.hint { font-size: 0.72rem; color: var(--text-muted); }
.form-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }
.btn-save { padding: 8px 24px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.btn-cancel { padding: 8px 16px; background: none; border: 1px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-body); }
</style>
