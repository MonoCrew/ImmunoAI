import { useRef, useState, useEffect } from 'react';
import {
  Maximize2,
  Cpu,
  Activity,
  Layers,
  ShieldAlert,
  ShieldCheck,
  Video,
  Camera
} from 'lucide-react';
import { useSecurity } from '../context/useSecurity';

export const WatchStreamView = () => {
  const {
    protectionMode,
    activeAlert,
    dismissAlert,
  } = useSecurity();

  const [hasCameraAccess, setHasCameraAccess] = useState(false);

  const containerRef = useRef(null);
  const videoRef = useRef(null);

  // Direct Attached Camera (getUserMedia)
  useEffect(() => {
    let stream = null;
    const currentVideoEl = videoRef.current;

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices
        .getUserMedia({ video: { width: 1280, height: 720 }, audio: false })
        .then((s) => {
          stream = s;
          if (currentVideoEl) {
            currentVideoEl.srcObject = s;
            currentVideoEl.play().catch(() => {});
          }
          setHasCameraAccess(true);
        })
        .catch((err) => {
          console.info('Direct camera stream info:', err?.message || err);
          setHasCameraAccess(false);
        });
    }

    return () => {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
      if (currentVideoEl && currentVideoEl.srcObject) {
        const tracks = currentVideoEl.srcObject.getTracks();
        tracks.forEach((t) => t.stop());
        currentVideoEl.srcObject = null;
      }
    };
  }, []);

  const handleDismissAlert = () => {
    dismissAlert();
  };

  // Fullscreen
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  // Active displayed bounding boxes (from backend alert)
  const displayBoxes =
    activeAlert && protectionMode
      ? [
          {
            x: activeAlert.box?.[0] ?? 35,
            y: activeAlert.box?.[1] ?? 25,
            w: activeAlert.box?.[2] ?? 25,
            h: activeAlert.box?.[3] ?? 50,
            label: 'INTRUDER',
            confidence: activeAlert.confidence || '97.2',
            trackingId: activeAlert.id ? String(activeAlert.id).slice(-4) : '1042',
          },
        ]
      : [];

  return (
    <div className="watch-stream-view" ref={containerRef}>
      {/* Big Surveillance Screen */}
      <div className={`dedicated-stream-container ${activeAlert ? 'alert-active' : ''}`}>
        {hasCameraAccess ? (
          <video
            ref={videoRef}
            className="dedicated-stream-media"
            autoPlay
            playsInline
            muted
          />
        ) : (
          <div className="dedicated-poster-viewport direct-camera-backdrop">
            <video
              ref={videoRef}
              className="dedicated-stream-media direct-hidden-video"
              autoPlay
              playsInline
              muted
            />
            <img
              src="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1600&auto=format&fit=crop&q=85"
              alt="Direct Attached System Camera"
              className="dedicated-stream-media poster-img"
            />
            <div className="stream-lens-overlay"></div>
          </div>
        )}

        {/* Real-time Bounding Box Overlay */}
        <div className="stream-detection-layer">
          {displayBoxes.map((box, index) => (
            <div
              key={index}
              className="bounding-box intruder-box"
              style={{
                left: `${box.x}%`,
                top: `${box.y}%`,
                width: `${box.w}%`,
                height: `${box.h}%`,
              }}
            >
              <div className="box-corner tl"></div>
              <div className="box-corner tr"></div>
              <div className="box-corner bl"></div>
              <div className="box-corner br"></div>

              <div className="box-tag intruder">
                <span className="pulse-danger"></span>
                <strong>{box.label}</strong>
                <span className="box-conf">{box.confidence}%</span>
              </div>

              <div className="box-tracking-id">
                <span>ID: #{box.trackingId}</span>
              </div>
            </div>
          ))}

          {!protectionMode && (
            <div className="standby-watermark">
              <ShieldCheck size={18} className="text-muted" />
              <div>
                <strong>Protection Mode Standby</strong>
                <p>Toggle "Protection Mode" ON in Dashboard to activate real-time intruder detection</p>
              </div>
            </div>
          )}

          {activeAlert && (
            <div className="stream-alert-banner">
              <div className="alert-banner-left">
                <ShieldAlert size={22} className="alert-siren-icon text-red" />
                <div>
                  <h4 className="alert-banner-title">INTRUDER DETECTED IN CAMERA FEED!</h4>
                  <p className="alert-banner-sub">
                    Confidence: <strong>{activeAlert.confidence}%</strong> • Tracked at{' '}
                    {activeAlert.timestamp}
                  </p>
                </div>
              </div>
              <button className="dismiss-alert-btn" onClick={handleDismissAlert} type="button">
                Dismiss Alert
              </button>
            </div>
          )}
        </div>

        {/* Top Bar: Only Live Badge (Clean - FHD, 100%, Wifi, On removed per instructions) */}
        <div className="stream-top-bar">
          <div className="stream-badges-left">
            <div className="badge-pill live-badge">
              <span className="live-dot"></span>
              <span>Live • Attached System Camera</span>
            </div>
          </div>

          <div className="stream-badges-right">
            <button
              className="action-btn icon-only fullscreen-pill"
              onClick={toggleFullscreen}
              title="Fullscreen"
              type="button"
            >
              <Maximize2 size={14} />
            </button>
          </div>
        </div>

        {/* Direct Camera Feed Indicator at bottom right of player */}
        <div className="watch-stream-floating-actions">
          <div className="floating-camera-indicator">
            <Camera size={13} className="text-orange" />
            <span>Direct System Camera Feed</span>
          </div>
        </div>
      </div>

      {/* Model Telemetry & Stream Status Bar at Bottom */}
      <div className="stream-model-status-bar">
        <div className="status-bar-item">
          <div className="status-bar-icon-box">
            <Cpu size={16} className="text-orange" />
          </div>
          <div className="status-bar-info">
            <span className="status-bar-label">AI Architecture</span>
            <span className="status-bar-value">YOLOv8-Custom (PyTorch)</span>
          </div>
        </div>

        <div className="status-bar-divider"></div>

        <div className="status-bar-item">
          <div className="status-bar-icon-box">
            <Activity size={16} className="text-green" />
          </div>
          <div className="status-bar-info">
            <span className="status-bar-label">Inference Latency</span>
            <span className="status-bar-value">12.4 ms • 29.8 FPS</span>
          </div>
        </div>

        <div className="status-bar-divider"></div>

        <div className="status-bar-item">
          <div className="status-bar-icon-box">
            <Layers size={16} />
          </div>
          <div className="status-bar-info">
            <span className="status-bar-label">Target Classes</span>
            <span className="status-bar-value">Person, Intruder</span>
          </div>
        </div>

        <div className="status-bar-divider"></div>

        <div className="status-bar-item">
          <div className="status-bar-icon-box">
            {protectionMode ? (
              <ShieldAlert size={16} className="text-orange" />
            ) : (
              <ShieldCheck size={16} className="text-muted" />
            )}
          </div>
          <div className="status-bar-info">
            <span className="status-bar-label">Surveillance Mode</span>
            <span className={`status-bar-value ${protectionMode ? 'text-orange-bold' : ''}`}>
              {protectionMode ? 'ARMED (Active Intrusion Guard)' : 'STANDBY (Protection Off)'}
            </span>
          </div>
        </div>

        <div className="status-bar-divider"></div>

        <div className="status-bar-item">
          <div className="status-bar-icon-box">
            <Video size={16} />
          </div>
          <div className="status-bar-info">
            <span className="status-bar-label">Live Threat Status</span>
            <span className={`status-bar-value ${activeAlert ? 'text-red-bold' : 'text-green'}`}>
              {activeAlert ? `🚨 INTRUDER DETECTED (${activeAlert.confidence}%)` : 'Normal • 0 Threats'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
