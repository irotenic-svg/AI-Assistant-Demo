<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <el-button type="primary" @click="$emit('new-chat')" :icon="Plus" size="small">
        新对话
      </el-button>
    </div>

    <div class="sidebar-title">对话历史</div>

    <el-menu
      :default-active="activeSession"
      @select="(id) => $emit('select-session', id)"
      class="sidebar-menu"
    >
      <el-menu-item
        v-for="session in sessions"
        :key="session.id"
        :index="session.id"
      >
        <el-icon><ChatDotRound /></el-icon>
        <span>{{ session.title }}</span>
      </el-menu-item>
    </el-menu>

    <div v-if="sessions.length === 0" class="sidebar-empty">
      暂无对话历史
    </div>
  </div>
</template>

<script setup>
import { Plus, ChatDotRound } from '@element-plus/icons-vue'

defineProps({
  sessions: { type: Array, default: () => [] },
  activeSession: { type: String, default: '' },
})

defineEmits(['new-chat', 'select-session'])
</script>

<style scoped>
.sidebar {
  width: 260px;
  height: 100%;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
}

.sidebar-title {
  padding: 8px 16px;
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.sidebar-menu {
  background: transparent !important;
  border-right: none !important;
}

.sidebar-menu :deep(.el-menu-item) {
  color: var(--text-secondary) !important;
  font-size: 13px;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--bg-elevated) !important;
  color: var(--accent) !important;
}

.sidebar-empty {
  padding: 24px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
}
</style>
