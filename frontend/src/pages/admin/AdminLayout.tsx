import { Outlet } from 'react-router-dom';
import { AppHeader } from '@/components/common/AppHeader';
import { AdminSidebar } from '@/components/common/AdminSidebar';
import './AdminLayout.css';
import { useLiveAdmin } from './LiveAdmin';

/**
 * Layout wrapper for the Admin dashboard.
 * Header on top, sidebar on the left, content area on the right.
 */
export function AdminLayout() {
  const { logout } = useLiveAdmin();
  return (
    <div className="admin-layout">
      <AppHeader contextLabel="Administrator" onExit={logout} />
      <div className="admin-layout__body">
        <AdminSidebar />
        <main className="admin-layout__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
