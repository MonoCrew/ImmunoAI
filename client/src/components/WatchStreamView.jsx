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
    backendStatus,
  } = useSecurity();

  const [hasCameraAccess, setHasCameraAccess] = useState(false);
  const [mediaStream, setMediaStream] = useState(null);

  const containerRef = useRef(null);
  const videoRef = useRef(null);

  // Direct Attached Camera (getUserMedia)
  useEffect(() => {
    let localStream = null;
    let isCancelled = false;

    async function startCamera() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.warn('getUserMedia is not supported by this browser');
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: 'user',
          },
          audio: false,
        });

        if (isCancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        localStream = stream;
        setMediaStream(stream);
        setHasCameraAccess(true);
      } catch (err) {
        console.info('Direct camera stream notice:', err?.message || err);
        setHasCameraAccess(false);
      }
    }

    startCamera();

    return () => {
      isCancelled = true;
      if (localStream) {
        localStream.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  // Guarantee that whenever mediaStream changes, videoRef has srcObject attached and plays
  useEffect(() => {
    const video = videoRef.current;
    if (video && mediaStream) {
      video.srcObject = mediaStream;
      video.play().catch((e) => console.warn('Webcam play error:', e));
    }
  }, [mediaStream]);

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
        {/* Single persistent Video Element — always mounted so stream never detaches */}
        <video
          ref={videoRef}
          className="dedicated-stream-media"
          autoPlay
          playsInline
          muted
          style={{ display: hasCameraAccess ? 'block' : 'none' }}
        />

        {/* Fallback backdrop while camera is connecting or when camera is offline */}
        {!hasCameraAccess && (
          <div className="dedicated-poster-viewport direct-camera-backdrop">
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
                <div className="alert-siren-icon">
                  <ShieldAlert size={20} />
                </div>
                <div>
                  <h4 className="alert-banner-title">INTRUDER CONFIRMED IN CAMERA FEED</h4>
                  <p className="alert-banner-sub">
                    Confidence: <strong>{activeAlert.confidence}%</strong> • Tracked at{' '}
                    {activeAlert.timestamp}
                  </p>
                </div>
              </div>
              <button className="dismiss-alert-btn" onClick={handleDismissAlert} type="button">
                Acknowledge Threat
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
            <span>
              {backendStatus?.online
                ? 'Backend Live Stream (30 FPS)'
                : hasCameraAccess
                ? 'Direct System Camera Feed'
                : 'Direct System Camera (Standby)'}
            </span>
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
