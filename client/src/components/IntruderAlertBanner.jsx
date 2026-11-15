import { ShieldAlert, VolumeX, X } from 'lucide-react';
import { useSecurity } from '../context/useSecurity';

export const IntruderAlertBanner = () => {
  const { activeAlert, dismissAlert, isMutedState, toggleMute } = useSecurity();

  if (!activeAlert) return null;

  return (
    <div className="floating-intruder-alert">
      <div className="alert-content-box">
        <div className="alert-flashing-icon">
          <ShieldAlert size={28} />
        </div>

        <div className="alert-text-group">
          <div className="alert-head-line">
            <span className="danger-pill">HIGH ALERT</span>
            <span className="alert-head-title">INTRUDER DETECTED</span>
          </div>
          <div className="alert-details">
            Unauthorized individual identified in <strong>{activeAlert.location}</strong> ({activeAlert.cameraName}) at {activeAlert.timestamp}.
          </div>
          <div className="alert-confidence-tag">
            Deep Learning Model Confidence: <strong>{activeAlert.confidence}%</strong>
          </div>
        </div>

        <div className="alert-actions-group">
          <button
            className="alert-btn mute-btn"
            onClick={toggleMute}
            title={isMutedState ? 'Unmute Siren' : 'Mute Siren'}
            type="button"
          >
            <VolumeX size={16} />
            <span>{isMutedState ? 'Unmuted' : 'Mute Siren'}</span>
          </button>

          <button
            className="alert-btn dismiss-btn"
            onClick={dismissAlert}
            title="Acknowledge and Dismiss Threat"
            type="button"
          >
            <X size={16} />
            <span>Dismiss</span>
          </button>
        </div>
      </div>
    </div>
  );
};
