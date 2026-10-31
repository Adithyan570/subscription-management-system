import { useCallback, useEffect, useState } from 'react'
import { api, openPrintable, qs } from '../api'
import { Badge, Btn, Field, Modal, Notice, PageHead, Pager, Table, fdate, inputCls, money, useDebounced } from '../ui'

export const invStatus = (r) => (r.is_overdue ? 'overdue' : r.status)

export function InvoiceDetail({ id, staff, onClose, onChange }) {
  const [inv, setInv] = useState(null)
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const [pay, setPay] = useState(null)

  const load = useCallback(() => api(`/invoices/${id}`).then(setInv).catch((e) => setErr(e.message)), [id])
  useEffect(() => { load() }, [load])

  const act = async (fn) => {
    setBusy(true); setErr('')
    try { const r = await fn(); if (r?.id) setInv(r); onChange?.() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const post = (a) => act(() => api(`/invoices/${id}/${a}`, { method: 'POST' }))

  if (!inv) return <Modal title="Invoice" onClose={onClose}><Notice>{err}</Notice>{!err && <p className="text-sm text-mute">Loading…</p>}</Modal>

  return (
    <Modal title={`Invoice ${inv.number}`} onClose={onClose} wide>
      <Notice>{err}</Notice>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="text-sm leading-6">
          <div><span className="text-mute">Customer </span>{inv.customer_name}</div>
          <div><span className="text-mute">Subscription </span>{inv.subscription_number}</div>
          <div><span className="text-mute">Period </span>{fdate(inv.period_start)} – {fdate(inv.period_end)}</div>
          <div><span className="text-mute">Issued </span>{fdate(inv.issue_date)} <span className="text-mute"> · Due </span>{fdate(inv.due_date)}</div>
          {inv.sent_at && <div className="text-mute">Sent {new Date(inv.sent_at + 'Z').toLocaleString()}</div>}
        </div>
        <Badge status={invStatus(inv)} />
      </div>
      <Table columns={[
        { label: 'Description', key: 'description' }, { label: 'Qty', right: true, key: 'quantity' },
        { label: 'Unit price', right: true, render: (l) => money(l.unit_price) },
        { label: 'Discount', right: true, render: (l) => (l.discount ? `−${money(l.discount)}` : '—') },
        { label: 'Tax', right: true, render: (l) => `${l.tax_rate}%` },
        { label: 'Amount', right: true, render: (l) => money(l.amount - l.discount + l.tax_amount) },
      ]} rows={inv.lines} />
      <dl className="ml-auto mt-4 grid w-64 grid-cols-2 gap-y-1 text-sm">
        <dt className="text-mute">Subtotal</dt><dd className="text-right">{money(inv.subtotal)}</dd>
        <dt className="text-mute">Discount</dt><dd className="text-right">−{money(inv.discount_total)}</dd>
        <dt className="text-mute">Tax</dt><dd className="text-right">{money(inv.tax_total)}</dd>
        <dt className="font-semibold">Total</dt><dd className="text-right font-semibold">{money(inv.total)}</dd>
        <dt className="text-mute">Paid</dt><dd className="text-right">{money(inv.amount_paid)}</dd>
        <dt className="font-semibold">Balance due</dt><dd className={`text-right font-semibold ${inv.is_overdue ? 'text-late' : ''}`}>{money(inv.outstanding)}</dd>
      </dl>

      {inv.payments.length > 0 && (
        <div className="mt-5">
          <h3 className="mb-2 text-sm font-semibold">Payments</h3>
          <Table columns={[{ label: 'Date', render: (p) => fdate(p.paid_on) }, { label: 'Method', key: 'method' },
            { label: 'Notes', render: (p) => p.notes || '—' }, { label: 'Amount', right: true, render: (p) => money(p.amount) }]} rows={inv.payments} />
        </div>
      )}

      {staff && inv.status === 'confirmed' && (
        pay ? (
          <form className="mt-5 grid gap-3 rounded-lg border border-line p-4 sm:grid-cols-4" onSubmit={(e) => {
            e.preventDefault()
            act(async () => { const r = await api(`/invoices/${id}/payments`, { method: 'POST', body: { ...pay, amount: Number(pay.amount) } }); setPay(null); return r })
          }}>
            <Field label="Method"><select className={inputCls} value={pay.method} onChange={(e) => setPay({ ...pay, method: e.target.value })}>
              {['Cash', 'Card', 'Bank transfer', 'UPI', 'Cheque', 'Other'].map((m) => <option key={m}>{m}</option>)}</select></Field>
            <Field label="Amount"><input className={inputCls} type="number" step="0.01" min="0.01" max={inv.outstanding} required value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value })} /></Field>
            <Field label="Date"><input className={inputCls} type="date" required value={pay.paid_on} onChange={(e) => setPay({ ...pay, paid_on: e.target.value })} /></Field>
            <Field label="Notes"><input className={inputCls} value={pay.notes} onChange={(e) => setPay({ ...pay, notes: e.target.value })} /></Field>
            <div className="flex gap-2 sm:col-span-4"><button disabled={busy} className="rounded-md bg-brand px-3.5 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50">Record payment</button><Btn onClick={() => setPay(null)}>Cancel</Btn></div>
          </form>
        ) : null
      )}

      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <Btn onClick={() => act(() => openPrintable(id))}>Print</Btn>
        {staff && inv.status === 'draft' && <Btn variant="primary" disabled={busy} onClick={() => post('confirm')}>Confirm invoice</Btn>}
        {staff && ['confirmed', 'paid'].includes(inv.status) && <Btn disabled={busy} onClick={() => post('send')}>{inv.sent_at ? 'Send again' : 'Send to customer'}</Btn>}
        {staff && inv.status === 'confirmed' && !pay && <Btn variant="primary" onClick={() => setPay({ method: 'Bank transfer', amount: inv.outstanding, paid_on: new Date().toISOString().slice(0, 10), notes: '' })}>Record payment</Btn>}
        {staff && ['draft', 'confirmed'].includes(inv.status) && inv.amount_paid === 0 && (
          <Btn variant="danger" disabled={busy} onClick={() => confirm('Cancel this invoice? Its billing cycle will not be billed again.') && post('cancel')}>Cancel invoice</Btn>)}
      </div>
    </Modal>
  )
}

const LIMIT = 25
export default function Invoices() {
  const [f, setF] = useState({ status: '', q: '', date_from: '', date_to: '' })
  const [offset, setOffset] = useState(0)
  const [data, setData] = useState({ items: [], total: 0 })
  const [open, setOpen] = useState(null)
  const [err, setErr] = useState(''); const [info, setInfo] = useState('')
  const [autoConfirm, setAutoConfirm] = useState(false)
  const q = useDebounced(f.q)

  const load = useCallback(() => {
    const { status, date_from, date_to } = f
    api('/invoices' + qs({ status: status === 'overdue' ? '' : status, overdue: status === 'overdue', q, date_from, date_to, limit: LIMIT, offset }))
      .then((d) => { setData(d); setErr('') }).catch((e) => setErr(e.message))
  }, [f.status, f.date_from, f.date_to, q, offset])
  useEffect(() => { load() }, [load])
  useEffect(() => { setOffset(0) }, [f.status, f.date_from, f.date_to, q])

  const runBilling = async () => {
    setErr(''); setInfo('')
    try {
      const r = await api('/billing/run' + qs({ auto_confirm: autoConfirm }), { method: 'POST' })
      setInfo(r.invoices_created ? `Created ${r.invoices_created} invoice${r.invoices_created > 1 ? 's' : ''}.` : 'Everything due is already billed.')
      load()
    } catch (e) { setErr(e.message) }
  }

  return (
    <div>
      <PageHead title="Invoices" sub="Generated automatically from active subscriptions on their billing days.">
        <label className="mr-1 flex items-center gap-1.5 text-sm text-mute"><input type="checkbox" className="accent-brand" checked={autoConfirm} onChange={(e) => setAutoConfirm(e.target.checked)} />Confirm new invoices</label>
        <Btn variant="primary" onClick={runBilling}>Run billing now</Btn>
      </PageHead>
      <Notice>{err}</Notice><Notice kind="ok">{info}</Notice>
      <div className="mb-3 flex flex-wrap gap-2">
        <input aria-label="Search" className={`${inputCls} !w-56`} placeholder="Search number or customer" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
        <select aria-label="Status" className={`${inputCls} !w-40`} value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>
          <option value="">All statuses</option>
          {['draft', 'confirmed', 'paid', 'overdue', 'cancelled'].map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
        </select>
        <input aria-label="Issued from" type="date" className={`${inputCls} !w-40`} value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} />
        <input aria-label="Issued to" type="date" className={`${inputCls} !w-40`} value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} />
      </div>
      <Table onRow={(r) => setOpen(r.id)} rows={data.items} empty="No invoices match these filters." columns={[
        { label: 'Number', render: (r) => <span className="font-medium">{r.number}</span> }, { label: 'Customer', key: 'customer_name' },
        { label: 'Subscription', key: 'subscription_number' },
        { label: 'Period', render: (r) => `${fdate(r.period_start)}` }, { label: 'Due', render: (r) => fdate(r.due_date) },
        { label: 'Total', right: true, render: (r) => money(r.total) },
        { label: 'Owed', right: true, render: (r) => (r.outstanding ? money(r.outstanding) : '—') },
        { label: 'Status', render: (r) => <Badge status={invStatus(r)} /> }]} />
      <Pager total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
      {open && <InvoiceDetail id={open} staff onClose={() => setOpen(null)} onChange={load} />}
    </div>
  )
}
