<template>
  <AdminLayout>
    <h2 class="page-title">Users</h2>
    <div class="toolbar">
      <input
        v-model="keyword"
        placeholder="Search username..."
        @input="search"
        class="search-input"
      />
      <button @click="showCreate = true" class="btn-primary">+ Create User</button>
    </div>
    <table class="data-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Username</th>
          <th>Created</th>
          <th>Notes</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.id }}</td>
          <td>{{ user.username }}</td>
          <td>{{ formatDate(user.createdAt) }}</td>
          <td>{{ user.noteCount }}</td>
          <td class="actions">
            <button @click="viewNotes(user.id)" class="btn-sm">Notes</button>
            <button @click="openReset(user)" class="btn-sm btn-warn">Reset Pwd</button>
            <button @click="confirmDelete(user)" class="btn-sm btn-danger">Delete</button>
          </td>
        </tr>
        <tr v-if="users.length === 0">
          <td colspan="5" class="empty">No users found</td>
        </tr>
      </tbody>
    </table>
    <div class="pagination" v-if="totalPages > 1">
      <button :disabled="page <= 1" @click="page--; load()">Prev</button>
      <span>Page {{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="page++; load()">Next</button>
    </div>

    <div v-if="showReset" class="modal-overlay" @click.self="showReset = null">
      <div class="modal">
        <h3>Reset Password for {{ showReset.username }}</h3>
        <input v-model="newPassword" type="text" placeholder="New password (min 3 chars)" />
        <div class="modal-actions">
          <button @click="doReset" :disabled="newPassword.length < 3">Confirm</button>
          <button @click="showReset = null" class="btn-cancel">Cancel</button>
        </div>
      </div>
    </div>

    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = null">
      <div class="modal">
        <h3>Delete User</h3>
        <p>Are you sure you want to delete <strong>{{ showDelete.username }}</strong> and all their notes?</p>
        <div class="modal-actions">
          <button @click="doDelete" class="btn-danger">Confirm Delete</button>
          <button @click="showDelete = null" class="btn-cancel">Cancel</button>
        </div>
      </div>
    </div>

    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h3>Create User</h3>
        <input v-model="newUsername" type="text" placeholder="Username (min 2 chars)" />
        <input v-model="newUserPassword" type="password" placeholder="Password (min 3 chars)" />
        <p v-if="createError" class="error-msg">{{ createError }}</p>
        <div class="modal-actions">
          <button @click="doCreate" :disabled="newUsername.length < 2 || newUserPassword.length < 3">Create</button>
          <button @click="showCreate = false; createError = ''" class="btn-cancel">Cancel</button>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AdminLayout from '../components/AdminLayout.vue'
import { getUsers, createUser, deleteUser, resetPassword } from '../api'

const router = useRouter()
const users = ref([])
const keyword = ref('')
const page = ref(1)
const totalPages = ref(1)
const showReset = ref(null)
const showDelete = ref(null)
const showCreate = ref(false)
const newUsername = ref('')
const newUserPassword = ref('')
const createError = ref('')
const newPassword = ref('')
let searchTimer = null

function formatDate(d) {
  if (!d) return ''
  return d.replace('T', ' ').substring(0, 19)
}

async function load() {
  const { data } = await getUsers({ page: page.value, keyword: keyword.value, size: 20 })
  if (data.code === 0) {
    users.value = data.data
    totalPages.value = data.pagination.totalPages
  }
}

function search() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; load() }, 300)
}

function viewNotes(userId) {
  router.push({ path: '/notes', query: { userId } })
}

function openReset(user) {
  showReset.value = user
  newPassword.value = ''
}

async function doReset() {
  await resetPassword(showReset.value.id, newPassword.value)
  showReset.value = null
  alert('Password updated')
}

function confirmDelete(user) {
  showDelete.value = user
}

async function doDelete() {
  await deleteUser(showDelete.value.id)
  showDelete.value = null
  load()
}

async function doCreate() {
  createError.value = ''
  try {
    const { data } = await createUser(newUsername.value.trim(), newUserPassword.value)
    if (data.code === 0) {
      showCreate.value = false
      newUsername.value = ''
      newUserPassword.value = ''
      load()
    } else {
      createError.value = data.msg
    }
  } catch {
    createError.value = 'Network error'
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 20px; margin-bottom: 20px; }
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.search-input {
  padding: 8px 14px;
  border: 1px solid #ddd;
  border-radius: 6px;
  width: 260px;
  font-size: 14px;
  outline: none;
}
.search-input:focus { border-color: #0f3460; }
.data-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.data-table th, .data-table td {
  padding: 12px 16px;
  text-align: left;
  font-size: 14px;
}
.data-table th {
  background: #fafafa;
  font-weight: 600;
  color: #555;
  border-bottom: 1px solid #eee;
}
.data-table td {
  border-bottom: 1px solid #f0f0f0;
}
.actions { white-space: nowrap; }
.btn-sm {
  padding: 4px 12px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  margin-right: 6px;
}
.btn-sm:hover { background: #f5f5f5; }
.btn-primary {
  padding: 8px 16px;
  background: #0f3460;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.btn-primary:hover { background: #1a5276; }
.btn-warn { color: #f39c12; border-color: #f39c12; }
.btn-danger { color: #e74c3c; border-color: #e74c3c; }
.empty { text-align: center; color: #999; padding: 24px; }
.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  font-size: 14px;
  color: #666;
}
.pagination button {
  padding: 6px 14px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
}
.pagination button:disabled { opacity: 0.4; cursor: default; }
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  background: #fff;
  padding: 28px;
  border-radius: 10px;
  width: 400px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}
.modal h3 { margin-bottom: 16px; }
.modal p { margin-bottom: 20px; font-size: 14px; color: #666; }
.modal input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  margin-bottom: 16px;
}
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; }
.modal-actions button {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  background: #0f3460;
  color: #fff;
}
.modal-actions button:disabled { opacity: 0.4; }
.modal-actions .btn-cancel { background: #eee; color: #333; }
.modal-actions .btn-danger { background: #e74c3c; }
.error-msg { color: #e74c3c; font-size: 14px; margin-bottom: 12px; }
</style>
