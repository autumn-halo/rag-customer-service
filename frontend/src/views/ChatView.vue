<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'

import ChatMessage from '@/components/ChatMessage.vue'
import ConversationList from '@/components/ConversationList.vue'
import SourcePanel from '@/components/SourcePanel.vue'
import { useChatStore } from '@/stores/chat'

const chat = useChatStore()
const input = ref('')
const messageBoxRef = ref()
const showSources = ref(true)

onMounted(() => chat.loadConversations())

function scrollToBottom() {
  nextTick(() => {
    if (messageBoxRef.value) {
      messageBoxRef.value.scrollTop = messageBoxRef.value.scrollHeight
    }
  })
}

watch(() => chat.streamingText, scrollToBottom)
watch(() => chat.messages.length, scrollToBottom)

function onSelect(id) {
  chat.selectConversation(id)
}

function onCreate() {
  chat.newConversation()
}

async function onSend() {
  const text = input.value.trim()
  if (!text || chat.streaming) return
  input.value = ''
  await chat.send(text)
}

function onKeydown(e) {
  if (e.ctrlKey && e.key === 'Enter') onSend()
}
</script>

<template>
  <div class="chat-page">
    <aside class="conv-aside">
      <ConversationList
        :conversations="chat.conversations"
        :current-id="chat.currentId"
        @select="onSelect"
        @create="onCreate"
        @rename="(id, title) => chat.rename(id, title)"
        @remove="(id) => chat.remove(id)"
      />
    </aside>

    <section class="chat-main">
      <header class="chat-header">
        <span class="chat-title">{{ chat.currentTitle || '新对话' }}</span>
        <el-switch v-model="showSources" size="small" active-text="引用来源" />
      </header>

      <div ref="messageBoxRef" class="message-box">
        <div v-if="!chat.messages.length && !chat.streaming" class="welcome">
          <div class="welcome-icon">🛒</div>
          <h3>你好，我是智能购物助手</h3>
          <p>关于商品参数、退换货政策、物流配送等问题，都可以问我</p>
        </div>
        <ChatMessage
          v-for="(msg, i) in chat.messages"
          :key="msg.id || `local-${i}`"
          :message="msg"
        />
        <div v-if="chat.streaming" class="msg-row is-assistant">
          <el-avatar :size="32" class="msg-avatar avatar-ai">AI</el-avatar>
          <div class="msg-body">
            <div class="msg-bubble assistant-bubble">
              {{ chat.streamingText }}<span class="cursor">▌</span>
            </div>
          </div>
        </div>
      </div>

      <footer class="chat-input">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="输入你的问题，Ctrl+Enter 发送"
          @keydown="onKeydown"
        />
        <div class="input-actions">
          <el-button v-if="chat.streaming" type="warning" plain @click="chat.stop()">
            停止生成
          </el-button>
          <el-button v-else type="primary" :disabled="!input.trim()" @click="onSend">
            发送
          </el-button>
        </div>
      </footer>
    </section>

    <aside v-if="showSources" class="source-aside">
      <SourcePanel :citations="chat.citations" />
    </aside>
  </div>
</template>

<style scoped>
.chat-page {
  height: 100%;
  display: flex;
}

.conv-aside {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid var(--el-border-color-light);
}

.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.chat-header {
  height: 48px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-light);
}

.chat-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.message-box {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.welcome {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.welcome-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.welcome h3 {
  margin: 0 0 8px;
  color: #606266;
}

.welcome p {
  margin: 0;
  font-size: 14px;
}

.chat-input {
  padding: 12px 20px 16px;
  border-top: 1px solid var(--el-border-color-light);
}

.input-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.source-aside {
  width: 300px;
  flex-shrink: 0;
}

/* 流式生成中的消息样式（与 ChatMessage 内保持一致） */
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.msg-avatar {
  flex-shrink: 0;
  font-size: 13px;
}

.avatar-ai {
  background: #e8f3ff;
  color: #409eff;
  font-weight: 600;
}

.msg-body {
  max-width: 76%;
}

.msg-bubble {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
  white-space: pre-wrap;
}

.assistant-bubble {
  background: #f4f6f8;
  color: #303133;
  border-top-left-radius: 2px;
}

.cursor {
  animation: blink 1s infinite;
  color: #409eff;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>
