const BASE = import.meta.env.VITE_API_URL || '/api'

export const tokenStore = {
  get: () => localStorage.getItem('token'),
  set: (t) => localStorage.setItem('token', t),
  clear: () => localStorage.removeItem('token'),
}

function message(detail) {
  if (!detail) return 'Something went wrong.'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => `${(d.loc || []).slice(1).join(' › ')}: ${d.msg}`).join('; ')
  return JSON.stringify(detail)
}

export async function api(path, { method = 'GET', body, text } = {}) {
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  const t = tokenStore.get()
  if (t) headers.Authorization = `Bearer ${t}`
  const res = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined })
  if (res.status === 401 && t) {
    tokenStore.clear()
    window.dispatchEvent(new Event('session-expired'))
  }
  if (!res.ok) {
    let data = null
    try { data = await res.json() } catch { /* empty */ }
    throw new Error(message(data?.detail))
  }
  if (res.status === 204) return null
  return text ? res.text() : res.json()
}

export const qs = (o) => {
  const p = new URLSearchParams()
  Object.entries(o).forEach(([k, v]) => v !== '' && v != null && v !== false && p.set(k, v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

export async function openPrintable(id) {
  const html = await api(`/invoices/${id}/print`, { text: true })
  const w = window.open('', '_blank')
  if (!w) throw new Error('Allow pop-ups to print invoices.')
  w.document.write(html)
  w.document.close()
  w.focus()
  setTimeout(() => w.print(), 300)
}
