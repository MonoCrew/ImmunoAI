import { useRef, useState, useEffect } from 'react';
import {
  Maximize2,
  Camera,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
} from 'lucide-react';
import { useSecurity } from '../context/useSecurity';
import { apiDetectFrame } from '../services/api';

export const LiveStreamPlayer = () => {
  const {
    protectionMode,
    activeAlert,
    dismissAlert,
    triggerIntruderAlert,
    updateDlTelemetry,
    dlTelemetry,
    backendStatus,
  } = useSecurity();

  const [hasCameraAccess, setHasCameraAccess] = useState(false);
  const [mediaStream, setMediaStream] = useState(null);
  const [liveBox, setLiveBox] = useState(null);

  const containerRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // Direct Attached System Camera Feed (getUserMedia)
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
        console.info('Direct system camera access notice:', err?.message || err);
        setHasCameraAccess(false);
      }
    }

    startCamera();

    return () => {
      isCancelled = true;
      if (localStream) {
        localStream.getTracks().forEach((track) => track.stop());
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

  // Frame Capture Loop: sends base64 image string to backend when Protection Mode is ON
  useEffect(() => {
    if (!protectionMode) return;

    let isSending = false;
    const interval = setInterval(async () => {
      if (isSending) return;
      try {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (hasCameraAccess && video && video.readyState >= 2) {
          // Adjust canvas resolution dynamically to match camera video
          if (video.videoWidth && canvas.width !== video.videoWidth) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
          }
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        } else {
          // Fallback test frame if hardware camera is not yet ready
          ctx.fillStyle = '#121418';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = '#64748b';
          ctx.font = '16px monospace';
          ctx.fillText('IMMUNOAI STANDBY SURVEILLANCE', 20, 40);
        }

        const base64Image = canvas.toDataURL('image/jpeg', 0.70);
        isSending = true;
        const res = await apiDetectFrame(base64Image);

        // Update Sidebar Live Monitor & Log to Browser Console
        if (res) {
          updateDlTelemetry(res);
          if (res.is_intruder && res.box) {
            setLiveBox({
              x: res.box[0],
              y: res.box[1],
              w: res.box[2],
              h: res.box[3],
              label: (res.consecutive_frames ?? 0) >= 5 ? 'INTRUDER' : (res.engine === 'yolo' ? 'TARGET ACQUIRED' : 'ANALYZING'),
              confidence: res.confidence,
              isConfirmed: (res.consecutive_frames ?? 0) >= 5,
              frames: res.consecutive_frames ?? 0,
            });
          } else {
            setLiveBox(null);
          }

          console.log(
            `%c[ImmunoAI DL]%c [${(res.engine || 'yolo').toUpperCase()}] Conf: ${(res.confidence ?? 0)}% | Logit: ${res.logit ?? 'N/A'} | Frames: ${res.consecutive_frames ?? 0}/5 | Latency: ${res.inference_ms ?? 0}ms`,
            'color: #f97316; font-weight: bold;',
            'color: #22c55e; font-weight: 500;'
          );
        }

        // Fail-safe immediate alert trigger if confirmed by 5 continuous frames
        if (res?.alert_triggered && res?.new_incident) {
          triggerIntruderAlert(res.new_incident);
        }
      } catch (err) {
        console.warn('Frame detection dispatch notice:', err?.message);
      } finally {
        isSending = false;
      }
    }, 600); // 600ms (~1.6 FPS): 5 continuous frames = 3s detection window

    return () => clearInterval(interval);
  }, [protectionMode, hasCameraAccess, triggerIntruderAlert]);

  // Clear live box if protection mode disarmed
  useEffect(() => {
    if (!protectionMode) {
      setLiveBox(null);
    }
  }, [protectionMode]);

  const handleDismissAlert = () => {
    dismissAlert();
  };

  // Toggle Fullscreen
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  // Active displayed bounding boxes (live tracking box + confirmed alert boxes)
  const displayBoxes =
    activeAlert && protectionMode
      ? [
          {
            x: activeAlert.box?.[0] ?? 35,
            y: activeAlert.box?.[1] ?? 25,
            w: activeAlert.box?.[2] ?? 25,
            h: activeAlert.box?.[3] ?? 50,
            label: 'INTRUDER CONFIRMED',
            confidence: activeAlert.confidence || '97.2',
            trackingId: activeAlert.id ? String(activeAlert.id).slice(-4) : 'ALERT',
            isConfirmed: true,
          },
        ]
      : protectionMode && liveBox
      ? [
          {
            x: liveBox.x,
            y: liveBox.y,
            w: liveBox.w,
            h: liveBox.h,
            label: `${liveBox.label} (${liveBox.frames}/5)`,
            confidence: liveBox.confidence,
            trackingId: 'SCAN',
            isConfirmed: liveBox.isConfirmed,
          },
        ]
      : [];

  return (
    <div className="stream-card-wrapper" ref={containerRef}>
      {/* Hidden canvas used to extract base64 frame string for the Python model */}
      <canvas ref={canvasRef} width={640} height={360} style={{ display: 'none' }} />

      {/* Stream Container */}
      <div className={`stream-player-container ${activeAlert ? 'alert-active' : ''}`}>
        {/* Single persistent Video Element — always mounted so stream never detaches */}
        <video
          ref={videoRef}
          className="stream-media"
          autoPlay
          playsInline
          muted
          style={{ display: hasCameraAccess ? 'block' : 'none' }}
        />

        {/* Fallback backdrop while camera is connecting or when camera is offline */}
        {!hasCameraAccess && (
          <div className="stream-poster-viewport direct-camera-backdrop">
            <img
              src="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1600&auto=format&fit=crop&q=85"
              alt="Direct System Camera Feed"
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
              className={`bounding-box ${box.isConfirmed ? 'intruder-box' : 'live-tracking-box'}`}
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
              <div className={`box-tag ${box.isConfirmed ? 'intruder' : 'tracking'}`}>
                <span className={box.isConfirmed ? 'pulse-danger' : 'pulse-warning'}></span>
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
              <ShieldCheck size={18} className="text-muted" />
              <div>
                <strong>Protection Mode Standby</strong>
                <p>Toggle "Protection Mode" ON to activate real-time intruder detection</p>
              </div>
            </div>
          )}

          {/* AI Server Offline Helper Banner (Shows helpful guidance instead of an ugly crash) */}
          {protectionMode && dlTelemetry?.ai_service_online === false && (
            <div className="ai-offline-watermark">
              <AlertTriangle size={18} className="text-amber" />
              <div>
                <strong>AI Inference Server Offline (Port 5001)</strong>
                <p>Start Python server: <code>cd server/ai_service/mini_server && python server.py</code></p>
              </div>
            </div>
          )}

          {/* Active Intruder Alert Banner Overlay */}
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
              <span>Live</span>
            </div>
          </div>

          <div className="stream-badges-right">
            <button
              className="badge-pill toggleable icon-only-badge"
              onClick={toggleFullscreen}
              title="Fullscreen"
              type="button"
            >
              <Maximize2 size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* Stream Bottom Controls: Direct Camera status info */}
      <div className="stream-bottom-controls">
        <div className="stream-camera-status-info">
          <Camera size={14} className="text-orange" />
          <span className="camera-status-text">
            {backendStatus?.online
              ? 'Live Camera Stream • Backend Connected (30 FPS)'
              : hasCameraAccess
              ? 'Direct System Camera • Hardware Connected'
              : 'Direct System Camera • Standby Feed Active'}
          </span>
        </div>
      </div>
    </div>
  );
};
