import { ShieldAlert, Volume2, VolumeX, CheckCircle } from 'lucide-react';
import { useSecurity } from '../context/useSecurity';

export const IntruderAlertBanner = () => {
  const { activeAlert, dismissAlert, isMutedState, toggleMute } = useSecurity();

  if (!activeAlert) return null;

  return (
    <aside className="floating-intruder-alert" aria-label="Security Emergency Alert">
      <div className="alert-content-box">
        {/* Sleek Glowing Shield Indicator */}
        <div className="alert-flashing-icon">
          <ShieldAlert size={22} />
        </div>

        {/* Informational Group */}
        <div className="alert-text-group">
          <div className="alert-head-line">
            <span className="danger-pill">HIGH ALERT</span>
            <span className="alert-head-title">INTRUDER CONFIRMED</span>
            <span className="alert-time-tag">{activeAlert.timestamp}</span>
          </div>

          <div className="alert-details">
            Unauthorized individual identified via <strong>{activeAlert.cameraName || 'Attached System Camera'}</strong>.
          </div>

          <div className="alert-meta-chips">
            <span className="alert-chip confidence-chip">
              Confidence: <strong>{activeAlert.confidence}%</strong>
            </span>
            <span className="alert-chip location-chip">
              Zone: <strong>{activeAlert.location || 'Monitored Perimeter'}</strong>
            </span>
          </div>
        </div>

        {/* Quick Response Actions */}
        <div className="alert-actions-group">
          <button
            className={`alert-btn mute-btn ${isMutedState ? 'is-muted' : ''}`}
            onClick={toggleMute}
            title={isMutedState ? 'Unmute Siren Audio' : 'Silence Siren Audio'}
            type="button"
          >
            {isMutedState ? <Volume2 size={14} /> : <VolumeX size={14} />}
            <span>{isMutedState ? 'Unmute' : 'Silence'}</span>
          </button>

          <button
            className="alert-btn dismiss-btn"
            onClick={dismissAlert}
            title="Acknowledge Threat and Dismiss Alert"
            type="button"
          >
            <CheckCircle size={14} />
            <span>Acknowledge</span>
          </button>
        </div>
      </div>
    </aside>
  );
};
