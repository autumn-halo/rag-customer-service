<script setup>
// 引用折叠列表：回答末尾展示引用条目，点击展开原文详情
defineProps({
  citations: { type: Array, default: () => [] },
  activeNames: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:activeNames'])

function onChange(names) {
  emit('update:activeNames', names)
}
</script>

<template>
  <div v-if="citations.length" class="citation-list">
    <el-collapse :model-value="activeNames" class="cite-collapse" @change="onChange">
      <el-collapse-item
        v-for="c in citations"
        :key="c.index"
        :name="String(c.index)"
        class="cite-item"
      >
        <template #title>
          <span class="cite-title">[{{ c.index }}] {{ c.document_title }}</span>
          <el-tag size="small" type="info" class="cite-score">
            相关度 {{ Math.round(c.score * 100) }}%
          </el-tag>
        </template>
        <p class="cite-content">{{ c.content }}</p>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<style scoped>
.citation-list {
  margin-top: 8px;
  max-width: 100%;
}

.cite-collapse {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: #fff;
}

.cite-item :deep(.el-collapse-item__header) {
  height: auto;
  min-height: 36px;
  padding: 6px 12px;
  font-size: 13px;
  line-height: 1.5;
}

.cite-title {
  color: #303133;
  margin-right: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cite-score {
  flex-shrink: 0;
}

.cite-item :deep(.el-collapse-item__content) {
  padding: 0 12px 10px;
}

.cite-content {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-word;
  border-left: 3px solid var(--el-color-primary-light-7);
  padding-left: 10px;
}
</style>
