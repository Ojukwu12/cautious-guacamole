import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// We will build these components next
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import DashboardLayout from './components/dashboard/DashboardLayout';
import HostedCheckout from './components/checkout/HostedCheckout';
import './App.css';

function App() {
  // Mock auth check (we will wire this to your JWT later)
  const isAuthenticated = !!localStorage.getItem('vg_access_token');

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
          element={isAuthenticated ? <DashboardLayout /> : <Navigate to="/login" />} 
        />

        {/* Default Redirect */}
        <Route path="*" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} />} />
      </Routes>
    </Router>
  );
}

export default App;