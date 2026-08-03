<template>
  <div class="login-wrapper">
    <form class="login-card" @submit.prevent="handleLogin">
      <h1>Open Note</h1>
      <p class="subtitle">Admin Panel</p>
      <input
        v-model="password"
        type="password"
        placeholder="Admin Password"
        autofocus
      />
      <button type="submit" :disabled="loading">
        {{ loading ? 'Logging in...' : 'Login' }}
      </button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminStore } from '../stores/admin'

const router = useRouter()
const adminStore = useAdminStore()
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  if (!password.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const ok = await adminStore.login(password.value.trim())
    if (ok) {
      router.push('/dashboard')
    } else {
      error.value = 'Invalid password'
    }
  } catch {
    error.value = 'Network error'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.login-card {
  background: #fff;
  padding: 48px 40px;
  border-radius: 12px;
  width: 360px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  text-align: center;
}
.login-card h1 {
  font-size: 28px;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.subtitle {
  color: #888;
  font-size: 14px;
  margin-bottom: 32px;
}
input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 15px;
  outline: none;
  transition: border-color .2s;
}
input:focus {
  border-color: #0f3460;
}
button {
  width: 100%;
  margin-top: 16px;
  padding: 12px;
  background: #0f3460;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: background .2s;
}
button:hover { background: #1a5276; }
button:disabled { opacity: 0.6; cursor: default; }
.error {
  color: #e74c3c;
  font-size: 14px;
  margin-top: 16px;
}
</style>
