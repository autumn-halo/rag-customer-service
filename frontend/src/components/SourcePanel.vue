<script setup>
// 引用来源面板：展示当前回答引用的知识库片段（阶段 5 接入检索后会有真实数据）
defineProps({
  citations: { type: Array, default: () => [] },
})
</script>

<template>
  <div class="source-panel">
    <div class="panel-title">📎 引用来源</div>
    <el-scrollbar class="panel-scroll">
      <template v-if="citations.length">
        <div v-for="c in citations" :key="c.index" class="source-item">
          <div class="source-head">
            <el-tag size="small" type="primary">[{{ c.index }}]</el-tag>
            <span class="source-doc">{{ c.document_title }}</span>
          </div>
          <div class="source-content">{{ c.content }}</div>
          <div class="source-score">相关度：{{ (c.score * 100).toFixed(0) }}%</div>
        </div>
      </template>
      <el-empty
        v-else
        description="本次回答未引用知识库资料"
        :image-size="70"
      />
    </el-scrollbar>
  </div>
</template>

<style scoped>
.source-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--el-border-color-light);
  background: #fafafa;
}

.panel-title {
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid var(--el-border-color-light);
}

.panel-scroll {
  flex: 1;
}

.source-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.source-doc {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.source-content {
  font-size: 12.5px;
  line-height: 1.6;
  color: #606266;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.source-score {
  margin-top: 6px;
  font-size: 12px;
  color: #a8abb2;
}
</style>
