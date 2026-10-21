<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

import DocumentTable from '@/components/DocumentTable.vue'
import { useDocumentsStore } from '@/stores/documents'

const store = useDocumentsStore()

onMounted(() => store.load())
onBeforeUnmount(() => store.stopPolling())

const ACCEPT = '.pdf,.docx,.xlsx,.txt,.md'

// ElUpload 自定义上传：走统一请求客户端（自动带令牌）
function customUpload({ file, onSuccess, onError }) {
  store
    .upload(file)
    .then(() => {
      onSuccess()
      ElMessage.success(`「${file.name}」已上传，后台解析中`)
    })
    .catch((e) => onError(e))
}
</script>

<template>
  <div class="kb-page">
    <div class="kb-header">
      <h3 class="kb-title">知识库管理</h3>
      <el-upload
        :accept="ACCEPT"
        multiple
        :show-file-list="false"
        :http-request="customUpload"
      >
        <el-button type="primary">
          <el-icon style="margin-right: 4px"><Upload /></el-icon>
          上传文档
        </el-button>
        <template #tip>
          <div class="upload-tip">
            支持 PDF / Word / Excel / TXT / Markdown，单文件 ≤ 20MB，可多选
          </div>
        </template>
      </el-upload>
    </div>

    <el-card shadow="never">
      <div class="filter-row">
        <el-radio-group v-model="store.statusFilter" size="small" @change="store.load()">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="success">已入库</el-radio-button>
          <el-radio-button label="processing">处理中</el-radio-button>
          <el-radio-button label="failed">失败</el-radio-button>
        </el-radio-group>
      </div>
      <DocumentTable />
    </el-card>
  </div>
</template>

<style scoped>
.kb-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100%;
}

.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.kb-title {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

.filter-row {
  margin-bottom: 14px;
}
</style>
