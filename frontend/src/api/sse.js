// SSE 流式问答客户端：EventSource 不支持 POST，所以用 fetch + ReadableStream
// 按行缓冲解析 SSE 事件块，逐事件回调。

function parseEvent(block) {
  let event = 'message'
  const dataLines = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7).trim()
    else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
  }
  if (!dataLines.length) return null
  return { event, data: JSON.parse(dataLines.join('\n')) }
}

export async function streamChat({ message, conversationId, signal, onEvent }) {
  const token = localStorage.getItem('token')
  const resp = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
    signal,
  })

  if (resp.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
    throw new Error('登录已过期')
  }

  if (!resp.ok || !resp.body) {
    let detail = '网络异常，请稍后重试'
    try {
      detail = (await resp.json()).detail || detail
    } catch {
      /* 非 JSON 响应，保留默认提示 */
    }
    throw new Error(detail)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // SSE 事件以空行分隔；buffer 里可能残留半个事件，等下次数据到达再解析
    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const parsed = parseEvent(block)
      if (parsed) onEvent(parsed)
    }
  }
}
