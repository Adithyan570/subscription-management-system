import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../src/auth.jsx'
import App from '../src/App.jsx'

async function signIn(user, email = 'admin@example.com', pw = 'Admin@1234') {
  render(<MemoryRouter initialEntries={['/login']}><AuthProvider><App /></AuthProvider></MemoryRouter>)
  await user.type(await screen.findByLabelText('Email'), email)
  await user.type(screen.getByLabelText('Password'), pw)
  await user.click(screen.getByRole('button', { name: 'Sign in' }))
  await screen.findByRole('navigation', { name: 'Main' })
}

const run = Date.now().toString(36)
const em = (n) => `${n}.${run}@example.com`
const cancelIfOpen = async (user) => { const b = screen.queryByRole('button', { name: 'Cancel' }); if (b) await user.click(b) }

async function addPerson(user, link, addBtn, { name, email, pw, role }) {
  await user.click(screen.getByRole('link', { name: link }))
  await user.click(await screen.findByRole('button', { name: addBtn }))
  const dlg = await screen.findByRole('dialog')
  await user.type(within(dlg).getByLabelText('Name'), name)
  await user.type(within(dlg).getByLabelText('Email'), email)
  await user.type(within(dlg).getByLabelText(/Temporary password/), pw)
  if (role) await user.selectOptions(within(dlg).getByLabelText('Role'), role)
  await user.click(within(dlg).getByRole('button', { name: 'Save' }))
  await new Promise((r) => setTimeout(r, 800))
  const open = screen.queryByRole('dialog')
  return { open: !!open, alerts: screen.queryAllByRole('alert').map((a) => a.textContent) }
}

test('all add-user scenarios', async () => {
  const user = userEvent.setup()
  await signIn(user)
  const out = {}
  out.admin = await addPerson(user, 'Team', /Add team member/, { name: 'Ann Admin', email: em('ann'), pw: 'Admin@12345', role: 'admin' })
  out.weak = await addPerson(user, 'Team', /Add team member/, { name: 'Weak', email: em('weak'), pw: 'Staff123' })
  await cancelIfOpen(user)
  out.dup = await addPerson(user, 'Team', /Add team member/, { name: 'Dup', email: em('ann'), pw: 'Admin@12345' })
  await cancelIfOpen(user)
  out.badEmail = await addPerson(user, 'Team', /Add team member/, { name: 'Bad', email: em('bob'), pw: 'Staff@12345' })
  await cancelIfOpen(user)
  out.customer = await addPerson(user, 'Customers', /Add customer/, { name: 'Cora Cust', email: em('cora'), pw: 'Cust@12345' })
  console.log('RESULTS', JSON.stringify(out, null, 1))
  console.log('CUSTOMER LISTED:', !!screen.queryByText(em('cora')))
})
