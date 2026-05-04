import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/Chat/ChatWindow';
import UploadPanel from './components/Upload/UploadPanel';
import AdminDashboard from './components/Dashboard/AdminDashboard';
import LoginPage from './components/Auth/LoginPage';

// --- Protected Route Wrapper ---
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-surface-container-lowest">
      <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin"></div>
    </div>
  );

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Redirect to their default dashboard if they try to access wrong area
    const defaultPaths = {
      admin: '/admin',
      professor: '/professor',
      student: '/student'
    };
    return <Navigate to={defaultPaths[user.role]} replace />;
  }

  return children;
};

// --- Main Layout Wrapper ---
const AppLayout = ({ children }) => {
  const { user } = useAuth();
  
  return (
    <div className="flex bg-surface-container-lowest min-h-screen text-on-surface">
      {/* Ambient Background Lighting */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[40vw] h-[40vw] rounded-full bg-primary/5 blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[10%] w-[30vw] h-[30vw] rounded-full bg-secondary-container/10 blur-[100px]"></div>
        <div className="absolute top-[40%] left-[60%] w-[20vw] h-[20vw] rounded-full bg-tertiary-container/5 blur-[80px]"></div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:48px_48px] opacity-30"></div>
      </div>

      {user && <Sidebar />}
      
      <main className={`flex-1 ${user ? 'md:ml-[300px]' : ''} relative z-10 min-h-screen flex flex-col transition-all duration-300`}>
        {children}
      </main>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Routes */}
          <Route path="/student" element={
            <ProtectedRoute allowedRoles={['student', 'admin']}>
              <AppLayout><ChatWindow /></AppLayout>
            </ProtectedRoute>
          } />
          
          <Route path="/professor" element={
            <ProtectedRoute allowedRoles={['professor', 'admin']}>
              <AppLayout><UploadPanel /></AppLayout>
            </ProtectedRoute>
          } />

          <Route path="/admin" element={
            <ProtectedRoute allowedRoles={['admin']}>
              <AppLayout><AdminDashboard /></AppLayout>
            </ProtectedRoute>
          } />

          {/* Default Redirection Logic */}
          <Route path="/" element={<Navigate to="/student" replace />} />
          <Route path="*" element={<Navigate to="/student" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
