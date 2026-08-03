import axios from 'axios'

const api = axios.create({
  baseURL: '/api/admin',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('admin_token')
      window.location.hash = '#/'
    }
    return Promise.reject(err)
  }
)

export function loginAdmin(password) {
  return api.post('/login', { password })
}

export function getStats() {
  return api.get('/stats')
}

export function getUsers(params) {
  return api.get('/users', { params })
}

export function createUser(username, password) {
  return api.post('/users', { username, password })
}

export function deleteUser(id) {
  return api.delete(`/users/${id}`)
}

export function resetPassword(id, password) {
  return api.put(`/users/${id}/password`, { password })
}

export function getNotes(params) {
  return api.get('/notes', { params })
}

export function deleteNote(id) {
  return api.delete(`/notes/${id}`)
}

export default api
