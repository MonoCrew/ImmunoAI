import { useState } from 'react';
import {
  Sun,
  Moon,
  Bell,
  ShieldCheck,
  ShieldAlert,
  Server,
  ChevronDown
} from 'lucide-react';
import { useSecurity } from '../context/useSecurity';

export const Header = ({ isDarkMode, onToggleTheme, activeTab = 'dashboard' }) => {
  const {
    protectionMode,
    backendStatus,
    notifications,
  } = useSecurity();

  const [showNotifications, setShowNotifications] = useState(false);

  const getPageTitle = () => {
    switch (activeTab) {
      case 'stream':
        return 'Live Surveillance Feed';
      case 'settings':
        return 'System Configuration';
      default:
        return 'Overview & Control Center';
    }
  };

  return (
    <header className="app-header">
      {/* Left: Brand Identity & Active Section */}
      <div className="header-left-group">
        <div className="header-brand-badge" title="ImmunoAI Deep Learning Intruder Detection">
          <img
            src="/logo/cropped_logo.png"
            alt="ImmunoAI"
            className="brand-badge-img"
            onError={(e) => {
              e.currentTarget.onerror = null;
              e.currentTarget.src = '/favicon-96x96.png';
            }}
          />
          <div className="brand-badge-text">
            <span className="brand-badge-name">ImmunoAI</span>
            <span className="brand-badge-subtitle">{getPageTitle()}</span>
          </div>
        </div>
      </div>

      {/* Center: Protection Status Banner */}
      <div className="header-status-pill">
        {protectionMode ? (
          <div className="status-badge armed">
            <span className="status-dot pulsing red"></span>
            <ShieldAlert size={15} />
            <span className="status-text">PROTECTION ARMED — AI INTRUDER SURVEILLANCE ACTIVE</span>
          </div>
        ) : (
          <div className="status-badge standby">
            <span className="status-dot gray"></span>
            <ShieldCheck size={15} />
            <span className="status-text">SYSTEM STANDBY — PROTECTION OFF</span>
          </div>
        )}
      </div>

      {/* Right: Controls & Profile */}
      <div className="header-right">
        {/* Backend Connectivity Status */}
        <div
          className={`backend-pill ${backendStatus.online ? 'online' : 'simulated'}`}
          title={backendStatus.online ? `Connected to ${backendStatus.url}` : 'Using local AI simulation fallback'}
        >
          <Server size={14} />
          <span>{backendStatus.online ? 'Backend Live' : 'AI Simulation'}</span>
        </div>

        {/* Theme Toggle Pill (Sun / Moon) */}
        <div className="theme-toggle-pill" onClick={onToggleTheme} role="button" tabIndex={0}>
          <button className={`theme-btn ${!isDarkMode ? 'active' : ''}`} title="Light Mode">
            <Sun size={15} />
          </button>
          <button className={`theme-btn ${isDarkMode ? 'active' : ''}`} title="Dark Mode">
            <Moon size={15} />
          </button>
        </div>

        {/* Notification Bell */}
        <div className="notification-wrapper">
          <button
            className={`icon-btn ${notifications.length > 0 ? 'has-badge' : ''}`}
            onClick={() => setShowNotifications(!showNotifications)}
            title="Intruder Notifications"
            type="button"
          >
            <Bell size={18} />
            {notifications.length > 0 && (
              <span className="notification-badge">{notifications.length}</span>
            )}
          </button>

          {showNotifications && (
            <div className="dropdown-menu notification-dropdown">
              <div className="notification-header">
                <h4>Surveillance Alerts</h4>
                {notifications.length > 0 && (
                  <span className="badge-count">{notifications.length} new</span>
                )}
              </div>
              <div className="notification-list">
                {notifications.length === 0 ? (
                  <div className="empty-notifications">
                    <ShieldCheck size={28} />
                    <p>No intruder threats detected</p>
                    <small>System is monitoring perimeter</small>
                  </div>
                ) : (
                  notifications.map((notif, idx) => (
                    <div key={notif.id || idx} className="notification-item alert">
                      <div className="notif-icon">🚨</div>
                      <div className="notif-content">
                        <div className="notif-title">Intruder Detected</div>
                        <div className="notif-desc">
                          {notif.cameraName || 'Camera 01'} • {notif.location || 'Perimeter'}
                        </div>
                        <div className="notif-meta">
                          <span>{notif.timestamp}</span>
                          <span className="conf-pill">{notif.confidence}% Confidence</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Profile */}
        <div className="user-profile">
          <img
            src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=80&auto=format&fit=crop&q=80"
            alt="Lorell Morales"
            className="user-avatar"
          />
          <span className="user-name">Lorell Morales</span>
          <ChevronDown size={14} className="user-arrow" />
        </div>
      </div>
    </header>
  );
};
