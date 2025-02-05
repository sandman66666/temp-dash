import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './components/dashboard/Dashboard';
import AnalyticsDashboard from './components/dashboard/dub_AnalyticsDashboard';
import Layout from './components/layout/Layout';
import Sidebar from './components/layout/dub_Sidebar';

const DubLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 ml-64 bg-gray-50 p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <DubLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/analytics" element={<Dashboard />} />
          <Route path="/user-activity" element={<AnalyticsDashboard />} />
          <Route path="/users" element={<Dashboard />} />
        </Routes>
      </DubLayout>
    </Router>
  );
};

export default App;