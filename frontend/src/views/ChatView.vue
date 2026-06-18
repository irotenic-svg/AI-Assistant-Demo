<template>
  <div class="chat-container">
    <!-- Header -->
    <header class="chat-header">
      <div class="chat-header-left">
        <div class="logo-mark">
          <span class="caduceus">⚕</span>
        </div>
        <div class="header-titles">
          <span class="header-title">医疗知识问答</span>
          <span class="header-subtitle">
            <span :class="['status-dot', { offline: !healthStatus }]"></span>
            {{ healthStatus ? 'RAG 就绪 · 207K 文献' : '离线' }}
          </span>
        </div>
      </div>
      <div class="header-actions">
        <el-button
          text
          size="small"
          @click="handleClearHistory"
          :disabled="messages.length === 0"
        >
          <el-icon style="margin-right:5px"><Delete /></el-icon>
          清空对话
        </el-button>
      </div>
    </header>

    <!-- Messages -->
    <div class="chat-body" ref="chatBodyRef">
      <div class="message-list">
        <!-- Empty State -->
        <div v-if="messages.length === 0" class="empty-state">
          <div class="hex-icon">
            <span class="inner-glyph">⚕</span>
          </div>
          <div class="greeting">有什么医学问题需要查询？</div>
          <div class="description">
            基于 20 万+ 医疗文献、临床问答与生物医学研究数据，
            <br>为您提供循证医学知识解答。
          </div>
          <div class="suggestions">
            <div
              v-for="q in suggestions"
              :key="q"
              class="suggestion-chip"
              @click="handleSuggestion(q)"
            >
              {{ q }}
            </div>
          </div>
        </div>

        <!-- Messages -->
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message-item', msg.role]"
        >
          <!-- AI avatar -->
          <div v-if="msg.role === 'ai'" class="message-avatar">⚕</div>

          <div class="message-content">
            <div class="message-bubble" v-html="renderMarkdown(msg.content)"></div>

            <!-- Sources -->
            <div v-if="msg.sources && msg.sources.length > 0" class="source-panel">
              <el-popover
                placement="right"
                :width="420"
                trigger="click"
                popper-class="source-detail-popover"
              >
                <template #reference>
                  <div class="source-toggle-btn">
                    <span class="icon">▦</span>
                    <span>引用来源 ({{ msg.sources.length }})</span>
                    <span class="arrow">→</span>
                  </div>
                </template>
                <div class="source-popover-content">
                  <div
                    v-for="(src, si) in msg.sources"
                    :key="si"
                    class="source-popover-item"
                  >
                    <div class="source-header">
                      <el-tag
                        size="small"
                        :type="src.source === 'PubMedQA' ? 'primary' : 'success'"
                        effect="light"
                      >
                        {{ src.source }}
                      </el-tag>
                      <span class="source-index">{{ String(si + 1).padStart(2, '0') }}</span>
                    </div>
                    <div v-if="src.question" class="source-question">
                      {{ src.question }}
                    </div>
                    <div class="source-content">{{ src.content }}</div>
                  </div>
                </div>
              </el-popover>
            </div>
          </div>

          <!-- User avatar -->
          <div v-if="msg.role === 'user'" class="message-avatar">?</div>
        </div>

        <!-- Streaming cursor — shown when AI is thinking/generating -->
        <div v-if="loading && messages.length && messages[messages.length-1].role === 'ai'" class="stream-cursor">
          <span class="cursor-blink">▍</span>
          {{ thinking ? '思考中…' : '生成中…' }}
        </div>
      </div>
    </div>

    <!-- Input — The Prescription Slip -->
    <div class="chat-footer">
      <!-- Amber threshold — separates conversation from composition -->
      <div class="footer-threshold"></div>

      <div class="chat-input-wrapper">
        <!-- Writing surface -->
        <div class="input-writing-surface">
          <div class="input-accent-strip"></div>
          <textarea
            ref="textareaRef"
            v-model="inputText"
            class="input-textarea"
            :placeholder="loading ? (thinking ? '正在思考…' : '正在检索文献…') : '描述您的医学问题…'"
            :disabled="loading"
            rows="2"
            @keydown="handleKeydown"
            @input="onTextareaInput"
          ></textarea>
        </div>

        <!-- Action bar -->
        <div class="input-action-bar">
          <span class="input-keyhint">
            <kbd>Enter</kbd> 发送 · <kbd>Shift</kbd> + <kbd>Enter</kbd> 换行
          </span>

          <button
            class="send-btn"
            :class="{ loading: loading, active: inputText.trim() && !loading }"
            :disabled="!inputText.trim() || loading"
            @click="handleSend"
            :title="loading ? '检索中…' : '发送'"
          >
            <span class="send-btn-hex">
              <span class="send-btn-icon">{{ loading ? '⏳' : '↑' }}</span>
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { sendMessageStream, clearHistory, healthCheck } from '@/api/chat'

const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const thinking = ref(false)
const healthStatus = ref(false)
const chatBodyRef = ref(null)
const textareaRef = ref(null)
const sessionId = ref('default')

const suggestions = [
  '糖尿病的常见症状有哪些？',
  '感冒和流感有什么区别？',
  '高血压患者饮食需要注意什么？',
  '如何预防骨质疏松？',
  '儿童发烧应该如何处理？',
]

// ── Helpers ──────────────────────────────────────

function scrollToBottom() {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTo({
        top: chatBodyRef.value.scrollHeight,
        behavior: 'smooth',
      })
    }
  })
}

function renderMarkdown(text) {
  if (!text) return ''

  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Fenced code blocks
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code>${code.trim()}</code></pre>`
  )

  // Bold, italic, bold-italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // Inline code
  html = html.replace(/`(.+?)`/g, '<code>$1</code>')

  // Headings
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>')

  // Blockquote
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')

  // Unordered list
  html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>')
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')

  // Ordered list
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr>')

  // Paragraphs
  html = html.replace(/\n\n+/g, '</p><p>')
  html = html.replace(/\n/g, '<br>')

  // Cleanup
  html = html.replace(/<p>\s*<\/p>/g, '')
  html = html.replace(/<p>(<[ou]l>)/g, '$1')
  html = html.replace(/(<\/[ou]l>)<\/p>/g, '$1')

  return `<p>${html}</p>`
}

// ── Actions ──────────────────────────────────────

async function handleSend() {
  const question = inputText.value.trim()
  if (!question || loading.value) return

  // User message
  messages.value.push({ role: 'user', content: question })
  inputText.value = ''
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }

  // Placeholder AI message — content fills in as tokens arrive
  const aiMsg = { role: 'ai', content: '', sources: [] }
  messages.value.push(aiMsg)
  scrollToBottom()

  loading.value = true
  thinking.value = false

  // 暂存 sources，等首个 token 到达后再显示，避免"空回答+已显示引用来源"
  let pendingSources = []
  let sourcesApplied = false

  // 流式渲染节流: 用 requestAnimationFrame 同步到屏幕刷新率
  let rafPending = false
  function scheduleRender() {
    if (!rafPending) {
      rafPending = true
      requestAnimationFrame(() => {
        rafPending = false
        scrollToBottom()
      })
    }
  }

  try {
    for await (const event of sendMessageStream(question, sessionId.value)) {
      switch (event.type) {
        case 'sources':
          pendingSources = event.data || []
          break

        case 'thinking':
          thinking.value = true
          break

        case 'token':
          // 首个 token 到达 → 应用暂存的 sources
          if (!sourcesApplied) {
            aiMsg.sources = pendingSources
            sourcesApplied = true
          }
          thinking.value = false
          // 直接追加 token，不做 setTimeout 缓冲 — 每 token 立即触发 Vue 响应式更新
          aiMsg.content += event.data
          scheduleRender()
          break

        case 'error':
          thinking.value = false
          if (!aiMsg.content) {
            aiMsg.content = `处理错误: ${event.data}`
            aiMsg.sources = pendingSources
          }
          ElMessage.warning(event.data)
          break

        case 'done':
          thinking.value = false
          if (!aiMsg.content) {
            aiMsg.content = '抱歉，未能生成回答。'
            aiMsg.sources = pendingSources
          } else if (!sourcesApplied) {
            // 如果所有 token 都没触发（极端情况），兜底应用 sources
            aiMsg.sources = pendingSources
          }
          break
      }
    }
  } catch (err) {
    thinking.value = false
    aiMsg.content = aiMsg.content || `请求失败: ${err.message}。请检查后端服务是否正常运行。`
    aiMsg.sources = pendingSources
    ElMessage.error('无法连接到后端服务')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function handleSuggestion(q) {
  inputText.value = q
  handleSend()
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function onTextareaInput() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'
}

async function handleClearHistory() {
  try {
    await clearHistory(sessionId.value)
    messages.value = []
    ElMessage.success('对话已清空')
  } catch {
    messages.value = []
  }
}

onMounted(async () => {
  try {
    const health = await healthCheck()
    healthStatus.value = health.status === 'ok'
  } catch {
    healthStatus.value = false
  }
})
</script>
