// Centralized API Client for Backend Integration (FastAPI / Django)
// Supports live HTTP/WebSocket endpoints with seamless automatic fallback to Simulated Mode

import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 3000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Check whether backend is accessible
export const checkBackendHealth = async () => {
  try {
    const res = await client.get('/api/health');
    return { online: true, data: res.data };
  } catch (err) {
    return { online: false, error: err.message };
  }
};

// Protection Mode API
export const apiGetStatus = async () => {
  try {
    const res = await client.get('/api/status');
    return { success: true, data: res.data };
  } catch {
    return { success: false, fallback: true };
  }
};

export const apiSetProtectionMode = async (enabled) => {
  try {
    const res = await client.post('/api/protection-mode', { enabled });
    return { success: true, data: res.data };
  } catch {
    return { success: false, fallback: true, enabled };
  }
};

// Intruder Detection Events API
export const apiGetEvents = async () => {
  try {
    const res = await client.get('/api/events');
    return { success: true, data: res.data };
  } catch {
    return { success: false, fallback: true };
  }
};

export const apiLogIntruderEvent = async (eventData) => {
  try {
    const res = await client.post('/api/events', eventData);
    return { success: true, data: res.data };
  } catch {
    return { success: false, fallback: true };
  }
};

// Authorized Members Whitelist API
export const apiGetMembers = async () => {
  try {
    const res = await client.get('/api/members');
    return { success: true, data: res.data };
  } catch {
    return { success: false, fallback: true };
  }
};

export const apiAddMember = async (member) => {
  try {
    const res = await client.post('/api/members', member);
    return { success: true, data: res.data };
  } catch {
    return { success: false, fallback: true };
  }
};

// Smart Device Control API
export const apiSetDeviceState = async (deviceId, state) => {
  try {
    const res = await client.post(`/api/devices/${deviceId}`, state);
    return { success: true, data: res.data };
  } catch {
    return { success: false, fallback: true };
  }
};

// Stream URL helper for <img> / <video> tag
export const getCameraStreamUrl = (cameraId = 'cam1') => {
  return `${API_BASE_URL}/api/stream/${cameraId}`;
};

// Real-time WebSocket connection for zero-latency detection alerts
export const createAlertWebSocket = (onAlertReceived, onStatusChange) => {
  let ws = null;
  let isClosedManually = false;
  let reconnectTimer = null;

  const connect = () => {
    try {
      ws = new WebSocket(`${WS_BASE_URL}/ws/alerts`);

      ws.onopen = () => {
        if (onStatusChange) onStatusChange({ connected: true });
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (onAlertReceived) onAlertReceived(payload);
        } catch {
          // ignore non-json messages
        }
      };

      ws.onerror = () => {
        if (onStatusChange) onStatusChange({ connected: false });
      };

      ws.onclose = () => {
        if (onStatusChange) onStatusChange({ connected: false });
        if (!isClosedManually) {
          reconnectTimer = setTimeout(connect, 5000);
        }
      };
    } catch {
      if (onStatusChange) onStatusChange({ connected: false });
    }
  };

  connect();

  return {
    close: () => {
      isClosedManually = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    },
    send: (data) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
      }
    },
  };
};
