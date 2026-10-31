import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { LinesEditor, cleanLines } from '../Editors'
import { Badge, Btn, Modal, Notice, PageHead, Table, fdate, money } from '../ui'
import { InvoiceDetail, invStatus } from './Invoices'

const PER = { daily: 'day', weekly: 'week', monthly: 'month', yearly: 'year' }

export default function Portal() {
  const [subs, setSubs] = useState([]); const [invs, setInvs] = useState([]); const [cat, setCat] = useState({ plans: [], products: [] })
  const [err, setErr] = useState(''); const [info, setInfo] = useState('')
  const [open, setOpen] = useState(null); const [req, setReq] = useState(null)

  const load = useCallback(async () => {
    try {
      const [s, i, c] = await Promise.all([api('/portal/subscriptions'), api('/customer-invoices'), api('/portal/catalog')])
      setSubs(s); setInvs(i); setCat(c); setErr('')
    } catch (e) { setErr(e.message) }
  }, [])
  useEffect(() => { load() }, [load])

  const close = async (s) => {
    if (!confirm(`Close ${s.number}? You won't be billed again after this.`)) return
    try { await api(`/portal/subscriptions/${s.id}/close`, { method: 'POST' }); setInfo(`${s.number} is closed.`); load() } catch (e) { setErr(e.message) }
  }
  const send = async () => {
    try {
      const r = await api('/portal/subscriptions', { method: 'POST', body: { plan_id: req.plan.id, lines: cleanLines(req.lines) } })
      setReq(null); setInfo(`Request ${r.number} sent. Our team will confirm it shortly.`); load()
    } catch (e) { setErr(e.message) }
  }
  const owed = invs.reduce((a, i) => a + i.outstanding, 0)

  return (
    <div className="space-y-8">
      <PageHead title="Your account" sub={owed > 0 ? `You have ${money(owed)} outstanding.` : 'You are all paid up.'} />
      <Notice>{err}</Notice><Notice kind="ok">{info}</Notice>

      <section>
        <h2 className="mb-2 text-base font-semibold">Subscriptions</h2>
        <Table rows={subs} empty="No subscriptions yet. Pick a plan below to get started." columns={[
          { label: 'Number', key: 'number' }, { label: 'Plan', key: 'plan_name' },
          { label: 'Term', render: (r) => `${fdate(r.start_date)} – ${fdate(r.expiry_date)}` },
          { label: 'Next billing', render: (r) => fdate(r.next_billing_date) },
          { label: 'Status', render: (r) => <Badge status={r.status} /> },
          { label: '', right: true, render: (r) => r.status === 'active' && <Btn small variant="danger" onClick={() => close(r)}>Close</Btn> }]} />
      </section>

      <section>
        <h2 className="mb-2 text-base font-semibold">Invoices</h2>
        <Table onRow={(r) => setOpen(r.id)} rows={invs} empty="No invoices yet." columns={[
          { label: 'Number', key: 'number' }, { label: 'Period', render: (r) => `${fdate(r.period_start)} – ${fdate(r.period_end)}` },
          { label: 'Due', render: (r) => fdate(r.due_date) }, { label: 'Total', right: true, render: (r) => money(r.total) },
          { label: 'Owed', right: true, render: (r) => (r.outstanding ? money(r.outstanding) : '—') },
          { label: 'Status', render: (r) => <Badge status={invStatus(r)} /> }]} />
      </section>

      <section>
        <h2 className="mb-2 text-base font-semibold">Available plans</h2>
        <Table rows={cat.plans} empty="No plans are open right now." columns={[
          { label: 'Plan', key: 'name' }, { label: 'Price', right: true, render: (r) => `${money(r.price)} / ${PER[r.billing_period]}` },
          { label: 'Minimum quantity', right: true, key: 'min_quantity' },
          { label: '', right: true, render: (r) => <Btn small variant="primary" onClick={() => setReq({ plan: r, lines: [] })}>Request</Btn> }]} />
      </section>

      {open && <InvoiceDetail id={open} onClose={() => setOpen(null)} />}
      {req && (
        <Modal title={`Request ${req.plan.name}`} onClose={() => setReq(null)} wide>
          <p className="mb-3 text-sm text-mute">Add any products you want included. We'll review your request and confirm it with you.</p>
          <LinesEditor products={cat.products} value={req.lines} onChange={(lines) => setReq({ ...req, lines })} />
          <div className="mt-5 flex justify-end gap-2"><Btn onClick={() => setReq(null)}>Cancel</Btn><Btn variant="primary" onClick={send}>Send request</Btn></div>
        </Modal>
      )}
    </div>
  )
}
