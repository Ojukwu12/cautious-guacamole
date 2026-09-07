import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// We will build these components next
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import DashboardLayout from './components/dashboard/DashboardLayout';
import HostedCheckout from './components/checkout/HostedCheckout';
import AdminDashboard from './components/admin/AdminDashboard';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => !!localStorage.getItem('vg_access_token')
  );
  const [role, setRole] = useState(() => localStorage.getItem('vg_role') || 'merchant');

  useEffect(() => {
    const syncAuth = () => {
      setIsAuthenticated(!!localStorage.getItem('vg_access_token'));
      setRole(localStorage.getItem('vg_role') || 'merchant');
    };
    window.addEventListener('vg-auth-changed', syncAuth);
    window.addEventListener('storage', syncAuth);
    return () => {
      window.removeEventListener('vg-auth-changed', syncAuth);
      window.removeEventListener('storage', syncAuth);
    };
  }, []);

  return (
    <Router>
      <Routes>
        {/* Public Authentication Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* The Decoupled Customer Checkout Page (External Facing) */}
        <Route path="/pay/:sessionId" element={<HostedCheckout />} />

        {/* Protected Merchant Dashboard Routes */}
        <Route 
          path="/dashboard/*" 
          element={isAuthenticated && role === 'merchant' ? <DashboardLayout /> : <Navigate to={role === 'admin' ? '/admin' : '/login'} />} 
        />
        <Route path="/admin/*" element={isAuthenticated && role === 'admin' ? <AdminDashboard /> : <Navigate to={isAuthenticated ? '/dashboard' : '/login'} />} />

        {/* Default Redirect */}
        <Route path="*" element={<Navigate to={isAuthenticated ? (role === 'admin' ? '/admin' : '/dashboard') : '/login'} />} />
      </Routes>
    </Router>
  );
}

export default App;