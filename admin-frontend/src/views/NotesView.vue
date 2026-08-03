<template>
  <AdminLayout>
    <h2 class="page-title">Notes</h2>
    <div class="toolbar">
      <input
        v-model="keyword"
        placeholder="Search notes..."
        @input="onSearch"
        class="search-input"
      />
      <label class="checkbox-label">
        <input type="checkbox" v-model="includeTrash" @change="load" />
        Include trash
      </label>
    </div>
    <table class="data-table">
      <thead>
        <tr>
          <th>Title</th>
          <th>User</th>
          <th>Color</th>
          <th>Status</th>
          <th>Updated</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="note in notes" :key="note.id">
          <td class="title-col" @click="viewNote = note">{{ note.title || '(untitled)' }}</td>
          <td>{{ note.username }}</td>
          <td>
            <span class="color-dot" :style="{ background: colorMap[note.color] || '#999' }"></span>
            {{ note.color }}
          </td>
          <td>
            <span :class="note.deletedAt ? 'tag trash' : 'tag active'">
              {{ note.deletedAt ? 'Trash' : 'Active' }}
            </span>
          </td>
          <td>{{ formatDate(note.updatedAt) }}</td>
          <td>
            <button @click="viewNote = note" class="btn-sm">View</button>
            <button @click="confirmDelete(note)" class="btn-sm btn-danger">Force Delete</button>
          </td>
        </tr>
        <tr v-if="notes.length === 0">
          <td colspan="6" class="empty">No notes found</td>
        </tr>
      </tbody>
    </table>
    <div class="pagination" v-if="totalPages > 1">
      <button :disabled="page <= 1" @click="page--; load()">Prev</button>
      <span>Page {{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="page++; load()">Next</button>
    </div>

    <NoteDetail v-if="viewNote" :note="viewNote" @close="viewNote = null" />

    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = null">
      <div class="modal">
        <h3>Permanently Delete Note</h3>
        <p>This will permanently delete "<strong>{{ showDelete.title }}</strong>" and its backup file.</p>
        <div class="modal-actions">
          <button @click="doDelete" class="btn-danger">Delete</button>
          <button @click="showDelete = null" class="btn-cancel">Cancel</button>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AdminLayout from '../components/AdminLayout.vue'
import NoteDetail from '../components/NoteDetail.vue'
import { getNotes, deleteNote } from '../api'

const route = useRoute()
const notes = ref([])
const keyword = ref('')
const includeTrash = ref(false)
const page = ref(1)
const totalPages = ref(1)
const viewNote = ref(null)
const showDelete = ref(null)
let searchTimer = null

const colorMap = {
  blue: '#4A90D9', green: '#7ED321', yellow: '#F5A623',
  orange: '#F47B20', red: '#E74C3C', gray: '#9B9B9B',
}

function formatDate(d) {
  if (!d) return ''
  return d.replace('T', ' ').substring(0, 19)
}

async function load() {
  const params = {
    page: page.value,
    keyword: keyword.value,
    includeTrash: includeTrash.value,
    size: 20,
  }
  const userId = route.query.userId
  if (userId) params.userId = userId
  const { data } = await getNotes(params)
  if (data.code === 0) {
    notes.value = data.data
    totalPages.value = data.pagination.totalPages
  }
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; load() }, 300)
}

function confirmDelete(note) {
  showDelete.value = note
}

async function doDelete() {
  await deleteNote(showDelete.value.id)
  showDelete.value = null
  load()
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 20px; margin-bottom: 20px; }
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
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
.checkbox-label {
  font-size: 14px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
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
.title-col {
  cursor: pointer;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.title-col:hover { color: #0f3460; }
.color-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}
.tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}
.tag.active { background: #e8f5e9; color: #2e7d32; }
.tag.trash { background: #fce4ec; color: #c62828; }
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
.modal-actions .btn-cancel { background: #eee; color: #333; }
.modal-actions .btn-danger { background: #e74c3c; }
</style>
