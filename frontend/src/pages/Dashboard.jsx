import { useEffect, useMemo, useState } from 'react'
import { api, qs } from '../api'
import { OptionSelect } from '../Editors'
import { Badge, Notice, PageHead, Table, fdate, inputCls, money } from '../ui'
import { InvoiceDetail } from './Invoices'

const iso = (d) => d.toISOString().slice(0, 10)
const monthStart = () => { const d = new Date(); d.setDate(1); return iso(d) }

function Ledger({ l }) {
  const pct = (n) => (l.billed ? Math.max((n / l.billed) * 100, n > 0 ? 1.5 : 0) : 0)
  const parts = [
    { key: 'collected', label: 'Collected', n: l.collected, cls: 'bg-paid' },
    { key: 'open', label: 'Open, not yet due', n: l.open, cls: 'bg-brand/70' },
    { key: 'overdue', label: 'Overdue', n: l.overdue, cls: 'bg-late' },
  ]
  return (
    <section aria-label="Invoices issued in this period" className="mb-6 rounded-lg border border-line bg-white p-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold">Where this period's billing stands</h2>
        <p className="text-sm text-mute">Billed <b className="text-ink">{money(l.billed)}</b></p>
      </div>
      <div className="flex h-5 overflow-hidden rounded bg-wash" role="img" aria-label={parts.map((p) => `${p.label} ${money(p.n)}`).join(', ')}>
        {l.billed > 0 && parts.map((p) => <div key={p.key} className={p.cls} style={{ width: `${pct(p.n)}%` }} />)}
      </div>
      {l.billed === 0 ? <p className="mt-3 text-sm text-mute">No confirmed invoices were issued in this period.</p> : (
        <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
          {parts.map((p) => (
            <li key={p.key} className="flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-sm ${p.cls}`} /><span className="text-mute">{p.label}</span><b className="ml-auto sm:ml-0">{money(p.n)}</b></li>
          ))}
        </ul>
      )}
    </section>
  )
}

function Months({ rows }) {
  const series = useMemo(() => {
    const map = Object.fromEntries(rows.map((r) => [r.month, r.amount]))
    const out = []; const d = new Date(); d.setDate(1)
    for (let i = 11; i >= 0; i--) {
      const x = new Date(d.getFullYear(), d.getMonth() - i, 1)
      const k = `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}`
      out.push({ k, label: x.toLocaleDateString(undefined, { month: 'short' }), amount: map[k] || 0 })
    }
    return out
  }, [rows])
  const max = Math.max(...series.map((s) => s.amount), 1)
  return (
    <section aria-label="Collections by month" className="rounded-lg border border-line bg-white p-5">
      <h2 className="mb-4 text-sm font-semibold">Collected per month, last 12 months</h2>
      <div className="flex h-36 items-end gap-1.5">
        {series.map((s) => (
          <div key={s.k} className="flex h-full flex-1 flex-col justify-end" title={`${s.k}: ${money(s.amount)}`}>
            <div className="rounded-t bg-brand/80" style={{ height: `${(s.amount / max) * 100}%`, minHeight: s.amount ? 3 : 0 }} />
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex gap-1.5 text-[11px] text-mute">{series.map((s) => <span key={s.k} className="flex-1 text-center">{s.label}</span>)}</div>
    </section>
  )
}

export default function Dashboard() {
  const [f, setF] = useState({ date_from: monthStart(), date_to: iso(new Date()), plan_id: '' })
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [open, setOpen] = useState(null)
  const load = () => api('/dashboard' + qs(f)).then((x) => { setD(x); setErr('') }).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [f.date_from, f.date_to, f.plan_id])

  return (
    <div>
      <PageHead title="Finance overview" sub="Month-end view of subscriptions, collections and money still owed.">
        <input aria-label="From" type="date" className={`${inputCls} !w-40`} value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} />
        <input aria-label="To" type="date" className={`${inputCls} !w-40`} value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} />
        <div className="w-44"><OptionSelect from="/plans" blank="All plans" aria-label="Plan" value={f.plan_id} onChange={(x) => setF({ ...f, plan_id: x })} /></div>
      </PageHead>
      <Notice>{err}</Notice>
      {!d ? <p className="text-sm text-mute">Loading…</p> : (
        <>
          <Ledger l={d.ledger} />
          <dl className="mb-6 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line lg:grid-cols-4">
            {[
              ['Active subscriptions', d.active_subscriptions, ''],
              ['Revenue collected', money(d.revenue_collected), `${fdate(d.range.from)} – ${fdate(d.range.to)}`],
              ['Still owed', money(d.amount_owed), 'All confirmed invoices, any date'],
              ['Overdue', money(d.overdue_amount), `${d.overdue_count} invoice${d.overdue_count === 1 ? '' : 's'}`],
            ].map(([k, v, s], i) => (
              <div key={k} className="bg-white p-4">
                <dt className="text-xs text-mute">{k}</dt>
                <dd className={`mt-1 text-xl font-semibold ${i === 3 && d.overdue_count ? 'text-late' : ''}`}>{v}</dd>
                {s && <p className="mt-0.5 text-xs text-mute">{s}</p>}
              </div>
            ))}
          </dl>
          <div className="grid gap-6 xl:grid-cols-2">
            <Months rows={d.monthly_collections} />
            <section aria-label="Overdue invoices">
              <h2 className="mb-2 text-sm font-semibold">Oldest overdue invoices</h2>
              <Table onRow={(r) => setOpen(r.id)} rows={d.overdue_invoices} empty="Nothing is overdue. Nice." columns={[
                { label: 'Invoice', key: 'number' }, { label: 'Customer', key: 'customer_name' },
                { label: 'Due', render: (r) => fdate(r.due_date) }, { label: 'Owed', right: true, render: (r) => <span className="text-late">{money(r.outstanding)}</span> }]} />
            </section>
          </div>
        </>
      )}
      {open && <InvoiceDetail id={open} staff onClose={() => setOpen(null)} onChange={load} />}
    </div>
  )
}
