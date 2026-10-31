import { useEffect, useState } from 'react'
import { api } from './api'

const fmt = new Intl.NumberFormat(import.meta.env.VITE_LOCALE || 'en-IN', {
  style: 'currency', currency: import.meta.env.VITE_CURRENCY || 'INR', maximumFractionDigits: 2,
})
export const money = (n) => fmt.format(n || 0)
export const fdate = (d) => (d ? new Date(d + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '—')

export const inputCls =
  'w-full rounded-md border border-line bg-white px-3 py-2 text-sm placeholder:text-mute/60 focus:border-brand disabled:bg-wash disabled:text-mute'

const BTN = {
  primary: 'bg-brand text-white hover:bg-brand-dark',
  default: 'bg-white text-ink border border-line hover:bg-wash',
  danger: 'bg-white text-late border border-late/40 hover:bg-late-tint',
  ghost: 'text-brand hover:bg-brand-tint',
}
export function Btn({ variant = 'default', className = '', small, ...p }) {
  return (
    <button
      type="button"
      {...p}
      className={`inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
        small ? 'px-2.5 py-1 text-xs' : 'px-3.5 py-2 text-sm'
      } ${BTN[variant]} ${className}`}
    />
  )
}

const BADGE = {
  paid: 'bg-paid-tint text-paid', active: 'bg-paid-tint text-paid',
  confirmed: 'bg-brand-tint text-brand-dark', quotation: 'bg-amber-tint text-[#8a6100]',
  draft: 'bg-wash text-mute border border-line', closed: 'bg-wash text-mute border border-line',
  cancelled: 'bg-wash text-mute border border-line', paused: 'bg-amber-tint text-[#8a6100]',
  overdue: 'bg-late-tint text-late',
}
export const Badge = ({ status, children }) => (
  <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium capitalize ${BADGE[status] || BADGE.draft}`}>{children || status}</span>
)

export function Field({ label, hint, children, className = '' }) {
  return (
    <label className={`block text-sm ${className}`}>
      <span className="mb-1 block font-medium">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-mute">{hint}</span>}
    </label>
  )
}

export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const k = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-ink/40 p-3 sm:p-8" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label={title} className={`w-full ${wide ? 'max-w-4xl' : 'max-w-xl'} rounded-lg bg-white shadow-xl`}>
        <div className="flex items-center justify-between border-b border-line px-5 py-3">
          <h2 className="text-base font-semibold">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded px-2 text-xl leading-none text-mute hover:bg-wash">×</button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export const Notice = ({ kind = 'error', children }) =>
  children ? (
    <div role={kind === 'error' ? 'alert' : 'status'} className={`mb-3 rounded-md px-3 py-2 text-sm ${kind === 'error' ? 'bg-late-tint text-late' : 'bg-paid-tint text-paid'}`}>{children}</div>
  ) : null

export function PageHead({ title, children, sub }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {sub && <p className="mt-0.5 text-sm text-mute">{sub}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  )
}

export function Table({ columns, rows, onRow, empty = 'Nothing here yet.' }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line bg-wash/60 text-left text-xs text-mute">
            {columns.map((c) => (
              <th key={c.label} className={`px-3 py-2 font-medium ${c.right ? 'text-right' : ''}`}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={columns.length} className="px-3 py-10 text-center text-mute">{empty}</td></tr>
          )}
          {rows.map((r, i) => (
            <tr key={r.id ?? i} onClick={onRow && (() => onRow(r))}
                onKeyDown={onRow && ((e) => e.key === 'Enter' && onRow(r))} tabIndex={onRow ? 0 : undefined}
                className={`border-b border-line/70 last:border-0 ${onRow ? 'cursor-pointer hover:bg-brand-tint/40' : ''}`}>
              {columns.map((c) => (
                <td key={c.label} className={`px-3 py-2.5 ${c.right ? 'text-right' : ''}`}>{c.render ? c.render(r) : r[c.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Pager({ total, limit, offset, onChange }) {
  if (total <= limit) return <p className="mt-2 text-xs text-mute">{total} {total === 1 ? 'record' : 'records'}</p>
  const from = offset + 1, to = Math.min(offset + limit, total)
  return (
    <div className="mt-3 flex items-center justify-between text-sm text-mute">
      <span>{from}–{to} of {total}</span>
      <div className="flex gap-2">
        <Btn small disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>Previous</Btn>
        <Btn small disabled={to >= total} onClick={() => onChange(offset + limit)}>Next</Btn>
      </div>
    </div>
  )
}

// tiny cache so selects across the app share one request per endpoint
const cache = new Map()
export function useOptions(path) {
  const [data, setData] = useState(cache.get(path) || [])
  useEffect(() => {
    if (!path) return
    let live = true
    api(path).then((d) => { cache.set(path, d); live && setData(d) }).catch(() => {})
    return () => { live = false }
  }, [path])
  return data
}
export const bustOptions = (path) => cache.delete(path)

export function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value)
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t) }, [value, ms])
  return v
}

const RULES = [
  ['More than 8 characters', (p) => p.length > 8],
  ['An uppercase letter', (p) => /[A-Z]/.test(p)],
  ['A lowercase letter', (p) => /[a-z]/.test(p)],
  ['A special character, like @ # ! $', (p) => /[^A-Za-z0-9]/.test(p)],
]
export const passwordIsValid = (p = '') => RULES.every(([, ok]) => ok(p))
export function PasswordRules({ value = '' }) {
  return (
    <ul className="mt-1.5 space-y-0.5 text-xs" aria-label="Password rules">
      {RULES.map(([label, ok]) => {
        const good = ok(value)
        return (
          <li key={label} className={good ? 'text-paid' : 'text-mute'}>
            <span aria-hidden="true">{good ? '✓' : '○'}</span> {label}
            <span className="sr-only">{good ? ' (met)' : ' (not met yet)'}</span>
          </li>
        )
      })}
    </ul>
  )
}
