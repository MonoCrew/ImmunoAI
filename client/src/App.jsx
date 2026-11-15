import { useState } from 'react';
import { SecurityProvider } from './context/SecurityContext';
import { useSecurity } from './context/useSecurity';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { LiveStreamPlayer } from './components/LiveStreamPlayer';
import { SmartControlCard } from './components/SmartControlCard';
import { ProtectionCard } from './components/ProtectionCard';
import { MiniCalendar } from './components/MiniCalendar';
import { ActivitySchedule } from './components/ActivitySchedule';
import { MembersList } from './components/MembersList';
import { CameraThumbnails } from './components/CameraThumbnails';
import { IntruderAlertBanner } from './components/IntruderAlertBanner';
import { WatchStreamView } from './components/WatchStreamView';
import { SettingsView } from './components/SettingsView';
import './App.css';

function DashboardContent() {
  const { smartDevices } = useSecurity();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);

  const toggleTheme = () => {
    setIsDarkMode((prev) => !prev);
  };

  const toggleSidebar = () => {
    setIsSidebarExpanded((prev) => !prev);
  };

  return (
    <div className={`dashboard-wrapper ${isDarkMode ? 'dark-theme' : 'light-theme'}`}>
      {/* Floating Intruder Emergency Alert Toast */}
      <IntruderAlertBanner />

      {/* Main App Container Box */}
      <div className="dashboard-container">
        {/* Left Navigation Sidebar (Expandable / Collapsible) */}
        <Sidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          isExpanded={isSidebarExpanded}
          onToggleExpand={toggleSidebar}
        />

        {/* Right Main Area */}
        <div className="dashboard-main-area">
          {/* Header Bar */}
          <Header
            isDarkMode={isDarkMode}
            onToggleTheme={toggleTheme}
            activeTab={activeTab}
          />

          {/* Conditional View Rendering based on selected tab */}
          {activeTab === 'stream' ? (
            /* Dedicated Watch Stream View */
            <WatchStreamView />
          ) : activeTab === 'settings' ? (
            /* Functional Settings View */
            <SettingsView />
          ) : (
            /* Dashboard View */
            <main className="dashboard-grid">
              {/* Left Big Section (Stream + Bottom Subgrid) */}
              <section className="grid-left-section">
                {/* Live Surveillance Video Player */}
                <LiveStreamPlayer />

                {/* Bottom 3-Card Subgrid */}
                <div className="left-bottom-subgrid">
                  <MiniCalendar />
                  <ActivitySchedule />
                  <MembersList />
                </div>
              </section>

              {/* Right Side Section (Smart Controls + Cameras) */}
              <aside className="grid-right-section">
                {/* 2x4 Device Controls Grid */}
                <div className="devices-grid">
                  {/* Row 1 */}
                  <SmartControlCard deviceKey="frontDoorLock" device={smartDevices.frontDoorLock} />
                  <SmartControlCard deviceKey="backyardSprinklers" device={smartDevices.backyardSprinklers} />

                  {/* Row 2 */}
                  <SmartControlCard deviceKey="garageDoor" device={smartDevices.garageDoor} />
                  <SmartControlCard deviceKey="outdoorLights" device={smartDevices.outdoorLights} />

                  {/* Row 3 */}
                  <SmartControlCard deviceKey="sleepMode" device={smartDevices.sleepMode} />
                  {/* THE CORE CHECK: Protection Mode (Security System) */}
                  <ProtectionCard />

                  {/* Row 4 */}
                  <SmartControlCard deviceKey="internet" device={smartDevices.internet} />
                  <SmartControlCard deviceKey="climate" device={smartDevices.climate} />
                </div>

                {/* Bottom Right: Multi-Camera Gallery */}
                <CameraThumbnails />
              </aside>
            </main>
          )}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <SecurityProvider>
      <DashboardContent />
    </SecurityProvider>
  );
}
