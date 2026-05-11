<script setup>
import { ref, computed } from 'vue'
import { isLoggedIn, getSavedUser, logout } from './services/api.js'
import LoginForm from './components/LoginForm.vue'
import ChatLayout from './components/ChatLayout.vue'

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
    <ChatLayout v-else :user="user" @logout="onLogout" />
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
}
</style>
