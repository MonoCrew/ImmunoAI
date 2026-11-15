import {
  Volume2,
  VolumeX,
  Wifi,
  Activity,
  Thermometer,
  ChevronLeft,
  ChevronRight,
  Snowflake,
  CheckCircle2
} from 'lucide-react';
import { useSecurity } from '../context/useSecurity';

// Card 2: Sound (Alarm siren toggle)
export const SoundCard = () => {
  const { isMutedState, toggleMute } = useSecurity();
  const isSoundOn = !isMutedState;

  return (
    <div
      className={`smart-card ${isSoundOn ? 'is-active' : ''}`}
      onClick={toggleMute}
      role="button"
      tabIndex={0}
      title="Toggle Alarm Siren Audio Alerts"
    >
      <div className="card-top-row">
        <div className="card-icon-title">
          {isSoundOn ? (
            <Volume2 size={18} className="card-icon text-orange" />
          ) : (
            <VolumeX size={18} className="card-icon text-muted" />
          )}
        </div>
        <span className={`status-tag ${isSoundOn ? 'active' : ''}`}>
          {isSoundOn ? 'On' : 'Mute'}
        </span>
      </div>

      <div className="card-main-info">
        <div className="card-device-name">Alarm Sound</div>
        <div className="card-subtext">
          {isSoundOn ? 'Siren alerts active on breach' : 'Audio alarm silenced'}
        </div>
      </div>

      {/* Pill Toggle Switch */}
      <div className="card-bottom-toggle">
        <div className={`switch-pill ${isSoundOn ? 'checked' : ''}`}>
          <div className="switch-thumb"></div>
        </div>
      </div>
    </div>
  );
};

// Card 3: Wi-Fi Status (Static display - NO BUTTON per user requirement)
export const WifiStatusCard = () => {
  return (
    <div className="smart-card static-info-card" title="Wi-Fi Connection Status (Telemetry Only)">
      <div className="card-top-row">
        <div className="card-icon-title">
          <Wifi size={18} className="card-icon text-green" />
        </div>
        <span className="status-tag active flex-center gap-1">
          <CheckCircle2 size={11} />
          <span>Connected</span>
        </span>
      </div>

      <div className="card-main-info">
        <div className="card-device-name">Wi-Fi Status</div>
        <div className="card-subtext">ImmunoNet-5GHz (Strong)</div>
      </div>

      {/* Static Visual Indicator - NO BUTTON */}
      <div className="card-bottom-static-indicator">
        <div className="signal-bars-indicator">
          <span className="sig-bar bar-1 active"></span>
          <span className="sig-bar bar-2 active"></span>
          <span className="sig-bar bar-3 active"></span>
          <span className="sig-bar bar-4 active"></span>
        </div>
        <span className="static-pill-badge">-42 dBm • Optimal</span>
      </div>
    </div>
  );
};

// Card 4: Wi-Fi Speed (Telemetry telemetry display)
export const WifiSpeedCard = () => {
  return (
    <div className="smart-card static-info-card" title="Real-Time Network Bandwidth for Video Stream">
      <div className="card-top-row">
        <div className="card-icon-title">
          <Activity size={18} className="card-icon text-orange" />
        </div>
        <span className="status-tag active">120 Mbps</span>
      </div>

      <div className="card-main-info">
        <div className="card-device-name">Wi-Fi Speed</div>
        <div className="card-subtext">Latency: 14ms • Low Jitter</div>
      </div>

      {/* Speed Data Metric */}
      <div className="card-bottom-telemetry">
        <span className="speed-pill download">↓ 120.4 Mbps</span>
        <span className="speed-pill upload">↑ 42.1 Mbps</span>
      </div>
    </div>
  );
};

// Card 5: Temperature (Climate Control)
export const ClimateControlCard = () => {
  const { smartDevices, setClimateTemp } = useSecurity();
  const device = smartDevices.climate || { temp: 24, status: true, mode: 'Cold', autoTurnOn: '20:00 PM', autoTurnOff: '18:00 PM' };

  return (
    <div className="smart-card climate-card climate-card-wide">
      <div className="card-top-row">
        <div className="card-icon-title">
          <Thermometer size={18} className="card-icon" />
        </div>
        <span className={`status-tag ${device.status ? 'active' : ''}`}>
          {device.status ? 'On' : 'Off'}
        </span>
      </div>

      <div className="card-device-name">Climate Control</div>

      {/* Center Temp Display with Chevrons */}
      <div className="climate-temp-picker">
        <button
          className="temp-chevron-btn"
          onClick={() => setClimateTemp(-1)}
          title="Decrease Temperature"
          type="button"
        >
          <ChevronLeft size={16} />
        </button>
        <div className="temp-number">
          <span>{device.temp}</span>
          <span className="temp-unit">°C</span>
        </div>
        <button
          className="temp-chevron-btn"
          onClick={() => setClimateTemp(1)}
          title="Increase Temperature"
          type="button"
        >
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Climate Details Rows */}
      <div className="climate-meta">
        <div className="climate-row">
          <span className="meta-label">Mode</span>
          <span className="meta-val flex-center">
            <span>{device.mode}</span>
            <Snowflake size={12} className="meta-sub-icon" />
          </span>
        </div>
        <div className="climate-row">
          <span className="meta-label">Auto turn on</span>
          <span className="meta-val">{device.autoTurnOn}</span>
        </div>
        <div className="climate-row">
          <span className="meta-label">Auto turn off</span>
          <span className="meta-val">{device.autoTurnOff}</span>
        </div>
      </div>
    </div>
  );
};

// Backward-compatible default export if needed
export const SmartControlCard = ({ deviceKey }) => {
  if (deviceKey === 'climate') {
    return <ClimateControlCard />;
  }
  return null;
};
