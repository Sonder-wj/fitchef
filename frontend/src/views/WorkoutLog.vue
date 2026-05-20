<script setup>
import { ref, onMounted } from 'vue'
import { listWorkouts, createWorkout, updateWorkout, deleteWorkout } from '../services/api.js'
import WorkoutForm from '../components/WorkoutForm.vue'

const workouts = ref([])
const showForm = ref(false)
const editData = ref(null)

async function load() {
  try { workouts.value = await listWorkouts() } catch {}
}

async function onSave(data) {
  try {
    if (editData.value?.id) {
      await updateWorkout(editData.value.id, data)
    } else {
      await createWorkout(data)
    }
    showForm.value = false
    editData.value = null
    await load()
  } catch (e) { alert(e.message) }
}

function onEdit(w) { editData.value = w; showForm.value = true }

async function onDelete(id) {
  if (!confirm('确定删除？')) return
  try { await deleteWorkout(id); await load() } catch {}
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h2>训练记录</h2>
      <button class="btn-primary" @click="editData = null; showForm = true">+ 新增训练</button>
    </div>

    <div v-if="workouts.length === 0" class="empty">还没有训练记录，点击上方开始</div>

    <div v-for="w in workouts" :key="w.id" class="item">
      <div class="item-main">
        <span class="item-date">{{ w.date }}</span>
        <span class="item-part">{{ w.body_part }}</span>
        <span class="item-meta">{{ w.exercise_count }}动作 · {{ w.total_volume }}kg</span>
      </div>
      <div class="item-actions">
        <button class="btn-text" @click="onEdit(w)">编辑</button>
        <button class="btn-text danger" @click="onDelete(w.id)">删除</button>
      </div>
    </div>

    <WorkoutForm v-if="showForm" :initial="editData" @save="onSave" @cancel="showForm = false; editData = null" />
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 640px; margin: 0 auto; height: 100%; overflow-y: auto; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-head h2 { font-size: 1.3rem; font-weight: 700; }
.btn-primary { padding: 8px 18px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.empty { text-align: center; color: var(--text-muted); padding: 40px; }
.item { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; background: var(--white); border-radius: var(--radius-sm); margin-bottom: 8px; box-shadow: var(--shadow-sm); }
.item-main { display: flex; gap: 16px; align-items: center; }
.item-date { font-weight: 600; font-size: 0.9rem; color: var(--text); }
.item-part { background: var(--green-100); color: var(--green-700); padding: 2px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }
.item-meta { font-size: 0.82rem; color: var(--text-muted); }
.item-actions { display: flex; gap: 8px; }
.btn-text { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.82rem; font-family: var(--font-body); }
.btn-text:hover { color: var(--text); }
.btn-text.danger:hover { color: var(--coral); }
</style>
