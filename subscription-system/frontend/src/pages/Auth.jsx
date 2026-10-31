import { useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { Field, Notice, inputCls } from '../ui'

function Shell({ title, children, foot }) {
  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm">
        <p className="mb-6 text-sm font-semibold text-brand">Subscription Manager</p>
        <h1 className="mb-4 text-2xl font-semibold">{title}</h1>
        {children}
        <div className="mt-5 text-sm text-mute">{foot}</div>
      </div>
    </div>
  )
}

const Submit = ({ busy, children }) => (
  <button disabled={busy} className="w-full rounded-md bg-brand px-3.5 py-2.5 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50">{busy ? 'Please wait…' : children}</button>
)

const RULES = 'More than 8 characters, with an uppercase letter, a lowercase letter and a special character.'

export function Login() {
  const { user, login } = useAuth()
  const [email, setEmail] = useState(''); const [pw, setPw] = useState('')
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/" replace />
  const go = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { await login(email, pw) } catch (x) { setErr(x.message); setBusy(false) }
  }
  return (
    <Shell title="Sign in" foot={<><Link className="text-brand" to="/register">Create a customer account</Link> · <Link className="text-brand" to="/forgot-password">Forgot password?</Link></>}>
      <form onSubmit={go} className="space-y-4">
        <Notice>{err}</Notice>
        <Field label="Email"><input className={inputCls} type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field label="Password"><input className={inputCls} type="password" required autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} /></Field>
        <Submit busy={busy}>Sign in</Submit>
      </form>
    </Shell>
  )
}

export function Register() {
  const { user, register } = useAuth()
  const [f, setF] = useState({ name: '', email: '', pw: '' })
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/" replace />
  const go = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { await register(f.name, f.email, f.pw) } catch (x) { setErr(x.message); setBusy(false) }
  }
  return (
    <Shell title="Create your account" foot={<>Already registered? <Link className="text-brand" to="/login">Sign in</Link></>}>
      <form onSubmit={go} className="space-y-4">
        <Notice>{err}</Notice>
        <Field label="Name"><input className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Email"><input className={inputCls} type="email" required autoComplete="username" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Password" hint={RULES}><input className={inputCls} type="password" required autoComplete="new-password" value={f.pw} onChange={(e) => setF({ ...f, pw: e.target.value })} /></Field>
        <Submit busy={busy}>Create account</Submit>
      </form>
    </Shell>
  )
}

export function Forgot() {
  const [email, setEmail] = useState(''); const [msg, setMsg] = useState(''); const [err, setErr] = useState('')
  const go = async (e) => {
    e.preventDefault(); setErr('')
    try { setMsg((await api('/auth/forgot-password', { method: 'POST', body: { email } })).message) } catch (x) { setErr(x.message) }
  }
  return (
    <Shell title="Reset your password" foot={<Link className="text-brand" to="/login">Back to sign in</Link>}>
      <form onSubmit={go} className="space-y-4">
        <Notice>{err}</Notice><Notice kind="ok">{msg}</Notice>
        <Field label="Email" hint="We'll email a link to choose a new password."><input className={inputCls} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Submit>Send reset link</Submit>
      </form>
    </Shell>
  )
}

export function Reset() {
  const [params] = useSearchParams(); const nav = useNavigate()
  const [pw, setPw] = useState(''); const [err, setErr] = useState(''); const [done, setDone] = useState(false)
  const go = async (e) => {
    e.preventDefault(); setErr('')
    try { await api('/auth/reset-password', { method: 'POST', body: { token: params.get('token') || '', password: pw } }); setDone(true); setTimeout(() => nav('/login'), 1500) }
    catch (x) { setErr(x.message) }
  }
  return (
    <Shell title="Choose a new password" foot={<Link className="text-brand" to="/login">Back to sign in</Link>}>
      <form onSubmit={go} className="space-y-4">
        <Notice>{err}</Notice><Notice kind="ok">{done && 'Password updated. Taking you to sign in…'}</Notice>
        <Field label="New password" hint={RULES}><input className={inputCls} type="password" required autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} /></Field>
        <Submit>Update password</Submit>
      </form>
    </Shell>
  )
}
