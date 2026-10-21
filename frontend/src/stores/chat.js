import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'

import http from '@/api/http'
import { streamChat } from '@/api/sse'

// 聊天状态：会话列表、当前会话消息、流式生成状态
export const useChatStore = defineStore('chat', {
  state: () => ({
    conversations: [],
    currentId: null,
    currentTitle: '',
    messages: [],
    streaming: false,
    streamingText: '',
    citations: [],
    controller: null, // 用于"停止生成"
  }),
  getters: {
    currentConversation: (s) => s.conversations.find((c) => c.id === s.currentId) || null,
  },
  actions: {
    async loadConversations() {
      const { data } = await http.get('/conversations')
      this.conversations = data
      this.currentTitle = this.currentConversation?.title || ''
    },
    async selectConversation(id) {
      this.currentId = id
      this.messages = []
      this.citations = []
      const { data } = await http.get(`/conversations/${id}/messages`)
      this.messages = data
      this.currentTitle = this.currentConversation?.title || ''
    },
    newConversation() {
      this.currentId = null
      this.currentTitle = ''
      this.messages = []
      this.citations = []
    },
    // 彻底重置：切换账号/退出登录时调用，防止上一个用户的数据残留在界面
    reset() {
      this.stop()
      this.conversations = []
      this.currentId = null
      this.currentTitle = ''
      this.messages = []
      this.streaming = false
      this.streamingText = ''
      this.citations = []
    },
    async rename(id, title) {
      await http.patch(`/conversations/${id}`, { title })
      await this.loadConversations()
    },
    async remove(id) {
      await http.delete(`/conversations/${id}`)
      if (this.currentId === id) this.newConversation()
      await this.loadConversations()
    },
    async send(message) {
      if (this.streaming || !message.trim()) return
      this.messages.push({ role: 'user', content: message })
      this.streaming = true
      this.streamingText = ''
      this.citations = []
      this.controller = new AbortController()
      try {
        await streamChat({
          message,
          conversationId: this.currentId,
          signal: this.controller.signal,
          onEvent: ({ event, data }) => this.handleEvent(event, data),
        })
      } catch (e) {
        // fetch 层已弹出错误提示；这里把已生成的部分保留下来
        if (this.streamingText) {
          this.messages.push({
            role: 'assistant',
            content: this.streamingText,
            interrupted: true,
          })
          this.streamingText = ''
        }
      } finally {
        this.streaming = false
        this.controller = null
        await this.loadConversations()
      }
    },
    handleEvent(event, data) {
      if (event === 'meta') {
        // 新会话时后端在 meta 里告知会话 id
        if (data.conversation_id) this.currentId = data.conversation_id
        this.citations = data.citations || []
      } else if (event === 'delta') {
        this.streamingText += data.content
      } else if (event === 'done') {
        // 引用以后端过滤后的最终列表为准（与答案中的 [n] 角标严格对应）
        this.messages.push({
          id: data.message_id,
          role: 'assistant',
          content: this.streamingText,
          references: data.citations || [],
          token_count: data.token_count,
        })
        this.streamingText = ''
        this.citations = data.citations || []
      } else if (event === 'error') {
        if (this.streamingText) {
          this.messages.push({
            role: 'assistant',
            content: this.streamingText,
            interrupted: true,
          })
          this.streamingText = ''
        }
        ElMessage.error(data.detail || '系统繁忙，请稍后重试')
      }
    },
    stop() {
      this.controller?.abort()
    },
  },
})
