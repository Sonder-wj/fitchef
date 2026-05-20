<script setup>
import { ref, watch } from 'vue'
import { searchFood } from '../services/api.js'

const emit = defineEmits(['select'])

const query = ref('')
const results = ref([])
const loading = ref(false)
const showDropdown = ref(false)

let timer = null
watch(query, (val) => {
  clearTimeout(timer)
  if (!val || val.length < 1) { results.value = []; showDropdown.value = false; return }
  timer = setTimeout(async () => {
    loading.value = true
    try {
      const r = await searchFood(val)
      results.value = r.items || []
      showDropdown.value = results.value.length > 0
    } catch { results.value = [] }
    finally { loading.value = false }
  }, 200)
})

function select(item) {
  emit('select', item)
  query.value = item.food_name
  showDropdown.value = false
}
</script>

<template>
  <div class="food-search">
    <input
      v-model="query"
      placeholder="搜索食物..."
      class="search-input"
      @focus="results.length > 0 && (showDropdown = true)"
    />
    <div v-if="showDropdown" class="dropdown">
      <div v-for="item in results" :key="item.id" class="dropdown-item" @click="select(item)">
        <span class="food-name">{{ item.food_name }}</span>
        <span class="food-meta">{{ item.calories }}kcal / 蛋白{{ item.protein }}g</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.food-search { position: relative; }
.search-input { width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.9rem; font-family: var(--font-body); }
.dropdown { position: absolute; top: 100%; left: 0; right: 0; background: var(--white); border: 1px solid var(--border); border-radius: var(--radius-sm); max-height: 200px; overflow-y: auto; z-index: 50; box-shadow: var(--shadow-md); }
.dropdown-item { padding: 10px 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--cream-dark); }
.dropdown-item:hover { background: var(--cream); }
.food-name { font-weight: 600; font-size: 0.88rem; }
.food-meta { font-size: 0.75rem; color: var(--text-muted); }
</style>
