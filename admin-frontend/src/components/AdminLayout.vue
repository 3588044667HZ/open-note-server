<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">Open Note Admin</div>
      <nav>
        <router-link to="/dashboard" class="nav-item">Dashboard</router-link>
        <router-link to="/users" class="nav-item">Users</router-link>
        <router-link to="/notes" class="nav-item">Notes</router-link>
      </nav>
    </aside>
    <div class="main-area">
      <header class="topbar">
        <span class="topbar-title">Admin Panel</span>
        <button class="logout-btn" @click="handleLogout">Logout</button>
      </header>
      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAdminStore } from '../stores/admin'

const router = useRouter()
const adminStore = useAdminStore()

function handleLogout() {
  adminStore.logout()
  router.push('/')
}
</script>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
}
.sidebar {
  width: 220px;
  background: #1a1a2e;
  color: #fff;
  flex-shrink: 0;
}
.brand {
  padding: 24px 20px;
  font-size: 17px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
nav {
  padding: 12px 0;
}
.nav-item {
  display: block;
  padding: 10px 20px;
  color: rgba(255,255,255,0.7);
  text-decoration: none;
  font-size: 14px;
  transition: all .2s;
}
.nav-item:hover,
.nav-item.router-link-active {
  color: #fff;
  background: rgba(255,255,255,0.1);
}
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
}
.topbar-title {
  font-size: 15px;
  color: #666;
}
.logout-btn {
  padding: 6px 16px;
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #666;
}
.logout-btn:hover {
  border-color: #e74c3c;
  color: #e74c3c;
}
.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
</style>
