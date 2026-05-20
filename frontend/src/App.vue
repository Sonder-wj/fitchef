<script setup>
import { ref } from 'vue'
import { isLoggedIn, getSavedUser, logout } from './services/api.js'
import LoginForm from './components/LoginForm.vue'

const user = ref(getSavedUser())
const loggedIn = ref(isLoggedIn())

function onLogin(account) {
  user.value = account
  loggedIn.value = true
}

function onLogout() {
  logout()
  user.value = null
  loggedIn.value = false
}
</script>

<template>
  <div class="app-shell">
    <LoginForm v-if="!loggedIn" @logged-in="onLogin" />
    <template v-else>
      <nav class="app-nav">
        <div class="nav-brand">
          <span class="brand-icon">🥗</span>
          <span class="brand-name">FitChef</span>
        </div>
        <div class="nav-links">
          <router-link to="/chat" class="nav-link">💬 对话</router-link>
          <router-link to="/dashboard" class="nav-link">📊 仪表盘</router-link>
          <router-link to="/workout" class="nav-link">🏋️ 训练</router-link>
          <router-link to="/body" class="nav-link">⚖️ 身体</router-link>
          <router-link to="/diet" class="nav-link">🍽️ 饮食</router-link>
        </div>
        <div class="nav-right">
          <span class="user-tag">{{ user?.email || '' }}</span>
          <button class="logout-btn" @click="onLogout">退出</button>
        </div>
      </nav>
      <div class="app-content">
        <router-view :user="user" @logout="onLogout" />
      </div>
    </template>
  </div>
</template>

<style>
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --green-900: #1A2E23;
  --green-700: #2A4A36;
  --green-500: #3D8B5F;
  --green-300: #6BBF8A;
  --green-100: #D4EDDF;
  --coral: #E8614D;
  --coral-light: #FFE8E4;
  --cream: #FEF9F0;
  --cream-dark: #F5EDE0;
  --white: #FFFFFF;
  --text: #2C241A;
  --text-muted: #8C8075;
  --border: #E8DDD0;
  --shadow-sm: 0 1px 3px rgba(44, 36, 26, 0.06);
  --shadow-md: 0 4px 16px rgba(44, 36, 26, 0.08);
  --shadow-lg: 0 8px 32px rgba(44, 36, 26, 0.12);
  --radius-sm: 8px;
  --radius: 14px;
  --radius-lg: 20px;
  --font-display: 'Amatic SC', cursive;
  --font-body: 'Nunito', sans-serif;
}

body {
  font-family: var(--font-body);
  color: var(--text);
  background: var(--cream);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-shell {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.app-nav {
  display: flex;
  align-items: center;
  height: 52px;
  padding: 0 20px;
  background: var(--green-900);
  gap: 24px;
  flex-shrink: 0;
}
.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}
.nav-brand .brand-icon { font-size: 1.2rem; }
.nav-brand .brand-name {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: #fff;
}
.nav-links { display: flex; gap: 4px; }
.nav-link {
  padding: 8px 14px;
  color: rgba(255,255,255,0.65);
  text-decoration: none;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
}
.nav-link:hover { background: rgba(255,255,255,0.08); color: #fff; }
.nav-link.router-link-active { background: var(--green-500); color: #fff; }
.nav-right { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.nav-right .user-tag { color: rgba(255,255,255,0.5); font-size: 0.82rem; }
.nav-right .logout-btn {
  padding: 5px 14px;
  background: none;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: var(--radius-sm);
  color: rgba(255,255,255,0.6);
  cursor: pointer;
  font-size: 0.82rem;
  font-family: var(--font-body);
  transition: border-color 0.15s, color 0.15s;
}
.nav-right .logout-btn:hover { border-color: var(--coral); color: var(--coral); }
.app-content {
  flex: 1;
  overflow: hidden;
}
</style>
