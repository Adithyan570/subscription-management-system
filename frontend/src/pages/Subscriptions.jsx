import { useCallback, useEffect, useState } from 'react'
import { api, qs } from '../api'
import { LinesEditor, OptionSelect, cleanLines } from '../Editors'
import { Badge, Btn, Field, Modal, Notice, PageHead, Pager, Table, fdate, inputCls, money, useDebounced, useOptions } from '../ui'
import { InvoiceDetail, invStatus } from './Invoices'

const STAGES = ['draft', 'quotation', 'confirmed', 'active', 'closed']
const NEXT_LABEL = { draft: 'Send as quotation', quotation: 'Confirm', confirmed: 'Activate', active: 'Close subscription' }
const NEXT = { draft: 'quotation', quotation: 'confirmed', confirmed: 'active', active: 'closed' }
const today = () => new Date().toISOString().slice(0, 10)
const plusYear = () => { const d = new Date(); d.setFullYear(d.getFullYear() + 1); return d.toISOString().slice(0, 10) }
const who = (u) => u.name || u.email

function SubForm({ sub, onClose, onSaved }) {
  const templates = useOptions('/templates')
  const [v, setV] = useState(() => sub ? {
    customer_id: sub.customer_id, plan_id: sub.plan_id, template_id: sub.template_id ?? '', discount_id: sub.discount_id ?? '',
    start_date: sub.start_date, expiry_date: sub.expiry_date, payment_terms_days: sub.payment_terms_days,
    lines: sub.lines.map((l) => ({ product_id: l.product_id, variant_id: l.variant_id ?? '', quantity: l.quantity, unit_price: l.unit_price })),
  } : { customer_id: '', plan_id: '', template_id: '', discount_id: '', start_date: today(), expiry_date: plusYear(), payment_terms_days: 15, lines: [] })
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const set = (k, x) => setV((p) => ({ ...p, [k]: x }))

  const pickTemplate = (id) => {
    const t = templates.find((x) => x.id === Number(id))
    setV((p) => ({ ...p, template_id: id, ...(t ? { plan_id: t.plan_id, lines: t.lines.map((l) => ({ product_id: l.product_id, variant_id: l.variant_id ?? '', quantity: l.quantity })) } : {}) }))
  }

  const save = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    const body = {
      customer_id: Number(v.customer_id), plan_id: v.plan_id ? Number(v.plan_id) : null,
      template_id: v.template_id ? Number(v.template_id) : null, discount_id: v.discount_id ? Number(v.discount_id) : null,
      start_date: v.start_date, expiry_date: v.expiry_date, payment_terms_days: Number(v.payment_terms_days), lines: cleanLines(v.lines),
    }
    try { const r = await api(sub ? `/subscriptions/${sub.id}` : '/subscriptions', { method: sub ? 'PUT' : 'POST', body }); onSaved(r) }
    catch (x) { setErr(x.message); setBusy(false) }
  }

  return (
    <Modal title={sub ? `Edit ${sub.number}` : 'New subscription'} onClose={onClose} wide>
      <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2"><Notice>{err}</Notice></div>
        <Field label="Customer"><OptionSelect from="/people?group=customer" labelKey={who} blank="Choose a customer" required value={v.customer_id} onChange={(x) => set('customer_id', x)} /></Field>
        <Field label="Start from template" hint="Fills in the plan and product lines."><select className={inputCls} value={v.template_id} onChange={(e) => pickTemplate(e.target.value)}>
          <option value="">No template</option>{templates.filter((t) => t.active).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field>
        <Field label="Plan"><OptionSelect from="/plans" blank="Choose a plan" required value={v.plan_id} onChange={(x) => set('plan_id', x)} labelKey={(p) => `${p.name} (${p.billing_period})${p.status !== 'active' ? ` – ${p.status}` : ''}`} /></Field>
        <Field label="Discount" hint="Applied automatically to each invoice while it's valid."><OptionSelect from="/discounts" blank="No discount" value={v.discount_id} onChange={(x) => set('discount_id', x)} /></Field>
        <Field label="Start date"><input className={inputCls} type="date" required value={v.start_date} onChange={(e) => set('start_date', e.target.value)} /></Field>
        <Field label="Expiry date"><input className={inputCls} type="date" required value={v.expiry_date} onChange={(e) => set('expiry_date', e.target.value)} /></Field>
        <Field label="Payment terms"><select className={inputCls} value={v.payment_terms_days} onChange={(e) => set('payment_terms_days', e.target.value)}>
          {[[0, 'Due on receipt'], [7, 'Net 7'], [15, 'Net 15'], [30, 'Net 30'], [45, 'Net 45'], [60, 'Net 60']].map(([d, l]) => <option key={d} value={d}>{l}</option>)}</select></Field>
        <Field label="Product lines" className="sm:col-span-2" hint="Unit price defaults to the product price plus the variant's fixed amount. Tax comes from the product."><LinesEditor withPrice value={v.lines} onChange={(x) => set('lines', x)} /></Field>
        <div className="flex justify-end gap-2 sm:col-span-2"><Btn onClick={onClose}>Cancel</Btn>
          <button disabled={busy} className="rounded-md bg-brand px-3.5 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50">{busy ? 'Saving…' : 'Save draft'}</button></div>
      </form>
    </Modal>
  )
}

function Stepper({ status }) {
  const at = STAGES.indexOf(status)
  return (
    <ol className="mb-5 flex flex-wrap gap-1.5 text-sm" aria-label="Subscription stage">
      {STAGES.map((s, i) => (
        <li key={s} aria-current={i === at ? 'step' : undefined}
            className={`rounded-md px-3 py-1.5 capitalize ${i === at ? 'bg-brand font-medium text-white' : i < at ? 'bg-brand-tint text-brand-dark' : 'border border-line text-mute'}`}>{s}</li>
      ))}
    </ol>
  )
}

function SubDetail({ id, onClose, onChange }) {
  const [sub, setSub] = useState(null); const [invs, setInvs] = useState([])
  const [err, setErr] = useState(''); const [edit, setEdit] = useState(false); const [openInv, setOpenInv] = useState(null)
  const load = useCallback(async () => {
    try { setSub(await api(`/subscriptions/${id}`)); setInvs((await api('/invoices' + qs({ subscription_id: id, limit: 50 }))).items) } catch (e) { setErr(e.message) }
  }, [id])
  useEffect(() => { load() }, [load])
  if (!sub) return <Modal title="Subscription" onClose={onClose}><Notice>{err}</Notice>{!err && <p className="text-sm text-mute">Loading…</p>}</Modal>
  if (edit) return <SubForm sub={sub} onClose={() => setEdit(false)} onSaved={() => { setEdit(false); load(); onChange() }} />

  const move = async () => {
    setErr('')
    if (sub.status === 'active' && !confirm('Close this subscription? No further invoices will be generated.')) return
    try { setSub(await api(`/subscriptions/${id}/transition`, { method: 'POST', body: { to: NEXT[sub.status] } })); onChange() } catch (e) { setErr(e.message) }
  }
  const del = async () => {
    if (!confirm('Delete this draft?')) return
    try { await api(`/subscriptions/${id}`, { method: 'DELETE' }); onChange(); onClose() } catch (e) { setErr(e.message) }
  }
  const total = sub.lines.reduce((a, l) => a + l.amount, 0)

  return (
    <Modal title={sub.number} onClose={onClose} wide>
      <Notice>{err}</Notice>
      <Stepper status={sub.status} />
      <div className="mb-5 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
        <div><span className="text-mute">Customer </span>{sub.customer_name}</div>
        <div><span className="text-mute">Plan </span>{sub.plan_name}</div>
        <div><span className="text-mute">Term </span>{fdate(sub.start_date)} – {fdate(sub.expiry_date)}</div>
        <div><span className="text-mute">Payment terms </span>{sub.payment_terms_days ? `Net ${sub.payment_terms_days}` : 'Due on receipt'}</div>
        {sub.quote_valid_until && sub.status === 'quotation' && <div><span className="text-mute">Quotation valid until </span>{fdate(sub.quote_valid_until)}</div>}
        {sub.next_billing_date && <div><span className="text-mute">Next billing </span>{fdate(sub.next_billing_date)}</div>}
      </div>
      <Table rows={sub.lines} empty="No product lines. The plan price is billed on its own." columns={[
        { label: 'Product', key: 'product_name' }, { label: 'Qty', right: true, key: 'quantity' },
        { label: 'Unit price', right: true, render: (l) => money(l.unit_price) }, { label: 'Tax', right: true, render: (l) => `${l.tax_rate}%` },
        { label: 'Amount', right: true, render: (l) => money(l.amount) }]} />
      {sub.lines.length > 0 && <p className="mt-2 text-right text-sm text-mute">Lines per cycle (before tax and discount): <b className="text-ink">{money(total)}</b></p>}

      {invs.length > 0 && <div className="mt-5"><h3 className="mb-2 text-sm font-semibold">Invoices</h3>
        <Table onRow={(r) => setOpenInv(r.id)} rows={invs} columns={[{ label: 'Number', key: 'number' }, { label: 'Period', render: (r) => `${fdate(r.period_start)} – ${fdate(r.period_end)}` },
          { label: 'Total', right: true, render: (r) => money(r.total) }, { label: 'Status', render: (r) => <Badge status={invStatus(r)} /> }]} /></div>}

      <div className="mt-5 flex flex-wrap justify-end gap-2">
        {sub.status === 'draft' && <><Btn variant="danger" onClick={del}>Delete</Btn><Btn onClick={() => setEdit(true)}>Edit</Btn></>}
        {NEXT[sub.status] && <Btn variant={sub.status === 'active' ? 'danger' : 'primary'} onClick={move}>{NEXT_LABEL[sub.status]}</Btn>}
      </div>
      {openInv && <InvoiceDetail id={openInv} staff onClose={() => setOpenInv(null)} onChange={load} />}
    </Modal>
  )
}

const LIMIT = 25
export default function Subscriptions() {
  const [f, setF] = useState({ status: '', q: '' }); const [offset, setOffset] = useState(0)
  const [data, setData] = useState({ items: [], total: 0 }); const [err, setErr] = useState('')
  const [open, setOpen] = useState(null); const [creating, setCreating] = useState(false)
  const q = useDebounced(f.q)
  const load = useCallback(() => api('/subscriptions' + qs({ status: f.status, q, limit: LIMIT, offset })).then((d) => { setData(d); setErr('') }).catch((e) => setErr(e.message)), [f.status, q, offset])
  useEffect(() => { load() }, [load])
  useEffect(() => { setOffset(0) }, [f.status, q])

  return (
    <div>
      <PageHead title="Subscriptions" sub="Draft → Quotation → Confirmed → Active → Closed"><Btn variant="primary" onClick={() => setCreating(true)}>New subscription</Btn></PageHead>
      <Notice>{err}</Notice>
      <div className="mb-3 flex flex-wrap gap-2">
        <input aria-label="Search" className={`${inputCls} !w-56`} placeholder="Search number or customer" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
        <select aria-label="Stage" className={`${inputCls} !w-40`} value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>
          <option value="">All stages</option>{STAGES.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}</select>
      </div>
      <Table onRow={(r) => setOpen(r.id)} rows={data.items} empty="No subscriptions match these filters." columns={[
        { label: 'Number', render: (r) => <span className="font-medium">{r.number}</span> }, { label: 'Customer', key: 'customer_name' }, { label: 'Plan', key: 'plan_name' },
        { label: 'Term', render: (r) => `${fdate(r.start_date)} – ${fdate(r.expiry_date)}` }, { label: 'Next billing', render: (r) => fdate(r.next_billing_date) },
        { label: 'Stage', render: (r) => <Badge status={r.status} /> }]} />
      <Pager total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
      {creating && <SubForm onClose={() => setCreating(false)} onSaved={(s) => { setCreating(false); load(); setOpen(s.id) }} />}
      {open && <SubDetail id={open} onClose={() => setOpen(null)} onChange={load} />}
    </div>
  )
}
