import React, { useState, useEffect } from 'react';
import PMFDashboard from './PMFDashboard';
import LoginPage from './LoginPage';

/**
 * Main App Component
 *
 * Entry point for the PMF Heat Map Dashboard application
 * Handles authentication and routing
 */
function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('authToken');
    if (token) {
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    setIsAuthenticated(false);
  };

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #052e1c 0%, #0A5C45 55%, #073d2e 100%)',
        color: 'white',
        fontSize: '18px',
        fontFamily: 'DM Sans, sans-serif'
      }}>
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app">
      <PMFDashboard onLogout={handleLogout} />
    </div>
  );
}

export default App;
