import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import Dashboard from './components/dashboard/Dashboard';
import Layout from './components/layout/Layout';

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <div className="min-h-screen bg-gray-50">
          <Dashboard />
        </div>
      </Layout>
    </Router>
  );
};

export default App;