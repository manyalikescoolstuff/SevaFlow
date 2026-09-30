import { createBrowserRouter } from 'react-router-dom';

import { RoleSelectPage } from '@/pages/RoleSelect';

import { StaffLayout } from '@/pages/staff/StaffLayout';
import { StaffDashboardPage } from '@/pages/staff/StaffDashboard';
import { LiveStaffPage } from '@/pages/staff/LiveStaff';

import { AdminLayout } from '@/pages/admin/AdminLayout';
import { AdminAccess, LiveAdminPage, AdminDemoNotice } from '@/pages/admin/LiveAdmin';
import { OverviewPage } from '@/pages/admin/Overview';
import { QueuesPage } from '@/pages/admin/Queues';
import { CountersPage } from '@/pages/admin/Counters';
import { AnalyticsPage } from '@/pages/admin/Analytics';
import { LiveAnalyticsPage } from '@/pages/admin/LiveAnalytics';
import { PredictionsPage } from '@/pages/admin/Predictions';
import { LivePredictionsPage } from '@/pages/admin/LivePredictions';

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
    element: <AdminAccess><AdminLayout /></AdminAccess>,
    children: [
      { index: true, element: <LiveAdminPage view="Overview" /> },
      { path: 'queues', element: <LiveAdminPage view="Queues" /> },
      { path: 'counters', element: <LiveAdminPage view="Counters" /> },
      { path: 'analytics', element: <LiveAnalyticsPage /> },
      { path: 'demo/analytics', element: <AdminDemoNotice><AnalyticsPage /></AdminDemoNotice> },
      { path: 'predictions', element: <LivePredictionsPage /> },
      { path: 'demo/predictions', element: <AdminDemoNotice><PredictionsPage /></AdminDemoNotice> },
      { path: 'demo/overview', element: <AdminDemoNotice><OverviewPage /></AdminDemoNotice> },
      { path: 'demo/queues', element: <AdminDemoNotice><QueuesPage /></AdminDemoNotice> },
      { path: 'demo/counters', element: <AdminDemoNotice><CountersPage /></AdminDemoNotice> },
    ],
  },
]);
