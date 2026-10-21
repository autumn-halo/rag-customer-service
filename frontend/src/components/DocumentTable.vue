<script setup>
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useDocumentsStore } from '@/stores/documents'

const store = useDocumentsStore()

// 状态 → 展示样式
const STATUS_MAP = {
  pending: { type: 'info', text: '待处理' },
  processing: { type: 'primary', text: '处理中' },
  success: { type: 'success', text: '已入库' },
  failed: { type: 'danger', text: '失败' },
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatTime(iso) {
  return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleString('zh-CN', { hour12: false })
}

async function onReprocess(row) {
  try {
    await ElMessageBox.confirm(`确定重新解析「${row.filename}」吗？`, '重新解析', {
      type: 'warning',
    })
  } catch {
    return
  }
  await store.reprocess(row.id)
  ElMessage.success('已加入处理队列')
}

async function onRemove(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.filename}」吗？关联的知识片段将一并删除，删除后不可恢复`,
      '删除文档',
      { type: 'error' },
    )
  } catch {
    return
  }
  await store.remove(row.id)
  ElMessage.success('已删除')
}

// ===== 分块预览对话框 =====
const chunkDialog = reactive({ visible: false, docTitle: '', chunks: [], total: 0, page: 1, size: 20, loading: false })

async function openChunks(row) {
  chunkDialog.visible = true
  chunkDialog.docTitle = row.filename
  chunkDialog.page = 1
  await loadChunks(row.id)
}

async function loadChunks(docId) {
  chunkDialog.loading = true
  try {
    const data = await store.loadChunks(docId, chunkDialog.page, chunkDialog.size)
    chunkDialog.chunks = data.items
    chunkDialog.total = data.total
  } finally {
    chunkDialog.loading = false
  }
}
</script>

<template>
  <div>
    <el-table v-loading="store.loading" :data="store.items" stripe>
      <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
      <el-table-column label="类型" width="80">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.file_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column label="分块数" width="90">
        <template #default="{ row }">{{ row.chunk_count || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tooltip
            v-if="row.status === 'failed'"
            :content="row.error_message || '未知错误'"
            placement="top"
          >
            <el-tag size="small" :type="STATUS_MAP[row.status]?.type || 'info'">
              {{ STATUS_MAP[row.status]?.text || row.status }}
            </el-tag>
          </el-tooltip>
          <el-tag v-else size="small" :type="STATUS_MAP[row.status]?.type || 'info'">
            {{ row.status === 'processing' ? '⟳ ' : '' }}{{ STATUS_MAP[row.status]?.text || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上传时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            size="small"
            :disabled="row.status !== 'success'"
            @click="openChunks(row)"
          >
            分块预览
          </el-button>
          <el-button link type="warning" size="small" @click="onReprocess(row)">
            重新解析
          </el-button>
          <el-button link type="danger" size="small" @click="onRemove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row">
      <el-pagination
        v-model:current-page="store.page"
        v-model:page-size="store.size"
        :total="store.total"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        @current-change="store.load()"
        @size-change="store.load()"
      />
    </div>

    <el-dialog v-model="chunkDialog.visible" :title="`分块预览 · ${chunkDialog.docTitle}`" width="720px">
      <el-scrollbar max-height="420px">
        <div v-for="c in chunkDialog.chunks" :key="c.id" class="chunk-item">
          <el-tag size="small" type="info">#{{ c.chunk_index + 1 }}</el-tag>
          <p class="chunk-content">{{ c.content }}</p>
        </div>
      </el-scrollbar>
      <template #footer>
        <el-pagination
          v-model:current-page="chunkDialog.page"
          :total="chunkDialog.total"
          :page-size="chunkDialog.size"
          layout="prev, pager, next"
          small
          @current-change="loadChunks"
        />
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.pagination-row {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.chunk-item {
  padding: 10px 12px;
  margin-bottom: 10px;
  background: #f8f9fa;
  border-radius: 6px;
}

.chunk-content {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
