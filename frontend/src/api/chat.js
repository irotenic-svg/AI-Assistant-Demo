import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,  // RAG 可能较慢，设置 60s
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * 发送问题，获取 AI 回答（非流式）
 * @param {string} question - 用户问题
 * @param {string} sessionId - 会话 ID
 * @returns {Promise<{answer: string, sources: Array, session_id: string}>}
 */
export function sendMessage(question, sessionId = 'default') {
  return api.post('/chat', {
    question,
    session_id: sessionId,
  }).then(res => res.data)
}

/**
 * 发送问题，流式获取 AI 回答 (Server-Sent Events)
 *
 * 用法:
 *   for await (const event of sendMessageStream(question, sessionId)) {
 *     switch (event.type) {
 *       case 'sources': ...   // { type: 'sources', data: [...] }
 *       case 'token':   ...   // { type: 'token',   data: '...' }
 *       case 'done':    ...   // { type: 'done' }
 *       case 'error':   ...   // { type: 'error',   data: '...' }
 *     }
 *   }
 *
 * @param {string} question - 用户问题
 * @param {string} sessionId - 会话 ID
 * @returns {AsyncGenerator<Object>} 事件流
 */
export async function* sendMessageStream(question, sessionId = 'default') {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ error: 'Network error' }))
    throw new Error(err.error || `HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE lines end with \n\n
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      const lines = part.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6))
            yield event
          } catch {
            // skip malformed JSON
          }
        }
      }
    }
  }

  // Flush remaining buffer
  if (buffer.trim()) {
    const lines = buffer.split('\n')
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6))
          yield event
        } catch {
          // skip
        }
      }
    }
  }
}

/**
 * 获取对话历史
 * @param {string} sessionId - 会话 ID
 * @returns {Promise<{session_id: string, messages: Array}>}
 */
export function getHistory(sessionId = 'default') {
  return api.get('/history', {
    params: { session_id: sessionId },
  }).then(res => res.data)
}

/**
 * 清空对话历史
 * @param {string} sessionId - 会话 ID
 */
export function clearHistory(sessionId = 'default') {
  return api.delete('/history', {
    data: { session_id: sessionId },
  }).then(res => res.data)
}

/**
 * 健康检查
 */
export function healthCheck() {
  return api.get('/health').then(res => res.data)
}

export default api
