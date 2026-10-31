import { api } from '../api'
import Crud from '../Crud'
import { useAuth } from '../auth'
import { Badge, fdate, money } from '../ui'

const yesNo = (v) => (v ? 'Yes' : 'No')
const PERIODS = [['daily', 'Daily'], ['weekly', 'Weekly'], ['monthly', 'Monthly'], ['yearly', 'Yearly']]
const useReadOnly = () => useAuth().user.role !== 'admin'

export function Taxes() {
  return <Crud title="Taxes" noun="tax" path="/taxes" readOnly={useReadOnly()} sub="Rates applied automatically on every invoice line."
    columns={[{ label: 'Name', key: 'name' }, { label: 'Rate', render: (r) => `${r.rate}%` }, { label: 'Active', render: (r) => yesNo(r.active) }]}
    fields={[{ name: 'name', label: 'Name', required: true }, { name: 'rate', label: 'Rate (%)', type: 'number', required: true },
             { name: 'active', label: 'Active', type: 'checkbox', default: true }]} />
}

export function Products() {
  return <Crud title="Products" noun="product" path="/products" readOnly={useReadOnly()}
    sub="Sales and cost prices, with optional variants that add a fixed amount."
    columns={[{ label: 'Name', key: 'name' }, { label: 'Type', key: 'type' },
              { label: 'Sales price', right: true, render: (r) => money(r.sales_price) },
              { label: 'Cost price', right: true, render: (r) => money(r.cost_price) },
              { label: 'Variants', render: (r) => r.variants.map((v) => `${v.value} +${v.extra_price}`).join(', ') || '—' },
              { label: 'Active', render: (r) => yesNo(r.active) }]}
    fields={[{ name: 'name', label: 'Name', required: true },
             { name: 'type', label: 'Type', type: 'select', default: 'service', options: [['service', 'Service'], ['goods', 'Goods'], ['digital', 'Digital']] },
             { name: 'sales_price', label: 'Sales price', type: 'number', required: true, min: 0 },
             { name: 'cost_price', label: 'Cost price', type: 'number', required: true, min: 0 },
             { name: 'default_tax_id', label: 'Default tax', type: 'select', optionsFrom: '/taxes', blank: 'No tax' },
             { name: 'active', label: 'Active', type: 'checkbox', default: true },
             { name: 'notes', label: 'Notes', type: 'textarea' },
             { name: 'variants', label: 'Variants', type: 'variants', hint: 'A variant adds a fixed amount to the price, e.g. Brand: Acme +560.' }]} />
}

export function Plans() {
  const ro = useReadOnly()
  return <Crud title="Plans" noun="plan" path="/plans" readOnly={ro}
    sub="What a plan costs, how often it bills, and how its lifecycle works."
    actions={[
      { label: 'Pause', show: (r) => r.status === 'active' && r.allow_pause, run: (r) => api(`/plans/${r.id}/pause`, { method: 'POST' }) },
      { label: 'Resume', show: (r) => r.status === 'paused', run: (r) => api(`/plans/${r.id}/resume`, { method: 'POST' }) },
      { label: 'Close', show: (r) => r.status !== 'closed', run: (r) => confirm(`Close plan “${r.name}”? It will stop taking new subscriptions.`) && api(`/plans/${r.id}/close`, { method: 'POST' }) },
      { label: 'Renew', show: (r) => r.allow_renew && (r.status === 'closed' || r.available_until), run: async (r) => {
          const d = prompt('Available until (YYYY-MM-DD):', r.available_until || '')
          if (d) await api(`/plans/${r.id}/renew?new_end=${encodeURIComponent(d)}`, { method: 'POST' })
        } },
    ]}
    columns={[{ label: 'Name', key: 'name' },
              { label: 'Price', right: true, render: (r) => money(r.price) },
              { label: 'Billing', render: (r) => <span className="capitalize">{r.billing_period}</span> },
              { label: 'Min qty', right: true, key: 'min_quantity' },
              { label: 'Available', render: (r) => `${fdate(r.available_from)} → ${r.available_until ? fdate(r.available_until) : 'open'}` },
              { label: 'Status', render: (r) => <Badge status={r.status} /> }]}
    fields={[{ name: 'name', label: 'Name', required: true },
             { name: 'price', label: 'Price per period', type: 'number', required: true, min: 0 },
             { name: 'billing_period', label: 'Billing frequency', type: 'select', default: 'monthly', options: PERIODS },
             { name: 'min_quantity', label: 'Minimum quantity', type: 'number', default: 1, min: 1, step: 1, required: true },
             { name: 'available_from', label: 'Available from', type: 'date' },
             { name: 'available_until', label: 'Available until', type: 'date' },
             { name: 'tax_id', label: 'Tax on plan price', type: 'select', optionsFrom: '/taxes', blank: 'No tax' },
             { name: 'auto_close', label: 'Auto-close on end date', type: 'checkbox', hint: 'Closes by itself after “available until”.' },
             { name: 'allow_early_close', label: 'Can be closed early', type: 'checkbox', default: true },
             { name: 'allow_pause', label: 'Can be paused', type: 'checkbox', default: true },
             { name: 'allow_renew', label: 'Can be renewed', type: 'checkbox', default: true }]} />
}

export function Discounts() {
  return <Crud title="Discounts" noun="discount" path="/discounts" readOnly={useReadOnly()}
    sub="Attach a discount to a subscription and it appears on each invoice until its limits run out."
    columns={[{ label: 'Name', key: 'name' },
              { label: 'Value', render: (r) => (r.kind === 'percent' ? `${r.value}%` : money(r.value)) },
              { label: 'Applies to', render: (r) => (r.product_id ? 'One product' : 'Whole subscription') },
              { label: 'Minimums', render: (r) => [r.min_purchase ? `spend ${money(r.min_purchase)}` : '', r.min_quantity ? `qty ${r.min_quantity}` : ''].filter(Boolean).join(', ') || '—' },
              { label: 'Valid', render: (r) => (r.start_date || r.end_date ? `${fdate(r.start_date)} → ${r.end_date ? fdate(r.end_date) : 'open'}` : 'Always') },
              { label: 'Used', right: true, render: (r) => `${r.used_count}${r.usage_limit ? ` / ${r.usage_limit}` : ''}` },
              { label: 'Status', render: (r) => <Badge status={r.active && !(r.usage_limit && r.used_count >= r.usage_limit) ? 'active' : 'closed'}>{r.active && !(r.usage_limit && r.used_count >= r.usage_limit) ? 'Active' : 'Expired'}</Badge> }]}
    fields={[{ name: 'name', label: 'Name', required: true },
             { name: 'kind', label: 'Type', type: 'select', default: 'percent', options: [['percent', 'Percentage'], ['fixed', 'Fixed amount']] },
             { name: 'value', label: 'Value', type: 'number', required: true, min: 0.01 },
             { name: 'product_id', label: 'Applies to', type: 'select', optionsFrom: '/products', blank: 'Entire subscription' },
             { name: 'min_purchase', label: 'Minimum purchase', type: 'number', default: 0, min: 0 },
             { name: 'min_quantity', label: 'Minimum quantity', type: 'number', default: 0, min: 0, step: 1 },
             { name: 'start_date', label: 'Starts', type: 'date' }, { name: 'end_date', label: 'Ends', type: 'date' },
             { name: 'usage_limit', label: 'Usage limit', type: 'number', step: 1, min: 1, hint: 'Number of invoices it can be used on. Blank = unlimited.' },
             { name: 'active', label: 'Active', type: 'checkbox', default: true }]} />
}

export function Templates() {
  return <Crud title="Quotation templates" noun="template" path="/templates" readOnly={useReadOnly()}
    sub="Preset plan and product lines that sales reps can start an offer from."
    columns={[{ label: 'Name', key: 'name' }, { label: 'Lines', right: true, render: (r) => r.lines.length },
              { label: 'Valid for', render: (r) => `${r.validity_days} days` }, { label: 'Active', render: (r) => yesNo(r.active) }]}
    fields={[{ name: 'name', label: 'Name', required: true },
             { name: 'plan_id', label: 'Plan', type: 'select', optionsFrom: '/plans', required: true, blank: 'Choose a plan' },
             { name: 'validity_days', label: 'Quotation valid for (days)', type: 'number', default: 30, step: 1, min: 1, required: true },
             { name: 'active', label: 'Active', type: 'checkbox', default: true },
             { name: 'lines', label: 'Product lines', type: 'lines' }]} />
}

const person = (r) => r.name || '—'
export function Customers() {
  return <Crud title="Customers" noun="customer" path="/people?group=customer" updatePath={(r) => `/people/${r.id}`} canDelete={false}
    fixed={{ role: 'customer' }} sub="Accounts that can sign in to the self-service portal."
    columns={[{ label: 'Name', render: person }, { label: 'Email', key: 'email' }, { label: 'Active', render: (r) => yesNo(r.is_active) }]}
    fields={[{ name: 'name', label: 'Name' }, { name: 'email', label: 'Email', type: 'email', required: true, createOnly: true },
             { name: 'password', label: 'Temporary password', type: 'password', required: true, createOnly: true },
             { name: 'is_active', label: 'Active', type: 'checkbox', default: true }]} />
}

export function Team() {
  return <Crud title="Team" noun="team member" path="/people?group=team" updatePath={(r) => `/people/${r.id}`} canDelete={false}
    sub="Admins have full control. Internal staff run day-to-day operations."
    columns={[{ label: 'Name', render: person }, { label: 'Email', key: 'email' },
              { label: 'Role', render: (r) => <span className="capitalize">{r.role}</span> }, { label: 'Active', render: (r) => yesNo(r.is_active) }]}
    fields={[{ name: 'name', label: 'Name' }, { name: 'email', label: 'Email', type: 'email', required: true, createOnly: true },
             { name: 'role', label: 'Role', type: 'select', default: 'staff', options: [['staff', 'Internal staff'], ['admin', 'Admin']], createOnly: true },
             { name: 'password', label: 'Temporary password', type: 'password', required: true, createOnly: true },
             { name: 'is_active', label: 'Active', type: 'checkbox', default: true }]} />
}
