import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api, tokenStore } from './api'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const out = () => setUser(null)
    window.addEventListener('session-expired', out)
    if (!tokenStore.get()) setReady(true)
    else api('/auth/me').then(setUser).catch(() => tokenStore.clear()).finally(() => setReady(true))
    return () => window.removeEventListener('session-expired', out)
  }, [])

  const finish = useCallback((data) => { tokenStore.set(data.access_token); setUser(data.user); return data.user }, [])
  const login = (email, password) => api('/auth/login', { method: 'POST', body: { email, password } }).then(finish)
  const register = (name, email, password) => api('/auth/register', { method: 'POST', body: { name, email, password } }).then(finish)
  const logout = () => { tokenStore.clear(); setUser(null) }

  return <Ctx.Provider value={{ user, ready, login, register, logout }}>{children}</Ctx.Provider>
}
