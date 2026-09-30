import { createBrowserRouter, Navigate } from 'react-router-dom';

import { RoleSelectPage } from '@/pages/RoleSelect';
import { LiveStaffPage } from '@/pages/staff/LiveStaff';

import { AdminLayout } from '@/pages/admin/AdminLayout';
import { AdminAccess, LiveAdminPage } from '@/pages/admin/LiveAdmin';
import { LiveAnalyticsPage } from '@/pages/admin/LiveAnalytics';
import { LivePredictionsPage } from '@/pages/admin/LivePredictions';
import { StaffAllocationsPage } from '@/pages/admin/StaffAllocations';

/**
 * Application route definitions — all routes connect to live backend APIs.
 *
 *  /              → Role selector
 *  /staff         → Staff workstation (Live API)
 *  /admin         → Admin layout with sidebar (Live API)
 *    /admin            → Overview (index)
 *    /admin/queues     → Queues
 *    /admin/counters   → Counters
 *    /admin/analytics  → Analytics
 *    /admin/predictions → Predictions
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <RoleSelectPage />,
  },
  {
    path: '/staff',
    element: <LiveStaffPage />,
  },
  {
    path: '/staff/demo',
    element: <Navigate to="/staff" replace />,
  },
  {
    path: '/admin',
    element: <AdminAccess><AdminLayout /></AdminAccess>,
    children: [
      { index: true, element: <LiveAdminPage view="Overview" /> },
      { path: 'queues', element: <LiveAdminPage view="Queues" /> },
      { path: 'counters', element: <LiveAdminPage view="Counters" /> },
      { path: 'staff-allocation', element: <StaffAllocationsPage /> },
      { path: 'analytics', element: <LiveAnalyticsPage /> },
      { path: 'predictions', element: <LivePredictionsPage /> },
      { path: 'demo/*', element: <Navigate to="/admin" replace /> },
    ],
  },
]);
