import { NavLink, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import { Forgot, Login, Register, Reset } from './pages/Auth'
import { Customers, Discounts, Plans, Products, Taxes, Team, Templates } from './pages/Catalog'
import Dashboard from './pages/Dashboard'
import Invoices from './pages/Invoices'
import Portal from './pages/Portal'
import Subscriptions from './pages/Subscriptions'
import { Btn } from './ui'

const GROUPS = [
  { title: 'Finance', items: [['/dashboard', 'Overview'], ['/subscriptions', 'Subscriptions'], ['/invoices', 'Invoices'], ['/customers', 'Customers']] },
  { title: 'Catalog', items: [['/products', 'Products'], ['/plans', 'Plans'], ['/templates', 'Templates'], ['/discounts', 'Discounts'], ['/taxes', 'Taxes']] },
  { title: 'Admin', admin: true, items: [['/team', 'Team']] },
]

function Layout() {
  const { user, ready, logout } = useAuth()
  if (!ready) return <p className="p-8 text-sm text-mute">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  const staff = user.role !== 'customer'
  const link = ({ isActive }) => `block whitespace-nowrap rounded-md px-3 py-1.5 text-sm ${isActive ? 'bg-brand-tint font-medium text-brand-dark' : 'text-mute hover:bg-wash hover:text-ink'}`
  return (
    <div className="min-h-screen md:flex">
      <aside className="border-b border-line bg-white md:sticky md:top-0 md:h-screen md:w-56 md:shrink-0 md:overflow-y-auto md:border-b-0 md:border-r">
        <div className="flex items-center justify-between px-4 py-3 md:block">
          <p className="text-sm font-semibold text-brand">Subscription Manager</p>
          <p className="hidden text-xs text-mute md:mt-3 md:block">{user.name || user.email}<br /><span className="capitalize">{user.role === 'staff' ? 'internal staff' : user.role}</span></p>
          <Btn small className="md:hidden" onClick={logout}>Sign out</Btn>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-2 pb-2 md:block md:space-y-4 md:px-3 md:pb-4">
          {staff ? GROUPS.filter((g) => !g.admin || user.role === 'admin').map((g) => (
            <div key={g.title} className="flex gap-1 md:block md:space-y-0.5">
              <p className="hidden px-3 pb-1 text-xs font-medium text-mute md:block">{g.title}</p>
              {g.items.map(([to, label]) => <NavLink key={to} to={to} className={link}>{label}</NavLink>)}
            </div>
          )) : <NavLink to="/portal" className={link}>My account</NavLink>}
        </nav>
        <div className="hidden px-3 pb-4 md:block"><Btn small className="w-full" onClick={logout}>Sign out</Btn></div>
      </aside>
      <main className="min-w-0 flex-1 p-4 sm:p-8"><div className="mx-auto max-w-6xl"><Outlet /></div></main>
    </div>
  )
}

const Home = () => { const { user } = useAuth(); return <Navigate to={user?.role === 'customer' ? '/portal' : '/dashboard'} replace /> }
const StaffOnly = ({ children, admin }) => {
  const { user } = useAuth()
  if (user.role === 'customer' || (admin && user.role !== 'admin')) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<Forgot />} />
      <Route path="/reset-password" element={<Reset />} />
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="portal" element={<Portal />} />
        {[['dashboard', Dashboard], ['subscriptions', Subscriptions], ['invoices', Invoices], ['customers', Customers],
          ['products', Products], ['plans', Plans], ['templates', Templates], ['discounts', Discounts], ['taxes', Taxes]].map(([p, C]) => (
          <Route key={p} path={p} element={<StaffOnly><C /></StaffOnly>} />
        ))}
        <Route path="team" element={<StaffOnly admin><Team /></StaffOnly>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
