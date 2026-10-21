<script setup>
import { ElMessageBox } from 'element-plus'

defineProps({
  conversations: { type: Array, required: true },
  currentId: { type: [Number, null], default: null },
})

const emit = defineEmits(['select', 'create', 'rename', 'remove'])

async function onRename(conv) {
  try {
    const { value } = await ElMessageBox.prompt('输入新的会话名称', '重命名会话', {
      inputValue: conv.title,
      inputValidator: (v) => (v && v.trim() ? true : '名称不能为空'),
    })
    emit('rename', conv.id, value.trim())
  } catch {
    /* 用户取消 */
  }
}

async function onRemove(conv) {
  try {
    await ElMessageBox.confirm(
      `确定删除会话「${conv.title}」吗？删除后不可恢复`,
      '删除会话',
      { type: 'warning' },
    )
    emit('remove', conv.id)
  } catch {
    /* 用户取消 */
  }
}

// 把后端时间格式化成"刚刚 / n 分钟前 / HH:mm / M月d日"
function formatTime(iso) {
  const d = new Date(iso.endsWith('Z') ? iso : `${iso}Z`)
  const now = new Date()
  const diff = now - d
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 3600 * 1000) return `${Math.floor(diff / 60000)} 分钟前`
  if (d.toDateString() === now.toDateString()) return d.toTimeString().slice(0, 5)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}
</script>

<template>
  <div class="conv-list">
    <el-button type="primary" class="new-btn" @click="emit('create')">
      <el-icon><Plus /></el-icon>
      新建对话
    </el-button>
    <el-scrollbar class="conv-scroll">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="conv-item"
        :class="{ active: conv.id === currentId }"
        @click="emit('select', conv.id)"
      >
        <div class="conv-title">{{ conv.title }}</div>
        <div class="conv-meta">
          <span class="conv-time">{{ formatTime(conv.updated_at) }}</span>
          <span class="conv-actions">
            <el-icon @click.stop="onRename(conv)"><Edit /></el-icon>
            <el-icon @click.stop="onRemove(conv)"><Delete /></el-icon>
          </span>
        </div>
      </div>
      <el-empty
        v-if="!conversations.length"
        description="还没有会话"
        :image-size="60"
      />
    </el-scrollbar>
  </div>
</template>

<style scoped>
.conv-list {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.new-btn {
  margin: 12px;
}

.conv-scroll {
  flex: 1;
}

.conv-item {
  padding: 10px 14px;
  margin: 0 8px 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.conv-item:hover {
  background: #f0f2f5;
}

.conv-item.active {
  background: #e8f3ff;
}

.conv-title {
  font-size: 14px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.conv-time {
  font-size: 12px;
  color: #a8abb2;
}

.conv-actions {
  display: none;
  gap: 8px;
  color: #909399;
}

.conv-item:hover .conv-actions {
  display: inline-flex;
}

.conv-actions .el-icon:hover {
  color: #409eff;
}
</style>
