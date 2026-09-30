import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext.jsx';
import Navbar from './components/Navbar.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Placeholder from './pages/Placeholder.jsx';
import ReportDetail from './pages/ReportDetail.jsx';
import History from './pages/History.jsx';

import Admin from './pages/Admin.jsx';

export default function App() {
  return (
    <ThemeProvider>
      <div className="min-h-screen">
        <Navbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/history" element={<History />} />
          <Route path="/admin" element={<Admin />} />
          <Route
            path="/login"
            element={
              <Placeholder
                title="Sign in"
                note="JWT-backed auth form will live here, wired to POST /login and POST /signup."
              />
            }
          />
          <Route path="/report/:id" element={<ReportDetail />} />
        </Routes>
      </div>
    </ThemeProvider>
  );
}
