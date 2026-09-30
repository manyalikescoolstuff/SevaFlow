import { NavLink } from 'react-router-dom';
import './AdminSidebar.css';

const NAV_ITEMS = [
  { to: '/admin',            label: 'Overview' },
  { to: '/admin/queues',     label: 'Queues' },
  { to: '/admin/counters',   label: 'Counters' },
  { to: '/admin/staff-allocation', label: 'Staff allocation' },
  { to: '/admin/analytics',  label: 'Analytics' },
  { to: '/admin/predictions', label: 'Predictions' },
];

export function AdminSidebar() {
  return (
    <aside className="admin-sidebar">
      <nav className="admin-sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/admin'}
            className={({ isActive }) =>
              `admin-sidebar__link${isActive ? ' admin-sidebar__link--active' : ''}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
