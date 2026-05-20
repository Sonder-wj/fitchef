<script setup>
import { ref, onMounted } from 'vue'
import { getExerciseNames } from '../services/api.js'

const props = defineProps({ initial: Object })
const emit = defineEmits(['save', 'cancel'])

const historyExercises = ref([])
onMounted(async () => {
  try { const r = await getExerciseNames(); historyExercises.value = r.exercises || []; } catch {}
})

const bodyParts = ['胸', '背', '腿', '肩', '臂', '全身']

const form = ref({
  date: props.initial?.date || new Date().toISOString().slice(0, 10),
  body_part: props.initial?.body_part || '',
  duration_min: props.initial?.duration_min || null,
  notes: props.initial?.notes || '',
  exercises: props.initial?.exercises || [],
})

function addExercise() {
  form.value.exercises.push({ exercise_name: '', sort_order: form.value.exercises.length, sets: [{ set_number: 1, weight_kg: 0, reps: 0 }] })
}

function removeExercise(idx) { form.value.exercises.splice(idx, 1) }

function addSet(exIdx) {
  const sets = form.value.exercises[exIdx].sets
  sets.push({ set_number: sets.length + 1, weight_kg: sets[sets.length - 1]?.weight_kg || 0, reps: sets[sets.length - 1]?.reps || 0 })
}

function removeSet(exIdx, setIdx) { form.value.exercises[exIdx].sets.splice(setIdx, 1) }

function onSave() { emit('save', { ...form.value }) }
</script>

<template>
  <div class="form-overlay" @click.self="emit('cancel')">
    <div class="form-panel">
      <h3>{{ props.initial ? '编辑训练' : '记录训练' }}</h3>

      <div class="field-row">
        <label>日期 <input type="date" v-model="form.date" /></label>
        <label>部位
          <select v-model="form.body_part">
            <option value="">选择</option>
            <option v-for="bp in bodyParts" :key="bp" :value="bp">{{ bp }}</option>
          </select>
        </label>
      </div>
      <div class="field-row">
        <label>时长(分) <input type="number" v-model="form.duration_min" min="0" /></label>
      </div>

      <div class="exercises-section">
        <div v-for="(ex, exIdx) in form.exercises" :key="exIdx" class="exercise-block">
          <div class="ex-header">
            <input
              v-model="ex.exercise_name"
              placeholder="动作名"
              list="exercise-list"
              class="ex-name-input"
            />
            <datalist id="exercise-list">
              <option v-for="name in historyExercises" :key="name" :value="name" />
            </datalist>
            <button class="btn-sm btn-del" @click="removeExercise(exIdx)">×</button>
          </div>
          <div v-for="(set, setIdx) in ex.sets" :key="setIdx" class="set-row">
            <span class="set-num">{{ setIdx + 1 }}</span>
            <input type="number" v-model="set.weight_kg" placeholder="重量kg" step="0.5" min="0" class="set-input" />
            <input type="number" v-model="set.reps" placeholder="次数" min="0" class="set-input" />
            <button v-if="ex.sets.length > 1" class="btn-sm btn-del" @click="removeSet(exIdx, setIdx)">×</button>
          </div>
          <button class="btn-sm btn-add" @click="addSet(exIdx)">+ 组</button>
        </div>
      </div>

      <button class="btn-add-ex" @click="addExercise">+ 动作</button>

      <label class="notes-label">备注 <textarea v-model="form.notes" rows="2" placeholder="训练感受..." /></label>

      <div class="form-actions">
        <button class="btn-save" @click="onSave">保存</button>
        <button class="btn-cancel" @click="emit('cancel')">取消</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.form-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 100; display: flex; align-items: flex-start; justify-content: center; padding-top: 40px; }
.form-panel { background: var(--white); border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 520px; max-height: 80vh; overflow-y: auto; box-shadow: var(--shadow-lg); }
.form-panel h3 { margin-bottom: 16px; font-size: 1.1rem; }
.field-row { display: flex; gap: 12px; margin-bottom: 10px; }
.field-row label { flex: 1; font-size: 0.82rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; }
.field-row input, .field-row select { padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.88rem; font-family: var(--font-body); }
.exercise-block { background: var(--cream); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 10px; }
.ex-header { display: flex; gap: 8px; margin-bottom: 8px; }
.ex-name-input { flex: 1; padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.88rem; font-family: var(--font-body); }
.set-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.set-num { width: 20px; text-align: center; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; }
.set-input { width: 80px; padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.85rem; font-family: var(--font-body); }
.btn-sm { padding: 2px 8px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-family: var(--font-body); }
.btn-del { background: none; color: var(--coral); font-size: 1.1rem; }
.btn-add { background: none; color: var(--green-500); font-weight: 600; margin-top: 4px; }
.btn-add-ex { width: 100%; padding: 8px; background: none; border: 1px dashed var(--border); border-radius: var(--radius-sm); color: var(--text-muted); cursor: pointer; font-family: var(--font-body); font-size: 0.85rem; margin-bottom: 10px; }
.btn-add-ex:hover { border-color: var(--green-500); color: var(--green-500); }
.notes-label { font-size: 0.82rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; margin-bottom: 16px; }
.notes-label textarea { padding: 8px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-family: var(--font-body); resize: vertical; }
.form-actions { display: flex; gap: 10px; justify-content: flex-end; }
.btn-save { padding: 8px 24px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.btn-cancel { padding: 8px 16px; background: none; border: 1px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-body); }
</style>
