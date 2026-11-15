import {
  Lock,
  Unlock,
  Droplets,
  Warehouse,
  Lightbulb,
  Moon,
  Wifi,
  Thermometer,
  ChevronLeft,
  ChevronRight,
  Snowflake
} from 'lucide-react';
import { useSecurity } from '../context/useSecurity';

const DEVICE_ICONS = {
  frontDoorLock: { on: Lock, off: Unlock },
  backyardSprinklers: { on: Droplets, off: Droplets },
  garageDoor: { on: Warehouse, off: Warehouse },
  outdoorLights: { on: Lightbulb, off: Lightbulb },
  sleepMode: { on: Moon, off: Moon },
  internet: { on: Wifi, off: Wifi },
};

export const SmartControlCard = ({ deviceKey, device }) => {
  const { toggleDevice, setClimateTemp } = useSecurity();

  // Climate Control Card (Custom layout matching screenshot)
  if (deviceKey === 'climate') {
    return (
      <div className="smart-card climate-card">
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
  }

  const isActive = device.status;
  const iconConfig = DEVICE_ICONS[deviceKey] || { on: Lightbulb, off: Lightbulb };
  const IconComponent = isActive ? iconConfig.on : iconConfig.off;
  const statusLabel = isActive ? (device.labelActive || 'On') : (device.labelInactive || 'Off');

  return (
    <div
      className={`smart-card ${isActive ? 'is-active' : ''}`}
      onClick={() => toggleDevice(deviceKey)}
      role="button"
      tabIndex={0}
    >
      <div className="card-top-row">
        <div className="card-icon-title">
          <IconComponent size={18} className="card-icon" />
        </div>
        <span className={`status-tag ${isActive ? 'active' : ''}`}>
          {statusLabel}
        </span>
      </div>

      <div className="card-main-info">
        <div className="card-device-name">{device.name}</div>
        <div className="card-subtext">{device.subtext}</div>
      </div>

      {/* Pill Toggle Switch */}
      <div className="card-bottom-toggle">
        <div className={`switch-pill ${isActive ? 'checked' : ''}`}>
          <div className="switch-thumb"></div>
        </div>
      </div>
    </div>
  );
};
