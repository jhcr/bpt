import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { useGetUserSettingsQuery, useUpdateUserSettingsMutation } from '../store/api';
import { Navigation } from '../components/Navigation';

interface SettingItem {
  category: string;
  data: Record<string, any>;
  version?: number;
}

export const Settings: React.FC = () => {
  const { data: settingsResponse, error, isLoading } = useGetUserSettingsQuery({});
  const [updateSettings] = useUpdateUserSettingsMutation();
  const [localSettings, setLocalSettings] = useState<Record<string, any>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string>('');

  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);

  useEffect(() => {
    if (settingsResponse?.settings) {
      const settingsMap: Record<string, any> = {};
      settingsResponse.settings.forEach((setting: SettingItem) => {
        settingsMap[setting.category] = setting.data;
      });
      setLocalSettings(settingsMap);
    }
  }, [settingsResponse]);

  const handleSettingChange = (category: string, key: string, value: any) => {
    setLocalSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }));
    setHasChanges(true);
    setSaveStatus('');
  };

  const handleSaveSettings = async (category: string) => {
    try {
      setSaveStatus('Saving...');

      const currentSetting = settingsResponse?.settings?.find(
        (s: SettingItem) => s.category === category
      );

      await updateSettings({
        category,
        data: localSettings[category],
        expectedVersion: currentSetting?.version
      }).unwrap();

      setSaveStatus('Saved successfully!');
      setHasChanges(false);

      setTimeout(() => setSaveStatus(''), 3000);
    } catch (error) {
      setSaveStatus('Save failed. Please try again.');
      console.error('Failed to save settings:', error);
    }
  };

  if (!isAuthenticated) {
    return <div>Please log in to view settings.</div>;
  }

  if (isLoading) {
    return (
      <div className="app-container">
        <Navigation />
        <div className="main-content">
          <div className="loading">Loading settings...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-container">
        <Navigation />
        <div className="main-content">
          <div className="error">Failed to load settings: {error.toString()}</div>
        </div>
      </div>
    );
  }

  const renderSettingInput = (category: string, key: string, value: any) => {
    if (typeof value === 'boolean') {
      return (
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={value}
            onChange={(e) => handleSettingChange(category, key, e.target.checked)}
          />
          <span className="checkmark"></span>
          {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
        </label>
      );
    }

    if (typeof value === 'number') {
      return (
        <div className="input-group">
          <label>{key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}</label>
          <input
            type="number"
            value={value}
            onChange={(e) => handleSettingChange(category, key, Number(e.target.value))}
          />
        </div>
      );
    }

    return (
      <div className="input-group">
        <label>{key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}</label>
        <input
          type="text"
          value={value?.toString() || ''}
          onChange={(e) => handleSettingChange(category, key, e.target.value)}
        />
      </div>
    );
  };

  return (
    <div className="app-container">
      <Navigation />
      <div className="main-content">
        <div className="page-header">
          <h1>Settings</h1>
          {hasChanges && (
            <div className="changes-indicator">
              You have unsaved changes
            </div>
          )}
          {saveStatus && (
            <div className={`save-status ${saveStatus.includes('failed') ? 'error' : 'success'}`}>
              {saveStatus}
            </div>
          )}
        </div>

        <div className="settings-container">
          {settingsResponse?.settings?.length === 0 ? (
            <div className="empty-state">
              <p>No settings found. Settings will appear here as you configure your preferences.</p>
            </div>
          ) : (
            settingsResponse?.settings?.map((setting: SettingItem) => (
              <div key={setting.category} className="setting-category">
                <div className="category-header">
                  <h3>{setting.category.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}</h3>
                  <button
                    className="save-button"
                    onClick={() => handleSaveSettings(setting.category)}
                    disabled={!hasChanges}
                  >
                    Save {setting.category}
                  </button>
                </div>

                <div className="setting-fields">
                  {Object.entries(localSettings[setting.category] || {}).map(([key, value]) => (
                    <div key={key} className="setting-field">
                      {renderSettingInput(setting.category, key, value)}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}

          {/* Add new setting category form */}
          <div className="setting-category">
            <div className="category-header">
              <h3>Add New Setting Category</h3>
            </div>
            <div className="add-category-form">
              <p>New settings can be added programmatically through the API or appear here when created by other parts of the application.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};