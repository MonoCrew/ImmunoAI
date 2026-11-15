import { useRef, useState, useEffect } from 'react';
import {
  Volume2,
  VolumeX,
  Wifi,
  Battery,
  Maximize2,
  AlertTriangle
} from 'lucide-react';
import { useSecurity } from '../context/useSecurity';
import { getCameraStreamUrl } from '../services/api';

// High-resolution architectural backdrops matching the screenshot for each camera
const CAMERA_PREVIEWS = {
  cam1: 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1600&auto=format&fit=crop&q=85', // Luxury modern villa exterior & driveway
  cam2: 'https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?w=1600&auto=format&fit=crop&q=85', // Pool area
  cam3: 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1600&auto=format&fit=crop&q=85', // Patio garden
};

export const LiveStreamPlayer = () => {
  const {
    protectionMode,
    activeCamera,
    activeAlert,
    triggerIntruderAlert,
    dismissAlert,
    isMutedState,
    toggleMute,
    streamSource,
    setStreamSource,
    backendStatus
  } = useSecurity();

  const [resolution, setResolution] = useState('FHD');
  const [showResMenu, setShowResMenu] = useState(false);
  const [simulatedBoxes, setSimulatedBoxes] = useState([]);
  const [uploadedVideoUrl, setUploadedVideoUrl] = useState(null);

  const containerRef = useRef(null);
  const videoRef = useRef(null);
  const fileInputRef = useRef(null);

  // Background image based on active camera
  const currentPoster = CAMERA_PREVIEWS[activeCamera.id] || CAMERA_PREVIEWS.cam1;

  // Manual Trigger for Intruder Detection (For Testing / Viva Demos)
  const handleSimulateIntruder = () => {
    if (!protectionMode) {
      alert('Please turn ON "Security System" (Protection Mode) first to detect intruders!');
      return;
    }

    // Set detection bounding box on canvas
    const box = {
      x: 35 + Math.random() * 20,
      y: 28 + Math.random() * 15,
      w: 18 + Math.random() * 10,
      h: 45 + Math.random() * 15,
      label: 'INTRUDER',
      confidence: (94 + Math.random() * 5.8).toFixed(1),
      trackingId: Math.floor(1000 + Math.random() * 9000),
    };
    setSimulatedBoxes([box]);

    triggerIntruderAlert({
      confidence: box.confidence,
      box: [box.x, box.y, box.w, box.h],
    });
  };

  const handleDismissAlert = () => {
    setSimulatedBoxes([]);
    dismissAlert();
  };

  // Handle Webcam streaming
  useEffect(() => {
    let stream = null;
    const currentVideoEl = videoRef.current;

    if (streamSource === 'webcam') {
      navigator.mediaDevices?.getUserMedia({ video: { width: 1280, height: 720 }, audio: false })
        .then((s) => {
          stream = s;
          if (currentVideoEl) {
            currentVideoEl.srcObject = s;
            currentVideoEl.play();
          }
        })
        .catch((err) => {
          console.warn('Webcam access error:', err);
          alert('Could not access webcam. Falling back to simulated stream.');
          setStreamSource('mock');
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
  }, [streamSource, setStreamSource]);

  // Handle Fullscreen
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  // Handle Local Video File Upload for testing
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setUploadedVideoUrl(url);
      setStreamSource('video');
    }
  };

  // Active displayed boxes (only visible when alert is active and protection mode is on)
  const displayBoxes = activeAlert && protectionMode ? simulatedBoxes : [];

  return (
    <div className="stream-card-wrapper" ref={containerRef}>
      {/* Stream Container */}
      <div className={`stream-player-container ${activeAlert ? 'alert-active' : ''}`}>
        {/* Stream Source Render */}
        {streamSource === 'webcam' ? (
          <video
            ref={videoRef}
            className="stream-media"
            autoPlay
            playsInline
            muted
          />
        ) : streamSource === 'video' && uploadedVideoUrl ? (
          <video
            src={uploadedVideoUrl}
            className="stream-media"
            autoPlay
            loop
            muted={isMutedState}
          />
        ) : streamSource === 'backend' && backendStatus.online ? (
          <img
            src={getCameraStreamUrl(activeCamera.id)}
            alt="Backend Camera Stream"
            className="stream-media backend-mjpeg"
            onError={() => {
              alert('Backend stream unavailable. Reverting to Simulated Stream.');
              setStreamSource('mock');
            }}
          />
        ) : (
          /* Simulated High-Res CCTV Feed */
          <div className="stream-poster-viewport">
            <img
              src={currentPoster}
              alt={activeCamera.name}
              className="stream-media poster-img"
            />
            <div className="stream-lens-overlay"></div>
          </div>
        )}

        {/* Real-Time Deep Learning Detection Bounding Box Overlay */}
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

              {/* Tag Header */}
              <div className="box-tag intruder">
                <span className="pulse-danger"></span>
                <strong>{box.label}</strong>
                <span className="box-conf">{box.confidence}%</span>
              </div>

              {/* Tracking ID */}
              <div className="box-tracking-id">
                <span>ID: #{box.trackingId}</span>
              </div>
            </div>
          ))}

          {/* Standby Watermark when Protection Mode is OFF */}
          {!protectionMode && (
            <div className="standby-watermark">
              <span className="standby-icon">🛡️</span>
              <div>
                <strong>Protection Mode Standby</strong>
                <p>Toggle "Security System" ON to activate real-time intruder detection</p>
              </div>
            </div>
          )}

          {/* Active Intruder Alert Banner Overlay */}
          {activeAlert && (
            <div className="stream-alert-banner">
              <div className="alert-banner-left">
                <span className="alert-siren-icon">🚨</span>
                <div>
                  <h4 className="alert-banner-title">INTRUDER DETECTED IN {activeAlert.location.toUpperCase()}!</h4>
                  <p className="alert-banner-sub">
                    Confidence: <strong>{activeAlert.confidence}%</strong> • Tracked at {activeAlert.timestamp}
                  </p>
                </div>
              </div>
              <button className="dismiss-alert-btn" onClick={handleDismissAlert} type="button">
                Dismiss Alert
              </button>
            </div>
          )}
        </div>

        {/* Top Badges (Exact match to reference screenshot) */}
        <div className="stream-top-bar">
          {/* Top Left Badges */}
          <div className="stream-badges-left">
            <div className="badge-pill dropdown" onClick={() => setShowResMenu(!showResMenu)}>
              <span>{resolution}</span>
              <span className="arrow-down">⌄</span>
              {showResMenu && (
                <div className="res-dropdown">
                  {['4K UHD', 'FHD (1080p)', 'HD (720p)'].map((r) => (
                    <div
                      key={r}
                      className="res-option"
                      onClick={(e) => {
                        e.stopPropagation();
                        setResolution(r.split(' ')[0]);
                        setShowResMenu(false);
                      }}
                    >
                      {r}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="badge-pill live-badge">
              <span className="live-dot"></span>
              <span>Live</span>
            </div>
          </div>

          {/* Top Right Badges (Battery, Wi-Fi, Sound) */}
          <div className="stream-badges-right">
            <div className="badge-pill info-badge" title="Camera Battery Level">
              <Battery size={13} className="badge-icon" />
              <span>{activeCamera.battery}%</span>
            </div>

            <div className="badge-pill info-badge" title="Wi-Fi Signal Strength">
              <Wifi size={13} className="badge-icon" />
              <span>{activeCamera.wifi}</span>
            </div>

            <div
              className={`badge-pill toggleable ${!isMutedState ? 'active' : ''}`}
              onClick={toggleMute}
              title="Camera Microphone Audio"
              role="button"
              tabIndex={0}
            >
              {!isMutedState ? <Volume2 size={13} /> : <VolumeX size={13} />}
              <span>{!isMutedState ? 'On' : 'Mute'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Stream Controls & Source Switcher Bar */}
      <div className="stream-bottom-controls">
        <div className="source-selector">
          <span className="source-label">Stream Source:</span>
          <div className="source-pills">
            <button
              className={`source-pill ${streamSource === 'mock' ? 'active' : ''}`}
              onClick={() => setStreamSource('mock')}
              type="button"
            >
              Simulated CCTV
            </button>
            <button
              className={`source-pill ${streamSource === 'webcam' ? 'active' : ''}`}
              onClick={() => setStreamSource('webcam')}
              type="button"
            >
              Webcam
            </button>
            <button
              className={`source-pill ${streamSource === 'backend' ? 'active' : ''}`}
              onClick={() => {
                if (!backendStatus.online) {
                  alert(`Backend server at ${backendStatus.url} is not responding yet. Once FastAPI/Django runs, this switches to real-time PyTorch inference!`);
                }
                setStreamSource('backend');
              }}
              type="button"
            >
              Backend API
            </button>
            <button
              className={`source-pill ${streamSource === 'video' ? 'active' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              type="button"
            >
              Upload Clip
            </button>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept="video/*"
              onChange={handleFileUpload}
            />
          </div>
        </div>

        {/* Quick Intruder Simulation Action Button (For VIVA & Demo) */}
        <div className="stream-actions">
          <button
            className="action-btn simulate-btn"
            onClick={handleSimulateIntruder}
            title="Simulate an Intruder Detection breach"
            type="button"
          >
            <AlertTriangle size={15} />
            <span>Simulate Intruder</span>
          </button>

          <button
            className="action-btn icon-only"
            onClick={toggleFullscreen}
            title="Toggle Fullscreen"
            type="button"
          >
            <Maximize2 size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
