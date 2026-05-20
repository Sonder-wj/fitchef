<script setup>
import { ref, computed } from 'vue'
import FoodSearch from './FoodSearch.vue'

const props = defineProps({ initial: Object })
const emit = defineEmits(['save', 'cancel'])

const mealTypes = [
  { value: 'breakfast', label: '早餐' },
  { value: 'lunch', label: '午餐' },
  { value: 'dinner', label: '晚餐' },
  { value: 'snack', label: '加餐' },
]

const form = ref({
  date: props.initial?.date || new Date().toISOString().slice(0, 10),
  meal_type: props.initial?.meal_type || 'lunch',
  items: props.initial?.items || [],
})

function addItem() {
  form.value.items.push({ food_name: '', amount_g: 100, calories: 0, protein_g: 0, fat_g: 0, carbs_g: 0 })
}

function onFoodSelect(foodItem, idx) {
  const fi = form.value.items[idx]
  fi.food_name = foodItem.food_name
  const ratio = fi.amount_g / 100
  fi.calories = Math.round((foodItem.calories || 0) * ratio)
  fi.protein_g = Math.round((foodItem.protein || 0) * ratio * 10) / 10
  fi.fat_g = Math.round((foodItem.fat || 0) * ratio * 10) / 10
  fi.carbs_g = Math.round((foodItem.carbs || 0) * ratio)
}

function recalc(idx) {
  // amount_g changed — recalc is handled by user re-entering food or they accept current values
  // For the plan MVP, keep the calculated values from food selection
}

function removeItem(idx) { form.value.items.splice(idx, 1) }

const totalCalories = computed(() => form.value.items.reduce((s, i) => s + (i.calories || 0), 0))
const totalProtein = computed(() => form.value.items.reduce((s, i) => s + (i.protein_g || 0), 0))

function onSave() { emit('save', { ...form.value }) }
</script>

<template>
  <div class="form-overlay" @click.self="emit('cancel')">
    <div class="form-panel">
      <h3>{{ props.initial ? '编辑' : '记录' }}饮食</h3>

      <div class="field-row">
        <label>日期 <input type="date" v-model="form.date" /></label>
        <label>餐次
          <select v-model="form.meal_type">
            <option v-for="mt in mealTypes" :key="mt.value" :value="mt.value">{{ mt.label }}</option>
          </select>
        </label>
      </div>

      <div class="items-section">
        <div v-for="(item, idx) in form.items" :key="idx" class="item-block">
          <div class="item-head">
            <span class="item-num">{{ idx + 1 }}</span>
            <FoodSearch @select="(f) => onFoodSelect(f, idx)" />
            <button class="btn-sm btn-del" @click="removeItem(idx)">&times;</button>
          </div>
          <div class="item-detail">
            <input type="number" v-model="item.amount_g" placeholder="克" min="0" class="amount-input" @change="recalc(idx)" />
            <span class="nutrition-preview" v-if="item.food_name">
              {{ item.calories }}kcal | P{{ item.protein_g }} F{{ item.fat_g }} C{{ item.carbs_g }}
            </span>
          </div>
        </div>
      </div>

      <button class="btn-add" @click="addItem">+ 食物</button>

      <div class="total-bar">
        <span>合计: {{ totalCalories }}kcal / 蛋白质 {{ totalProtein }}g</span>
      </div>

      <div class="form-actions">
        <button class="btn-save" @click="onSave">保存</button>
        <button class="btn-cancel" @click="emit('cancel')">取消</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.form-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 100; display: flex; align-items: flex-start; justify-content: center; padding-top: 40px; }
.form-panel { background: var(--white); border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 480px; max-height: 80vh; overflow-y: auto; box-shadow: var(--shadow-lg); }
.form-panel h3 { margin-bottom: 16px; font-size: 1.1rem; }
.field-row { display: flex; gap: 12px; margin-bottom: 12px; }
.field-row label { flex: 1; font-size: 0.82rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; }
.field-row input, .field-row select { padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.88rem; font-family: var(--font-body); }
.items-section { display: flex; flex-direction: column; gap: 10px; margin-bottom: 10px; }
.item-block { background: var(--cream); border-radius: var(--radius-sm); padding: 10px; }
.item-head { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.item-num { width: 20px; font-weight: 600; font-size: 0.82rem; color: var(--text-muted); text-align: center; }
.item-detail { display: flex; gap: 8px; align-items: center; }
.amount-input { width: 70px; padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.85rem; font-family: var(--font-body); }
.nutrition-preview { font-size: 0.75rem; color: var(--green-700); font-weight: 500; }
.btn-sm { padding: 2px 8px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-family: var(--font-body); }
.btn-del { background: none; color: var(--coral); font-size: 1.1rem; }
.btn-add { width: 100%; padding: 8px; background: none; border: 1px dashed var(--border); border-radius: var(--radius-sm); color: var(--text-muted); cursor: pointer; font-family: var(--font-body); font-size: 0.85rem; margin-bottom: 10px; }
.total-bar { padding: 10px; background: var(--green-100); border-radius: var(--radius-sm); text-align: center; font-weight: 600; font-size: 0.9rem; color: var(--green-700); margin-bottom: 16px; }
.form-actions { display: flex; gap: 10px; justify-content: flex-end; }
.btn-save { padding: 8px 24px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.btn-cancel { padding: 8px 16px; background: none; border: 1px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-body); }
</style>
