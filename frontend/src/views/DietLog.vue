<script setup>
import { ref, onMounted } from 'vue'
import { listDietMeals, createDietMeal, updateDietMeal, deleteDietMeal } from '../services/api.js'
import DietMealForm from '../components/DietMealForm.vue'

const data = ref({ meals: [], daily_summaries: [] })
const showForm = ref(false)
const editData = ref(null)

async function load() {
  try { data.value = await listDietMeals() } catch {}
}

function groupedMeals() {
  const groups = {}
  for (const m of data.value.meals || []) {
    const d = m.date
    if (!groups[d]) groups[d] = []
    groups[d].push(m)
  }
  return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]))
}

const mealTypeLabels = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' }

async function onSave(formData) {
  try {
    if (editData.value?.id) {
      await updateDietMeal(editData.value.id, formData)
    } else {
      await createDietMeal(formData)
    }
    showForm.value = false; editData.value = null; await load()
  } catch (e) { alert(e.message) }
}

function onEdit(m) { editData.value = m; showForm.value = true }

async function onDelete(id) {
  if (!confirm('确定删除？')) return
  try { await deleteDietMeal(id); await load() } catch {}
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h2>饮食日志</h2>
      <button class="btn-primary" @click="editData = null; showForm = true">+ 记录饮食</button>
    </div>

    <div v-if="data.daily_summaries.length" class="daily-summaries">
      <div v-for="ds in data.daily_summaries.slice(-7).reverse()" :key="ds.date" class="summary-row">
        <span class="sum-date">{{ ds.date }}</span>
        <span>{{ ds.total_calories }}kcal</span>
        <span>P{{ ds.total_protein }}g</span>
      </div>
    </div>

    <div v-for="[date, meals] in groupedMeals()" :key="date" class="day-group">
      <h3 class="day-label">{{ date }}</h3>
      <div v-for="m in meals" :key="m.id" class="meal-item">
        <div class="meal-main">
          <span class="meal-type">{{ mealTypeLabels[m.meal_type] || m.meal_type }}</span>
          <span class="meal-total">{{ Math.round(m.total_calories) }}kcal</span>
          <span class="meal-items-list">{{ m.items?.map(i => i.food_name).join('、') }}</span>
        </div>
        <div class="meal-actions">
          <button class="btn-text" @click="onEdit(m)">编辑</button>
          <button class="btn-text danger" @click="onDelete(m.id)">删除</button>
        </div>
      </div>
    </div>

    <DietMealForm v-if="showForm" :initial="editData" @save="onSave" @cancel="showForm = false; editData = null" />
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 640px; margin: 0 auto; height: 100%; overflow-y: auto; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-head h2 { font-size: 1.3rem; font-weight: 700; }
.btn-primary { padding: 8px 18px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.daily-summaries { background: var(--white); border-radius: var(--radius); padding: 14px; margin-bottom: 16px; display: flex; gap: 20px; overflow-x: auto; box-shadow: var(--shadow-sm); }
.summary-row { display: flex; gap: 8px; font-size: 0.82rem; white-space: nowrap; }
.sum-date { font-weight: 600; }
.day-group { margin-bottom: 20px; }
.day-label { font-size: 0.95rem; font-weight: 600; margin-bottom: 8px; color: var(--text); }
.meal-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: var(--white); border-radius: var(--radius-sm); margin-bottom: 4px; box-shadow: var(--shadow-sm); }
.meal-main { display: flex; gap: 12px; align-items: center; }
.meal-type { background: var(--green-100); color: var(--green-700); padding: 2px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }
.meal-total { font-weight: 700; font-size: 0.9rem; }
.meal-items-list { font-size: 0.8rem; color: var(--text-muted); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meal-actions { display: flex; gap: 8px; }
.btn-text { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.82rem; font-family: var(--font-body); }
.btn-text:hover { color: var(--text); }
.btn-text.danger:hover { color: var(--coral); }
</style>
