import React from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { useGetCurrentUserQuery } from '../store/api';
import { Navigation } from '../components/Navigation';

export const UserProfile: React.FC = () => {
  const { data: user, error, isLoading } = useGetCurrentUserQuery();
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);

  if (!isAuthenticated) {
    return <div>Please log in to view your profile.</div>;
  }

  if (isLoading) {
    return (
      <div className="app-container">
        <Navigation />
        <div className="main-content">
          <div className="loading">Loading profile...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-container">
        <Navigation />
        <div className="main-content">
          <div className="error">Failed to load profile: {error.toString()}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <Navigation />
      <div className="main-content">
        <div className="page-header">
          <h1>User Profile</h1>
        </div>

        <div className="profile-container">
          <div className="profile-card">
            <div className="profile-avatar">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="Profile" />
              ) : (
                <div className="avatar-placeholder">
                  {user?.display_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
                </div>
              )}
            </div>

            <div className="profile-info">
              <h2>{user?.display_name || 'Anonymous User'}</h2>
              <p className="email">{user?.email}</p>
              <p className="status">
                Status: <span className={user?.is_active ? 'active' : 'inactive'}>
                  {user?.is_active ? 'Active' : 'Inactive'}
                </span>
              </p>
              {user?.created_at && (
                <p className="joined">
                  Member since: {new Date(user.created_at).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>

          <div className="profile-details">
            <h3>Profile Details</h3>
            <div className="detail-grid">
              <div className="detail-item">
                <label>User ID</label>
                <span>{user?.id}</span>
              </div>
              <div className="detail-item">
                <label>Email</label>
                <span>{user?.email}</span>
              </div>
              <div className="detail-item">
                <label>Display Name</label>
                <span>{user?.display_name || 'Not set'}</span>
              </div>
              <div className="detail-item">
                <label>Account Status</label>
                <span>{user?.is_active ? 'Active' : 'Inactive'}</span>
              </div>
              {user?.created_at && (
                <div className="detail-item">
                  <label>Created</label>
                  <span>{new Date(user.created_at).toLocaleString()}</span>
                </div>
              )}
              {user?.updated_at && (
                <div className="detail-item">
                  <label>Last Updated</label>
                  <span>{new Date(user.updated_at).toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};