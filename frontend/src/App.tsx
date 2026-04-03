import { Routes, Route, NavLink, useLocation, Outlet } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Users, Calendar, Mail, Upload, Activity, LogOut } from 'lucide-react';
import PatientList from './pages/PatientList';
import PatientDetail from './pages/PatientDetail';
import Schedule from './pages/Schedule';
import Messages from './pages/Messages';
import Import from './pages/Import';
import LearningVisit from './pages/LearningVisit';
import Login from './pages/Login';
import Signup from './pages/Signup';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider, useAuth } from './context/AuthContext';
import { getUnreadCount } from './lib/api';
import { EchoWidget } from '@meded/echo-widget';
import '@meded/echo-widget/styles.css';

/**
 * Main app layout with sidebar navigation.
 */
function AppLayout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    getUnreadCount()
      .then(data => setUnreadCount(data?.unread_count || 0))
      .catch(() => setUnreadCount(0));
  }, [location.pathname]);

  const navItems = [
    { to: '/patients', icon: Users, label: 'Patients' },
    { to: '/schedule', icon: Calendar, label: 'Schedule' },
    { to: '/messages', icon: Mail, label: 'Messages', badge: unreadCount },
    { to: '/import', icon: Upload, label: 'Import' },
  ];

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Sidebar */}
      <aside className="w-64 flex flex-col" style={{ backgroundColor: 'var(--bg-dark)' }}>
        {/* Logo */}
        <div className="h-16 flex items-center px-6" style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <Activity className="w-7 h-7" style={{ color: 'var(--accent-tertiary)' }} />
          <span className="ml-2 text-xl font-display font-semibold" style={{ color: 'var(--text-inverse)' }}>Mneme</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1">
          {navItems.map(({ to, icon: Icon, label, badge }) => (
            <NavLink
              key={to}
              to={to}
              className="flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
              style={({ isActive }) => ({
                backgroundColor: isActive ? 'var(--accent)' : 'transparent',
                color: isActive ? 'var(--text-inverse)' : 'rgba(250,249,247,0.7)',
              })}
            >
              <Icon className="w-5 h-5 mr-3" />
              {label}
              {badge ? (
                <span
                  className="ml-auto text-white text-xs font-bold px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: 'var(--clinical-error)' }}
                >
                  {badge}
                </span>
              ) : null}
            </NavLink>
          ))}
        </nav>

        {/* User & Logout */}
        <div className="p-4" style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          {user && (
            <div className="mb-3 px-3">
              <p className="text-sm font-medium truncate" style={{ color: 'var(--text-inverse)' }}>
                {user.display_name || user.email}
              </p>
              <p className="text-xs capitalize" style={{ color: 'rgba(250,249,247,0.5)' }}>
                {user.role}
              </p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="w-full flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors hover:bg-white/10"
            style={{ color: 'rgba(250,249,247,0.7)' }}
          >
            <LogOut className="w-5 h-5 mr-3" />
            Sign Out
          </button>
          <p className="text-xs text-center font-mono mt-3" style={{ color: 'rgba(250,249,247,0.5)' }}>
            Mneme v0.1.0
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>

      {/* Echo AI Tutor Widget */}
      <EchoWidget
        apiUrl="http://localhost:9102"
        context={{
          source: 'mneme',
        }}
        position="bottom-right"
        theme="system"
      />
    </div>
  );
}

/**
 * Main App component with routing.
 */
function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Protected routes */}
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<PatientList />} />
          <Route path="/patients" element={<PatientList />} />
          <Route path="/patients/:id" element={<PatientDetail />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/messages" element={<Messages />} />
          <Route path="/import" element={<Import />} />
          <Route path="/learning/:sessionId" element={<LearningVisit />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

export default App;
