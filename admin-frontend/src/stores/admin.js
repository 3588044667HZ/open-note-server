import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { loginAdmin } from '../api'

export const useAdminStore = defineStore('admin', () => {
  const token = ref(localStorage.getItem('admin_token') || '')

  const isLoggedIn = computed(() => !!token.value)

  async function login(password) {
    const { data } = await loginAdmin(password)
    if (data.code === 0) {
      token.value = data.data.token
      localStorage.setItem('admin_token', data.data.token)
      return true
    }
    return false
  }

  function logout() {
    token.value = ''
    localStorage.removeItem('admin_token')
  }

  return { token, isLoggedIn, login, logout }
})
