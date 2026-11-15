import {
  LayoutGrid,
  Video,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { useSecurity } from '../context/useSecurity';

export const Sidebar = ({ activeTab = 'dashboard', onSelectTab, isExpanded, onToggleExpand }) => {
  const { protectionMode } = useSecurity();

  const navItems = [
    { id: 'dashboard', icon: LayoutGrid, label: 'Dashboard' },
    { id: 'stream', icon: Video, label: 'Watch Stream' },
  ];

  return (
    <aside
      className={`app-sidebar ${isExpanded ? 'is-expanded' : 'is-collapsed'}`}
      aria-label="Main Navigation"
    >
      {/* Top: Brand Logo + Collapse / Expand Toggle */}
      <div className="sidebar-top-header">
        <div
          className="sidebar-brand-box"
          onClick={() => onSelectTab && onSelectTab('dashboard')}
          role="button"
          tabIndex={0}
          title="ImmunoAI Dashboard"
        >
          <div className={`logo-ring ${protectionMode ? 'armed' : ''}`}>
            <img
              src="/logo/cropped_logo.png"
              alt="ImmunoAI"
              className="brand-logo-img"
              onError={(e) => {
                e.currentTarget.onerror = null;
                e.currentTarget.src = '/favicon-96x96.png';
              }}
            />
          </div>
          {isExpanded && (
            <div className="sidebar-brand-text">
              <span className="sidebar-brand-title">ImmunoAI</span>
              <span className="sidebar-brand-sub">Intruder Defense</span>
            </div>
          )}
        </div>

        {/* Toggle Collapse Button */}
        <button
          className="sidebar-collapse-btn"
          onClick={onToggleExpand}
          title={isExpanded ? 'Collapse Sidebar' : 'Expand Sidebar'}
          type="button"
          aria-label={isExpanded ? 'Collapse Sidebar' : 'Expand Sidebar'}
        >
          {isExpanded ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>
      </div>

      {/* Main Navigation Items (Only Dashboard & Watch Stream) */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-btn ${isActive ? 'active' : ''} ${isExpanded ? 'expanded-btn' : ''}`}
              onClick={() => onSelectTab && onSelectTab(item.id)}
              title={!isExpanded ? item.label : undefined}
              type="button"
            >
              <Icon size={20} strokeWidth={isActive ? 2.4 : 1.8} className="nav-icon" />
              {isExpanded && <span className="nav-label">{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Footer Navigation (Settings & Logout) */}
      <div className="sidebar-footer">
        <button
          className={`nav-btn footer-btn ${activeTab === 'settings' ? 'active' : ''} ${
            isExpanded ? 'expanded-btn' : ''
          }`}
          title={!isExpanded ? 'Settings' : undefined}
          type="button"
          onClick={() => onSelectTab && onSelectTab('settings')}
        >
          <Settings size={20} strokeWidth={1.8} className="nav-icon" />
          {isExpanded && <span className="nav-label">Settings</span>}
        </button>

        <button
          className={`nav-btn footer-btn logout-btn ${isExpanded ? 'expanded-btn' : ''}`}
          title={!isExpanded ? 'Log Out' : undefined}
          type="button"
          onClick={() => alert('Security Admin Session is Active')}
        >
          <LogOut size={20} strokeWidth={1.8} className="nav-icon" />
          {isExpanded && <span className="nav-label">Log Out</span>}
        </button>
      </div>
    </aside>
  );
};
