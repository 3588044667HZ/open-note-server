<template>
  <AdminLayout>
    <h2 class="page-title">Dashboard</h2>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-number">{{ stats.userCount }}</div>
        <div class="stat-label">Total Users</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.noteCount }}</div>
        <div class="stat-label">Active Notes</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.trashCount }}</div>
        <div class="stat-label">Trash Notes</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ formatSize(stats.totalContentSize) }}</div>
        <div class="stat-label">Total Content</div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AdminLayout from '../components/AdminLayout.vue'
import { getStats } from '../api'

const stats = ref({
  userCount: 0,
  noteCount: 0,
  trashCount: 0,
  totalContentSize: 0,
})

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

onMounted(async () => {
  const { data } = await getStats()
  if (data.code === 0) stats.value = data.data
})
</script>

<style scoped>
.page-title { font-size: 20px; margin-bottom: 24px; }
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}
.stat-card {
  background: #fff;
  padding: 28px 24px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.stat-number {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
}
.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 6px;
}
</style>
