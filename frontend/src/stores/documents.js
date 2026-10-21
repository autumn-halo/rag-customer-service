import { defineStore } from 'pinia'

import http from '@/api/http'

// 知识库文档状态：列表 + 上传 + 入库进度轮询
export const useDocumentsStore = defineStore('documents', {
  state: () => ({
    items: [],
    total: 0,
    page: 1,
    size: 20,
    loading: false,
    statusFilter: '',
    pollTimer: null,
  }),
  actions: {
    async load() {
      this.loading = true
      try {
        const { data } = await http.get('/documents', {
          params: {
            page: this.page,
            size: this.size,
            status: this.statusFilter || undefined,
          },
        })
        this.items = data.items
        this.total = data.total
      } finally {
        this.loading = false
      }
      this.syncPolling()
    },
    // 只要存在处理中的文档，每 2 秒轮询一次列表，全部完成后自动停止
    syncPolling() {
      const hasProcessing = this.items.some(
        (d) => d.status === 'pending' || d.status === 'processing',
      )
      if (hasProcessing && !this.pollTimer) {
        this.pollTimer = setInterval(() => this.load(), 2000)
      } else if (!hasProcessing && this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    // 切换账号时清空管理页数据（防止上一个用户的数据残留）
    reset() {
      this.stopPolling()
      this.items = []
      this.total = 0
      this.page = 1
      this.statusFilter = ''
    },
    async upload(file) {
      const form = new FormData()
      form.append('files', file)
      await http.post('/documents/upload', form)
      await this.load()
    },
    async reprocess(id) {
      await http.post(`/documents/${id}/reprocess`)
      await this.load()
    },
    async remove(id) {
      await http.delete(`/documents/${id}`)
      await this.load()
    },
    async loadChunks(id, page = 1, size = 20) {
      const { data } = await http.get(`/documents/${id}/chunks`, { params: { page, size } })
      return data
    },
  },
})
