import { Btn, Field, inputCls, useOptions } from './ui'

// product variants: "Brand: Acme (+560)"
export function VariantsEditor({ value = [], onChange }) {
  const set = (i, k, v) => onChange(value.map((x, j) => (j === i ? { ...x, [k]: v } : x)))
  return (
    <div className="space-y-2">
      {value.map((v, i) => (
        <div key={i} className="grid grid-cols-[1fr_1fr_7rem_auto] items-end gap-2">
          <input aria-label="Attribute" className={inputCls} placeholder="Attribute (Brand)" value={v.attribute} onChange={(e) => set(i, 'attribute', e.target.value)} />
          <input aria-label="Value" className={inputCls} placeholder="Value (Acme)" value={v.value} onChange={(e) => set(i, 'value', e.target.value)} />
          <input aria-label="Extra price" type="number" step="0.01" className={inputCls} placeholder="+ amount" value={v.extra_price} onChange={(e) => set(i, 'extra_price', e.target.value)} />
          <Btn small variant="danger" onClick={() => onChange(value.filter((_, j) => j !== i))}>Remove</Btn>
        </div>
      ))}
      <Btn small onClick={() => onChange([...value, { attribute: '', value: '', extra_price: 0 }])}>Add variant</Btn>
    </div>
  )
}

// product lines for templates and subscriptions
export function LinesEditor({ value = [], onChange, withPrice, products: given }) {
  const fetched = useOptions(given ? null : '/products')
  const products = given || fetched
  const set = (i, patch) => onChange(value.map((x, j) => (j === i ? { ...x, ...patch } : x)))
  return (
    <div className="space-y-2">
      {value.map((l, i) => {
        const prod = products.find((p) => p.id === Number(l.product_id))
        return (
          <div key={i} className={`grid items-end gap-2 ${withPrice ? 'grid-cols-[1.4fr_1fr_5rem_6.5rem_auto]' : 'grid-cols-[1.4fr_1fr_5rem_auto]'}`}>
            <select aria-label="Product" className={inputCls} value={l.product_id ?? ''} onChange={(e) => set(i, { product_id: e.target.value, variant_id: '' })}>
              <option value="">Choose product…</option>
              {products.filter((p) => p.active).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <select aria-label="Variant" className={inputCls} disabled={!prod?.variants?.length} value={l.variant_id ?? ''} onChange={(e) => set(i, { variant_id: e.target.value })}>
              <option value="">{prod?.variants?.length ? 'No variant' : '—'}</option>
              {(prod?.variants || []).map((v) => <option key={v.id} value={v.id}>{v.attribute}: {v.value} (+{v.extra_price})</option>)}
            </select>
            <input aria-label="Quantity" type="number" min="1" className={inputCls} value={l.quantity} onChange={(e) => set(i, { quantity: e.target.value })} />
            {withPrice && <input aria-label="Unit price override" type="number" step="0.01" className={inputCls} placeholder="Auto price" value={l.unit_price ?? ''} onChange={(e) => set(i, { unit_price: e.target.value })} />}
            <Btn small variant="danger" onClick={() => onChange(value.filter((_, j) => j !== i))}>Remove</Btn>
          </div>
        )
      })}
      <Btn small onClick={() => onChange([...value, { product_id: '', variant_id: '', quantity: 1 }])}>Add line</Btn>
    </div>
  )
}

export const cleanLines = (lines) =>
  lines.filter((l) => l.product_id).map((l) => ({
    product_id: Number(l.product_id),
    variant_id: l.variant_id ? Number(l.variant_id) : null,
    quantity: Number(l.quantity) || 1,
    ...(l.unit_price !== undefined && l.unit_price !== '' && l.unit_price !== null ? { unit_price: Number(l.unit_price) } : {}),
  }))

export function OptionSelect({ from, labelKey = 'name', blank, value, onChange, ...p }) {
  const opts = useOptions(from)
  return (
    <select className={inputCls} value={value ?? ''} onChange={(e) => onChange(e.target.value)} {...p}>
      {blank !== undefined && <option value="">{blank}</option>}
      {opts.map((o) => <option key={o.id} value={o.id}>{typeof labelKey === 'function' ? labelKey(o) : o[labelKey]}</option>)}
    </select>
  )
}
