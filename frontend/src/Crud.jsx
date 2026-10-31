import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import { Btn, Field, Modal, Notice, PageHead, PasswordRules, Table, bustOptions, inputCls } from './ui'
import { LinesEditor, OptionSelect, VariantsEditor, cleanLines } from './Editors'

function initial(fields, row) {
  const v = {}
  for (const f of fields) {
    const cur = row?.[f.name]
    v[f.name] = cur ?? f.default ?? (f.type === 'checkbox' ? false : f.type === 'variants' || f.type === 'lines' ? [] : '')
  }
  return v
}

function coerce(fields, values) {
  const out = {}
  for (const f of fields) {
    const v = values[f.name]
    if (f.type === 'number') out[f.name] = v === '' || v == null ? (f.required ? 0 : null) : Number(v)
    else if (f.type === 'select' && f.optionsFrom) out[f.name] = v === '' || v == null ? null : Number(v)
    else if (f.type === 'date') out[f.name] = v || null
    else if (f.type === 'variants') out[f.name] = v.filter((x) => x.attribute && x.value).map((x) => ({ ...(x.id ? { id: x.id } : {}), attribute: x.attribute, value: x.value, extra_price: Number(x.extra_price) || 0 }))
    else if (f.type === 'lines') out[f.name] = cleanLines(v)
    else out[f.name] = v
  }
  return out
}

function FieldInput({ f, value, onChange }) {
  const common = { id: f.name, value: value ?? '', required: f.required, disabled: f.disabledOnEdit && f._editing }
  if (f.type === 'checkbox')
    return <input type="checkbox" className="h-4 w-4 accent-brand" checked={!!value} onChange={(e) => onChange(e.target.checked)} />
  if (f.type === 'textarea') return <textarea rows={3} className={inputCls} {...common} onChange={(e) => onChange(e.target.value)} />
  if (f.type === 'select' && f.optionsFrom)
    return <OptionSelect from={f.optionsFrom} labelKey={f.labelKey} blank={f.blank ?? 'None'} value={value} onChange={onChange} required={f.required} />
  if (f.type === 'select')
    return (
      <select className={inputCls} {...common} onChange={(e) => onChange(e.target.value)}>
        {f.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    )
  if (f.type === 'variants') return <VariantsEditor value={value} onChange={onChange} />
  if (f.type === 'lines') return <LinesEditor value={value} onChange={onChange} />
  return (
    <input className={inputCls} type={f.type || 'text'} step={f.type === 'number' ? f.step ?? 'any' : undefined}
           min={f.min} placeholder={f.placeholder} autoComplete={f.type === 'password' ? 'new-password' : undefined}
           {...common} onChange={(e) => onChange(e.target.value)} />
  )
}

export default function Crud({ title, sub, path, columns, fields, actions = [], readOnly, canDelete = true, noun, createOnly, onSaved, updatePath, fixed }) {
  const [rows, setRows] = useState([])
  const [err, setErr] = useState('')
  const [edit, setEdit] = useState(null) // {row|null}
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => api(path).then((r) => { setRows(r); setErr('') }).catch((e) => setErr(e.message)).finally(() => setLoading(false)), [path])
  useEffect(() => { setLoading(true); load() }, [load])

  const remove = async (row) => {
    if (!confirm(`Delete this ${noun || 'item'}? This can't be undone.`)) return
    try { await api(`${path}/${row.id}`, { method: 'DELETE' }); bustOptions(path); load() } catch (e) { setErr(e.message) }
  }

  const cols = [...columns]
  if (!readOnly || actions.length)
    cols.push({
      label: '', right: true,
      render: (r) => (
        <div className="flex justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
          {!readOnly && actions.filter((a) => a.show(r)).map((a) => (
            <Btn key={a.label} small onClick={async () => { try { await a.run(r); bustOptions(path); load() } catch (e) { setErr(e.message) } }}>{a.label}</Btn>
          ))}
          {!readOnly && !createOnly && <Btn small variant="ghost" onClick={() => setEdit({ row: r })}>Edit</Btn>}
          {!readOnly && canDelete && <Btn small variant="danger" onClick={() => remove(r)}>Delete</Btn>}
        </div>
      ),
    })

  return (
    <div>
      <PageHead title={title} sub={sub}>
        {!readOnly && <Btn variant="primary" onClick={() => setEdit({ row: null })}>Add {noun || 'new'}</Btn>}
      </PageHead>
      <Notice>{err}</Notice>
      {loading ? <p className="text-sm text-mute">Loading…</p> : <Table columns={cols} rows={rows} empty={`No ${title.toLowerCase()} yet.`} />}
      {edit && (
        <FormModal title={`${edit.row ? 'Edit' : 'Add'} ${noun || 'item'}`} fields={fields} row={edit.row}
          onClose={() => setEdit(null)}
          onSave={async (values) => {
            const url = edit.row ? `${updatePath ? updatePath(edit.row) : path + '/' + edit.row.id}` : path
            await api(url, { method: edit.row ? 'PUT' : 'POST', body: { ...fixed, ...values } })
            bustOptions(path); onSaved?.(); setEdit(null); load()
          }} />
      )}
    </div>
  )
}

function FormModal({ title, fields, row, onClose, onSave }) {
  const [vals, setVals] = useState(() => initial(fields, row))
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const errRef = useRef(null)
  useEffect(() => { err && errRef.current?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' }) }, [err])
  const visible = fields.filter((f) => !(row && f.createOnly))
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const body = coerce(visible, vals)
      await onSave(body)
    } catch (ex) { setErr(ex.message); setBusy(false) }
  }
  return (
    <Modal title={title} onClose={onClose} wide={fields.some((f) => f.type === 'variants' || f.type === 'lines')}>
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        {visible.map((f) => (
          <Field key={f.name} label={f.label} hint={f.type === 'password' ? <PasswordRules value={vals[f.name]} /> : f.hint} className={f.wide || f.type === 'variants' || f.type === 'lines' || f.type === 'textarea' ? 'sm:col-span-2' : f.type === 'checkbox' ? 'flex items-center gap-2 sm:col-span-1' : ''}>
            {f.type === 'checkbox' ? (
              <span className="flex items-center gap-2"><FieldInput f={f} value={vals[f.name]} onChange={(v) => setVals({ ...vals, [f.name]: v })} /><span className="text-sm text-mute">{f.hint}</span></span>
            ) : (
              <FieldInput f={{ ...f, _editing: !!row }} value={vals[f.name]} onChange={(v) => setVals({ ...vals, [f.name]: v })} />
            )}
          </Field>
        ))}
        <div className="sm:col-span-2">{err && <div ref={errRef}><Notice>{err}</Notice></div>}</div>
        <div className="flex justify-end gap-2 sm:col-span-2">
          <Btn onClick={onClose}>Cancel</Btn>
          <button type="submit" disabled={busy} className="rounded-md bg-brand px-3.5 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50">{busy ? 'Saving…' : 'Save'}</button>
        </div>
      </form>
    </Modal>
  )
}
