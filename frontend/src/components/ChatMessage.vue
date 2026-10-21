<script setup>
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'

import CitationList from '@/components/CitationList.vue'

// html: false 防止回答中的 HTML 被注入执行（XSS 防护）
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const props = defineProps({
  message: { type: Object, required: true },
})

const isUser = computed(() => props.message.role === 'user')
const refs = computed(() => props.message.references || [])
const activeNames = ref([])

// 把 [n] 角标替换成可点击的 sup；历史消息的引用快照存在消息记录里
const rendered = computed(() => {
  let html = md.render(props.message.content || '')
  if (!isUser.value && refs.value.length) {
    html = html.replace(/\[(\d+)\]/g, (match, n) => {
      return refs.value.some((r) => String(r.index) === n)
        ? `<sup class="cite-link" data-cite="${n}">[${n}]</sup>`
        : match
    })
  }
  return html
})

// 事件委托：点击 [n] 角标展开/收起对应引用
function onContentClick(e) {
  const el = e.target.closest('.cite-link')
  if (!el) return
  const name = el.dataset.cite
  activeNames.value = activeNames.value.includes(name)
    ? activeNames.value.filter((n) => n !== name)
    : [...activeNames.value, name]
}
</script>

<template>
  <div class="msg-row" :class="isUser ? 'is-user' : 'is-assistant'">
    <el-avatar :size="32" class="msg-avatar" :class="isUser ? 'avatar-user' : 'avatar-ai'">
      {{ isUser ? '我' : 'AI' }}
    </el-avatar>
    <div class="msg-body">
      <div v-if="isUser" class="msg-bubble user-bubble">{{ message.content }}</div>
      <template v-else>
        <div
          class="msg-bubble assistant-bubble markdown-body"
          v-html="rendered"
          @click="onContentClick"
        ></div>
        <CitationList v-model:active-names="activeNames" :citations="refs" />
      </template>
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

/* 可点击的引用角标 */
.cite-link {
  color: #409eff;
  cursor: pointer;
  font-weight: 600;
  margin: 0 1px;
}

.cite-link:hover {
  text-decoration: underline;
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
