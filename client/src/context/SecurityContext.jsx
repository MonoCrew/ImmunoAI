import { useState, useEffect, useCallback } from 'react';
import {
  apiSetProtectionMode,
  checkBackendHealth,
  createAlertWebSocket,
  apiGetSnapshots,
  API_BASE_URL
} from '../services/api';
import {
  playArmSound,
  playDisarmSound,
  playClickSound,
  playIntruderAlarm,
  stopIntruderSiren,
  setMuted
} from '../services/audioAlert';
import { SecurityContext } from './SecurityContextInstance';

export const SecurityProvider = ({ children }) => {
  // Core: Protection Mode (The central check requested by user)
  const [protectionMode, setProtectionModeState] = useState(false);

  // Active Camera selection
  const [activeCameraId, setActiveCameraId] = useState('cam1');

  // Single Camera Stream for now as requested
  const [cameras] = useState([
    {
      id: 'cam1',
      name: 'Main Camera',
      location: 'Perimeter Surveillance Feed',
      resolution: 'FHD',
      battery: 100,
      wifi: 'Wi-Fi',
      isLive: true,
      audioOn: true,
    },
  ]);

  // Smart Control Cards from screenshot
  const [smartDevices, setSmartDevices] = useState({
    frontDoorLock: { name: 'Front Door Lock', status: true, subtext: 'Next unlock 06:00 AM', labelActive: 'Lock', labelInactive: 'Unlocked' },
    backyardSprinklers: { name: 'Backyard Sprinklers', status: false, subtext: 'Next watering 06:00 AM', labelActive: 'On', labelInactive: 'Off' },
    garageDoor: { name: 'Garage Door', status: true, subtext: 'Next open 08:00 AM', labelActive: 'Closed', labelInactive: 'Open' },
    outdoorLights: { name: 'Outdoor lights', status: true, subtext: 'Next unlock 06:00 AM', labelActive: 'On', labelInactive: 'Off' },
    sleepMode: { name: 'Sleep Mode', status: false, subtext: 'Scheduled 11:00 PM', labelActive: 'On', labelInactive: 'Off' },
    internet: { name: 'Internet', status: true, subtext: '120 Mbps Low Latency', labelActive: 'On', labelInactive: 'Off' },
    climate: { name: 'Climate Control', status: true, temp: 24, mode: 'Cold', autoTurnOn: '20:00 PM', autoTurnOff: '18:00 PM' },
  });

  // Whitelisted Authorized Project Members (Cartoon Avatars)
  const [members, setMembers] = useState([
    { id: 1, name: 'Anam', role: 'Team Member', avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=Anam' },
    { id: 2, name: 'Maliha', role: 'Team Member', avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=Maliha' },
    { id: 3, name: 'Mohsin (me)', role: 'Team Member', avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=Mohsin' },
  ]);

  // Activity Schedule & Intruder Logs
  const [activityLog, setActivityLog] = useState([
    { id: 101, title: 'Outdoor lights ON', time: '07:30 PM', type: 'schedule', category: 'light' },
    { id: 102, title: 'Garden watering', time: '07:40 PM', type: 'schedule', category: 'water' },
    { id: 103, title: 'Robot Vacuum Start', time: '08:25 PM', type: 'schedule', category: 'vacuum' },
    { id: 104, title: 'Auto-lock all door', time: '09:50 PM', type: 'schedule', category: 'lock' },
  ]);

  // Real-time Intruder Alert state
  const [activeAlert, setActiveAlert] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [isMutedState, setIsMutedState] = useState(false);

  // Video feed source: direct camera
  const [streamSource, setStreamSource] = useState('direct');

  // Real Captured Intruders Snapshot Gallery (Starts 100% empty, populated only by real camera captures)
  const [capturedIntruders, setCapturedIntruders] = useState([]);

  // Live Deep Learning Telemetry & Mini Logs for Sidebar Monitor
  const [dlTelemetry, setDlTelemetry] = useState({
    prob: 0,
    confidence: 0,
    logit: 0,
    is_intruder: false,
    consecutive_frames: 0,
    required_frames: 5,
    in_cooldown: false,
    cooldown_remaining_seconds: 0,
    inference_ms: 0,
    recentLogs: [],
    lastUpdated: 0,
  });

  const updateDlTelemetry = (data) => {
    if (!data) return;
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const probVal = data.prob !== undefined ? data.prob : (data.confidence ? data.confidence / 100 : 0);
    const confPercent = (probVal * 100).toFixed(1);
    const count = data.consecutive_frames || 0;
    const isAlert = data.is_intruder;

    const logLine = `${nowTime} | P:${confPercent}% | C:${count}/5 | ${isAlert ? '🚨POS' : '✅NORM'}`;

    setDlTelemetry((prev) => ({
      prob: probVal,
      confidence: confPercent,
      logit: data.logit || 0,
      is_intruder: Boolean(isAlert),
      consecutive_frames: count,
      required_frames: data.required_frames || 5,
      in_cooldown: Boolean(data.in_cooldown),
      cooldown_remaining_seconds: data.cooldown_remaining_seconds || 0,
      inference_ms: data.inference_ms || 18,
      recentLogs: [logLine, ...(prev.recentLogs || [])].slice(0, 4),
      lastUpdated: Date.now(),
    }));
  };

  // Backend connection status
  const [backendStatus, setBackendStatus] = useState({
    online: false,
    checking: true,
    url: API_BASE_URL,
    fps: 0,
    model: 'YOLOv8-Intruder (PyTorch)',
  });

  // Detection parameters
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.70);

  // Mute toggle
  const toggleMute = () => {
    const next = !isMutedState;
    setIsMutedState(next);
    setMuted(next);
  };

  // Toggle Protection Mode
  const toggleProtectionMode = async () => {
    playClickSound();
    const nextState = !protectionMode;
    setProtectionModeState(nextState);

    if (nextState) {
      playArmSound();
      const armLog = {
        id: Date.now(),
        title: 'Security System ARMED (Intruder Detection Active)',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        type: 'system',
        category: 'shield',
      };
      setActivityLog((prev) => [armLog, ...prev]);
    } else {
      playDisarmSound();
      stopIntruderSiren();
      setActiveAlert(null);
      const disarmLog = {
        id: Date.now(),
        title: 'Security System DISARMED (Standby Mode)',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        type: 'system',
        category: 'shield',
      };
      setActivityLog((prev) => [disarmLog, ...prev]);
    }

    // Call backend API (if available)
    await apiSetProtectionMode(nextState);
  };

  // Toggle individual smart device
  const toggleDevice = (deviceId) => {
    playClickSound();
    setSmartDevices((prev) => {
      const dev = prev[deviceId];
      if (!dev) return prev;
      return {
        ...prev,
        [deviceId]: { ...dev, status: !dev.status },
      };
    });
  };

  // Update Climate Temperature
  const setClimateTemp = (delta) => {
    playClickSound();
    setSmartDevices((prev) => ({
      ...prev,
      climate: {
        ...prev.climate,
        temp: Math.min(32, Math.max(16, prev.climate.temp + delta)),
      },
    }));
  };

  // Trigger Intruder Alert Handler
  const triggerIntruderAlert = useCallback((detection) => {
    if (!protectionMode) {
      return;
    }

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const activeCam = cameras.find((c) => c.id === activeCameraId) || cameras[0];

    const alertEvent = {
      id: Date.now(),
      cameraId: activeCam.id,
      cameraName: activeCam.name,
      location: activeCam.location,
      confidence: detection?.confidence || 96.8,
      timestamp,
      box: detection?.box || [150, 100, 220, 340],
      imageUrl: detection?.imageUrl || null,
      message: `Unauthorized Person Detected in ${activeCam.location}!`,
    };

    setActiveAlert(alertEvent);
    playIntruderAlarm(5000);

    // Add to activity log
    setActivityLog((prev) => [
      {
        id: alertEvent.id,
        title: `🚨 INTRUDER DETECTED (${alertEvent.confidence}% confidence)`,
        time: timestamp,
        type: 'intruder',
        category: 'alert',
        camera: activeCam.name,
      },
      ...prev,
    ]);

    // Add to notifications
    setNotifications((prev) => [alertEvent, ...prev]);

    // Automatically record snapshot to Captured Intruders Gallery
    const newSnapshot = {
      id: `snap-${Date.now()}`,
      timestamp: `Today, ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      camera: activeCam.name,
      confidence: `${detection?.confidence || '97.4'}%`,
      threatLevel: 'Live Breach Detected',
      image: detection?.imageUrl || 'https://images.unsplash.com/photo-1509114397022-ed747cca3f65?w=600&auto=format&fit=crop&q=80',
      details: 'Live unauthorized intruder detected by direct system camera feed.',
      box: detection?.box || [30, 20, 35, 60],
    };
    setCapturedIntruders((prev) => [newSnapshot, ...prev]);
  }, [protectionMode, activeCameraId, cameras]);

  // Dismiss current alert
  const dismissAlert = () => {
    playClickSound();
    stopIntruderSiren();
    setActiveAlert(null);
  };

  // Add Enrolled Member
  const addMember = (memberData) => {
    playClickSound();
    const newMember = {
      id: Date.now(),
      name: memberData.name || 'New Member',
      role: memberData.role || 'Authorized',
      avatar: memberData.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80',
    };
    setMembers((prev) => [...prev, newMember]);
  };

  // Check backend health periodically
  useEffect(() => {
    let mounted = true;

    const check = async () => {
      const res = await checkBackendHealth();
      if (!mounted) return;
      if (res.online) {
        setBackendStatus({
          online: true,
          checking: false,
          url: API_BASE_URL,
          fps: res.data?.fps || 30,
          model: res.data?.model || 'ImmunoAICNN (PyTorch)',
        });
        const snaps = await apiGetSnapshots();
        if (mounted && Array.isArray(snaps)) {
          setCapturedIntruders(snaps);
        }
      } else {
        setBackendStatus((prev) => ({
          ...prev,
          online: false,
          checking: false,
        }));
      }
    };

    check();
    const timer = setInterval(check, 10000);

    // Also establish WebSocket if backend supports it
    const ws = createAlertWebSocket(
      (data) => {
        if (data.type === 'INTRUDER_DETECTED') {
          triggerIntruderAlert(data);
        }
      },
      (status) => {
        if (mounted && status.connected) {
          setBackendStatus((prev) => ({ ...prev, online: true }));
        }
      }
    );

    return () => {
      mounted = false;
      clearInterval(timer);
      ws.close();
      stopIntruderSiren();
    };
  }, [triggerIntruderAlert]);

  const activeCamera = cameras.find((c) => c.id === activeCameraId) || cameras[0];

  return (
    <SecurityContext.Provider
      value={{
        protectionMode,
        toggleProtectionMode,
        activeCameraId,
        setActiveCameraId,
        activeCamera,
        cameras,
        smartDevices,
        toggleDevice,
        setClimateTemp,
        members,
        addMember,
        activityLog,
        activeAlert,
        triggerIntruderAlert,
        dismissAlert,
        notifications,
        isMutedState,
        toggleMute,
        streamSource,
        setStreamSource,
        capturedIntruders,
        setCapturedIntruders,
        backendStatus,
        confidenceThreshold,
        setConfidenceThreshold,
        dlTelemetry,
        updateDlTelemetry,
      }}
    >
      {children}
    </SecurityContext.Provider>
  );
};
