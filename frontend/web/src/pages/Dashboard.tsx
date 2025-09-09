// Dashboard page component
import React from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { useGetCurrentUserQuery } from '../store/api';
import { Navigation } from '../components/Navigation';

export const Dashboard: React.FC = () => {
  const { accessToken } = useSelector((state: RootState) => state.auth);
  const { data: user, isLoading, error } = useGetCurrentUserQuery();

  if (isLoading) {
    return (
      <div className="dashboard">
        <Navigation />
        <div className="dashboard-content">
          <div className="loading">Loading your dashboard...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard">
        <Navigation />
        <div className="dashboard-content">
          <div className="error">Failed to load dashboard data</div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <Navigation />
      <div className="dashboard-content">
        <header className="dashboard-header">
          <h1>Welcome back{user?.display_name ? `, ${user.display_name}` : ''}!</h1>
          <p className="dashboard-subtitle">
            Here's what's happening with your account
          </p>
        </header>

        <div className="dashboard-grid">
          <div className="dashboard-card">
            <h3>Profile Status</h3>
            <div className="profile-summary">
              <div className="profile-avatar">
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt="Profile" />
                ) : (
                  <div className="avatar-placeholder">
                    {user?.display_name?.[0] || user?.email?.[0] || '?'}
                  </div>
                )}
              </div>
              <div className="profile-info">
                <p><strong>{user?.display_name || 'No display name'}</strong></p>
                <p className="email">{user?.email}</p>
                <p className="status">
                  Status: <span className={user?.is_active ? 'active' : 'inactive'}>
                    {user?.is_active ? 'Active' : 'Inactive'}
                  </span>
                </p>
              </div>
            </div>
          </div>

          <div className="dashboard-card">
            <h3>Account Activity</h3>
            <div className="activity-summary">
              <div className="activity-item">
                <span className="activity-label">Created:</span>
                <span className="activity-value">
                  {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown'}
                </span>
              </div>
              <div className="activity-item">
                <span className="activity-label">Last Updated:</span>
                <span className="activity-value">
                  {user?.updated_at ? new Date(user.updated_at).toLocaleDateString() : 'Unknown'}
                </span>
              </div>
            </div>
          </div>

          <div className="dashboard-card">
            <h3>Settings Overview</h3>
            <div className="settings-summary">
              {user?.settings && Object.keys(user.settings).length > 0 ? (
                <div className="settings-preview">
                  <p>You have {Object.keys(user.settings).length} setting categories configured:</p>
                  <ul>
                    {Object.keys(user.settings).map((category) => (
                      <li key={category}>
                        <strong>{category}</strong>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p>No custom settings configured yet.</p>
              )}
              <button 
                className="btn btn-primary"
                onClick={() => window.location.href = '/settings'}
              >
                Manage Settings
              </button>
            </div>
          </div>

          <div className="dashboard-card">
            <h3>Quick Actions</h3>
            <div className="quick-actions">
              <button 
                className="action-btn"
                onClick={() => window.location.href = '/profile'}
              >
                Edit Profile
              </button>
              <button 
                className="action-btn"
                onClick={() => window.location.href = '/settings'}
              >
                Settings
              </button>
              <button className="action-btn" disabled>
                Analytics
              </button>
            </div>
          </div>
        </div>

        <div className="dashboard-footer">
          <p className="debug-info">
            <small>
              Session Token: {accessToken ? `${accessToken.substring(0, 20)}...` : 'None'}
            </small>
          </p>
        </div>
      </div>
    </div>
  );
};