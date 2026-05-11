<script setup>
import { ref } from 'vue'
import { login, register } from '../services/api.js'

const emit = defineEmits(['logged-in'])

const isRegister = ref(false)
const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  if (!email.value || !password.value) {
    error.value = '请填写邮箱和密码'
    return
  }
  if (isRegister.value && !name.value) {
    error.value = '请填写用户名'
    return
  }

  loading.value = true
  try {
    if (isRegister.value) {
      await register(name.value, email.value, password.value)
    } else {
      await login(email.value, password.value)
    }
    emit('logged-in', { email: email.value, name: name.value || email.value })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <!-- Decorative elements -->
    <div class="bg-leaves">
      <span class="leaf leaf-1">🥬</span>
      <span class="leaf leaf-2">🥕</span>
      <span class="leaf leaf-3">🍳</span>
      <span class="leaf leaf-4">🥑</span>
      <span class="leaf leaf-5">🍅</span>
      <span class="leaf leaf-6">🥦</span>
    </div>

    <div class="login-card">
      <div class="logo-area">
        <div class="logo-icon">🥗</div>
        <h1 class="logo-text">FitChef</h1>
        <p class="logo-sub">你的私人健身营养助手</p>
      </div>

      <form class="form" @submit.prevent="submit">
        <div v-if="isRegister" class="field">
          <label>用户名</label>
          <input v-model="name" type="text" placeholder="怎么称呼你？" autocomplete="username" />
        </div>

        <div class="field">
          <label>邮箱</label>
          <input v-model="email" type="email" placeholder="your@email.com" autocomplete="email" />
        </div>

        <div class="field">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="••••••" autocomplete="current-password" />
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" class="btn-primary" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>{{ isRegister ? '注册' : '登录' }}</span>
        </button>
      </form>

      <p class="switch-mode">
        {{ isRegister ? '已有账号？' : '还没账号？' }}
        <a href="#" @click.prevent="isRegister = !isRegister; error = ''">
          {{ isRegister ? '去登录' : '注册一个' }}
        </a>
      </p>
    </div>

    <p class="footer-tip">💪 每天一个营养小知识，吃出好身材</p>
  </div>
</template>

<style scoped>
.login-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #FEF9F0 0%, #F0F7F0 40%, #FFF5F2 100%);
  position: relative;
  overflow: hidden;
}

.bg-leaves {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.15;
}

.leaf {
  position: absolute;
  font-size: 4rem;
  animation: float 12s ease-in-out infinite;
}
.leaf-1 { top: 8%; left: 10%; animation-delay: 0s; font-size: 5rem; }
.leaf-2 { top: 5%; right: 15%; animation-delay: 2s; font-size: 3.5rem; }
.leaf-3 { top: 40%; left: 5%; animation-delay: 4s; font-size: 4.5rem; }
.leaf-4 { bottom: 15%; right: 8%; animation-delay: 1s; font-size: 6rem; }
.leaf-5 { bottom: 25%; left: 12%; animation-delay: 3s; font-size: 3rem; }
.leaf-6 { top: 30%; right: 5%; animation-delay: 5s; font-size: 4rem; }

@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-20px) rotate(3deg); }
  66% { transform: translateY(10px) rotate(-2deg); }
}

.login-card {
  position: relative;
  z-index: 1;
  background: var(--white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 48px 40px 36px;
  width: 400px;
  max-width: 90vw;
}

.logo-area {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  font-size: 3rem;
  margin-bottom: 4px;
}

.logo-text {
  font-family: var(--font-display);
  font-size: 3rem;
  font-weight: 700;
  color: var(--green-700);
  line-height: 1;
  letter-spacing: 1px;
}

.logo-sub {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 0.9rem;
  font-weight: 400;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.field input {
  padding: 12px 16px;
  border: 2px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  font-family: var(--font-body);
  color: var(--text);
  background: var(--cream);
  transition: border-color 0.2s, box-shadow 0.2s;
  outline: none;
}

.field input:focus {
  border-color: var(--green-500);
  box-shadow: 0 0 0 3px var(--green-100);
  background: var(--white);
}

.field input::placeholder {
  color: var(--text-muted);
  opacity: 0.6;
}

.error-msg {
  background: var(--coral-light);
  color: var(--coral);
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
}

.btn-primary {
  padding: 14px;
  background: var(--green-500);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 1rem;
  font-weight: 600;
  font-family: var(--font-body);
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
  margin-top: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
}

.btn-primary:hover:not(:disabled) {
  background: var(--green-700);
  transform: translateY(-1px);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2.5px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.switch-mode {
  text-align: center;
  margin-top: 24px;
  font-size: 0.88rem;
  color: var(--text-muted);
}

.switch-mode a {
  color: var(--green-500);
  text-decoration: none;
  font-weight: 600;
}

.switch-mode a:hover {
  color: var(--green-700);
}

.footer-tip {
  position: absolute;
  bottom: 24px;
  font-size: 0.85rem;
  color: var(--text-muted);
  opacity: 0.7;
}
</style>
