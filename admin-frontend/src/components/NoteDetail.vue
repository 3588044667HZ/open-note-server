<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>{{ note.title || '(untitled)' }}</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>
      <div class="meta">
        <span>User: <strong>{{ note.username }}</strong></span>
        <span>Version: {{ note.version }}</span>
        <span>Updated: {{ formatDate(note.updatedAt) }}</span>
        <span>Notebook: {{ note.notebookId || '-' }}</span>
      </div>
      <div class="content-body" v-html="rendered"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  note: { type: Object, required: true }
})

defineEmits(['close'])

const rendered = computed(() => {
  return marked(props.note.content || '') || '<p style="color:#999">No content</p>'
})

function formatDate(d) {
  if (!d) return ''
  return d.replace('T', ' ').substring(0, 19)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal-content {
  background: #fff;
  border-radius: 12px;
  width: 720px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
}
.modal-header h3 {
  font-size: 18px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  line-height: 1;
}
.close-btn:hover { color: #333; }
.meta {
  padding: 12px 24px;
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #888;
  border-bottom: 1px solid #f0f0f0;
  flex-wrap: wrap;
}
.content-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
  line-height: 1.7;
  font-size: 15px;
}
.content-body :deep(h1),
.content-body :deep(h2),
.content-body :deep(h3) { margin: 16px 0 8px; }
.content-body :deep(p) { margin: 8px 0; }
.content-body :deep(ul),
.content-body :deep(ol) { padding-left: 20px; }
.content-body :deep(li) { margin: 4px 0; }
.content-body :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}
.content-body :deep(pre) {
  background: #f5f5f5;
  padding: 14px;
  border-radius: 6px;
  overflow-x: auto;
}
.content-body :deep(blockquote) {
  border-left: 3px solid #ddd;
  padding-left: 14px;
  color: #888;
  margin: 12px 0;
}
</style>
