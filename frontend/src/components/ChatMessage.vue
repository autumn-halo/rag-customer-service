<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

// html: false 防止回答中的 HTML 被注入执行（XSS 防护）
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const props = defineProps({
  message: { type: Object, required: true },
})

const isUser = computed(() => props.message.role === 'user')
const rendered = computed(() => md.render(props.message.content || ''))
</script>

<template>
  <div class="msg-row" :class="isUser ? 'is-user' : 'is-assistant'">
    <el-avatar :size="32" class="msg-avatar" :class="isUser ? 'avatar-user' : 'avatar-ai'">
      {{ isUser ? '我' : 'AI' }}
    </el-avatar>
    <div class="msg-body">
      <div v-if="isUser" class="msg-bubble user-bubble">{{ message.content }}</div>
      <div v-else class="msg-bubble assistant-bubble markdown-body" v-html="rendered"></div>
      <div v-if="!isUser" class="msg-meta">
        <span v-if="message.interrupted" class="interrupted">已停止生成</span>
        <span v-if="message.token_count" class="tokens">{{ message.token_count }} tokens</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.msg-row.is-user {
  flex-direction: row-reverse;
}

.msg-avatar {
  flex-shrink: 0;
  font-size: 13px;
}

.avatar-user {
  background: #409eff;
  color: #fff;
}

.avatar-ai {
  background: #e8f3ff;
  color: #409eff;
  font-weight: 600;
}

.msg-body {
  max-width: 76%;
  display: flex;
  flex-direction: column;
}

.is-user .msg-body {
  align-items: flex-end;
}

.msg-bubble {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
  white-space: pre-wrap;
}

.user-bubble {
  background: #409eff;
  color: #fff;
  border-top-right-radius: 2px;
}

.assistant-bubble {
  background: #f4f6f8;
  color: #303133;
  border-top-left-radius: 2px;
}

.msg-meta {
  margin-top: 4px;
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #a8abb2;
}

.interrupted {
  color: #e6a23c;
}

/* markdown 渲染样式 */
.markdown-body :deep(p) {
  margin: 0 0 8px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(code) {
  background: #eceef1;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 13px;
}

.markdown-body :deep(pre) {
  background: #2d2d2d;
  color: #eee;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.markdown-body :deep(blockquote) {
  margin: 6px 0;
  padding: 4px 12px;
  border-left: 3px solid #dcdfe6;
  color: #909399;
}
</style>
