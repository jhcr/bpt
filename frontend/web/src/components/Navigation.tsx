// Navigation component
import React from 'react';
import { useDispatch } from 'react-redux';
import { useLogoutMutation } from '../store/api';
import { clearAuth } from '../store/authSlice';

export const Navigation: React.FC = () => {
  const dispatch = useDispatch();
  const [logout] = useLogoutMutation();

  const handleLogout = async () => {
    try {
      await logout().unwrap();
      dispatch(clearAuth());
      window.location.href = '/login';
    } catch (error) {
      // Even if logout fails, clear local auth state
      dispatch(clearAuth());
      window.location.href = '/login';
    }
  };

  return (
    <nav className="navigation">
      <div className="nav-brand">
        <h1>Cloud App</h1>
      </div>
      
      <div className="nav-links">
        <a href="/dashboard" className="nav-link">Dashboard</a>
        <a href="/profile" className="nav-link">Profile</a>
        <a href="/settings" className="nav-link">Settings</a>
      </div>
      
      <div className="nav-actions">
        <button onClick={handleLogout} className="logout-btn">
          Logout
        </button>
      </div>
    </nav>
  );
};