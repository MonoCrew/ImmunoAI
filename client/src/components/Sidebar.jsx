import {
  LayoutGrid,
  Armchair,
  Calendar,
  Video,
  Users,
  SlidersHorizontal,
  Settings,
  LogOut
} from 'lucide-react';
import { useSecurity } from '../context/useSecurity';

export const Sidebar = ({ activeTab = 'dashboard', onSelectTab }) => {
  const { protectionMode } = useSecurity();

  const navItems = [
    { id: 'dashboard', icon: LayoutGrid, label: 'Dashboard' },
    { id: 'rooms', icon: Armchair, label: 'Zones / Rooms' },
    { id: 'calendar', icon: Calendar, label: 'Schedule' },
    { id: 'cameras', icon: Video, label: 'CCTV Feeds' },
    { id: 'members', icon: Users, label: 'Members' },
    { id: 'tuning', icon: SlidersHorizontal, label: 'AI Tuning' },
  ];

  return (
    <aside className="app-sidebar" aria-label="Main Navigation">
      {/* Brand / Logo */}
      <div className="sidebar-logo" title="ImmunoAI — Deep Learning Intruder Detection">
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
      </div>

      {/* Main Navigation Icons */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectTab && onSelectTab(item.id)}
              title={item.label}
              type="button"
            >
              <Icon size={20} strokeWidth={isActive ? 2.4 : 1.8} />
            </button>
          );
        })}
      </nav>

      {/* Bottom Icons */}
      <div className="sidebar-footer">
        <button
          className="nav-btn footer-btn"
          title="System Settings"
          type="button"
          onClick={() => onSelectTab && onSelectTab('settings')}
        >
          <Settings size={20} strokeWidth={1.8} />
        </button>
        <button
          className="nav-btn footer-btn"
          title="Log Out"
          type="button"
          onClick={() => alert('Security Admin Session is Active')}
        >
          <LogOut size={20} strokeWidth={1.8} />
        </button>
      </div>
    </aside>
  );
};
