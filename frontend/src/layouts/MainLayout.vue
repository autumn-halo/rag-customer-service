<script setup>
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

function handleCommand(cmd) {
  if (cmd === 'profile') router.push({ name: 'profile' })
  if (cmd === 'knowledge') router.push({ name: 'knowledge' })
  if (cmd === 'logout') {
    auth.logout()
    router.push({ name: 'login' })
  }
}
</script>

<template>
  <el-container class="layout">
    <el-header class="layout-header" height="56px">
      <div class="brand">🛒 RAG 电商知识库问答</div>
      <el-dropdown @command="handleCommand">
        <span class="user-chip">
          <el-avatar :size="28">{{ auth.user?.username?.[0]?.toUpperCase() }}</el-avatar>
          <span class="user-name">{{ auth.user?.username }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-if="auth.isAdmin" command="knowledge">
              知识库管理
            </el-dropdown-item>
            <el-dropdown-item command="profile">个人中心</el-dropdown-item>
            <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-header>
    <el-container class="layout-body">
      <el-aside width="260px" class="layout-aside">
        <!-- 会话列表：阶段 3 实现 -->
        <div class="aside-placeholder">💬 会话列表（开发中）</div>
      </el-aside>
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100%;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-light);
  background: #fff;
}

.brand {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #303133;
  outline: none;
}

.user-name {
  font-size: 14px;
}

.layout-body {
  height: calc(100% - 56px);
}

.layout-aside {
  border-right: 1px solid var(--el-border-color-light);
  background: #fafafa;
  display: flex;
  flex-direction: column;
}

.aside-placeholder {
  padding: 16px;
  color: #909399;
  font-size: 13px;
}

.layout-main {
  padding: 0;
  background: #fff;
}
</style>
