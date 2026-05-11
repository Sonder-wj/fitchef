const TOKEN_KEY = 'fitchef_token'
const USER_KEY = 'fitchef_user'

function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function login(email, password) {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  })
  if (!res.ok) {
    const e = await res.json()
    throw new Error(e.detail || '登录失败')
  }
  const data = await res.json()
  localStorage.setItem(TOKEN_KEY, data.access_token)
  return data
}

export async function register(name, email, password) {
  const res = await fetch('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: name, email, password }),
  })
  if (!res.ok) {
    const e = await res.json()
    throw new Error(e.detail || '注册失败')
  }
  const data = await res.json()
  // Auto-login after register
  return login(email, password)
}

export async function getMe() {
  const res = await fetch('/auth/me', { headers: authHeaders() })
  if (!res.ok) {
    localStorage.removeItem(TOKEN_KEY)
    return null
  }
  const user = await res.json()
  localStorage.setItem(USER_KEY, JSON.stringify(user))
  return user
}

export function getSavedUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY))
  } catch { return null }
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isLoggedIn() {
  return !!getToken()
}

// ── Conversations ──

export async function listConversations() {
  const res = await fetch('/chat/conversations', { headers: authHeaders() })
  if (!res.ok) throw new Error('获取会话列表失败')
  return res.json()
}

export async function createConversation() {
  const res = await fetch('/chat/conversations', {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('创建会话失败')
  return res.json()
}

export async function getMessages(convId) {
  const res = await fetch(`/chat/conversations/${convId}/messages`, { headers: authHeaders() })
  if (!res.ok) throw new Error('获取消息失败')
  return res.json()
}

export async function deleteConversation(convId) {
  const res = await fetch(`/chat/conversations/${convId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('删除会话失败')
  return res.json()
}

// ── RAG Chat (SSE streaming) ──

export function sendMessage(message, conversationId, { onToken, onEvent, onDone, onError }) {
  const headers = {
    'Content-Type': 'application/json',
    ...authHeaders(),
  }
  const body = JSON.stringify({
    message,
    conversation_id: conversationId || null,
  })

  fetch('/chat/rag', { method: 'POST', headers, body })
    .then(async (res) => {
      if (res.status === 401) {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
        window.location.reload()
        return
      }
      if (!res.ok) {
        const err = await res.text()
        throw new Error(err || '请求失败')
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const dataStr = line.slice(6).trim()
          if (!dataStr) continue

          try {
            const data = JSON.parse(dataStr)
            if (typeof data === 'string') {
              onToken(data)
            } else if (data.type) {
              onEvent(data.type, data)
            }
          } catch {
            // skip malformed
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      onError(err.message)
    })
}

// ── Knowledge Base ──

export async function getKnowledgeStats() {
  const res = await fetch('/chat/knowledge/stats', { headers: authHeaders() })
  if (!res.ok) throw new Error('获取知识库统计失败')
  return res.json()
}
