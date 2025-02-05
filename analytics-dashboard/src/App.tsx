import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './components/dashboard/Dashboard';
import UserActivity from './components/analytics/UserActivity';
import Layout from './components/layout/Layout';

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/user-activity" element={<UserActivity />} />
          </Routes>
        </div>
      </Layout>
    </Router>
  );
};

export default App;