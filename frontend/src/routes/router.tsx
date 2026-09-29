import { createBrowserRouter } from 'react-router-dom';

import { RoleSelectPage } from '@/pages/RoleSelect';

import { StaffLayout } from '@/pages/staff/StaffLayout';
import { StaffDashboardPage } from '@/pages/staff/StaffDashboard';
import { LiveStaffPage } from '@/pages/staff/LiveStaff';

import { AdminLayout } from '@/pages/admin/AdminLayout';
import { OverviewPage } from '@/pages/admin/Overview';
import { QueuesPage } from '@/pages/admin/Queues';
import { CountersPage } from '@/pages/admin/Counters';
import { AnalyticsPage } from '@/pages/admin/Analytics';
import { PredictionsPage } from '@/pages/admin/Predictions';

/**
 * Application route definitions.
 *
 *  /              → Role selector (dev/demo only)
 *  /staff         → Staff dashboard (single page)
 *  /admin         → Admin layout with sidebar
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
    element: <StaffLayout />,
    children: [
      { index: true, element: <StaffDashboardPage /> },
    ],
  },
  {
    path: '/admin',
    element: <AdminLayout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: 'queues', element: <QueuesPage /> },
      { path: 'counters', element: <CountersPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
      { path: 'predictions', element: <PredictionsPage /> },
    ],
  },
]);
