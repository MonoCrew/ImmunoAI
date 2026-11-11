/**
 * Argus Intruder Detection System - Frontend Controller
 * Manages WebSocket telemetry, UI state switches, Web Audio alerts,
 * and REST API communication.
 */

// Application State
const state = {
    isArmed: false,
    isConnected: false,
    isIntrusionActive: false,
    isAudioMuted: false,
    cooldownRemaining: 0,
    ws: null,
    audioCtx: null,
    cooldownInterval: null,
    recentEvents: []
};

// Initialize Lucide icons
function refreshIcons() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

// Web Audio API Security Alarm Synthesizer
function playSecurityAlarm() {
    if (state.isAudioMuted) return;

    try {
        if (!state.audioCtx) {
            state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (state.audioCtx.state === 'suspended') {
            state.audioCtx.resume();
        }

        const now = state.audioCtx.currentTime;
        const osc = state.audioCtx.createOscillator();
        const gain = state.audioCtx.createGain();

        osc.type = 'sawtooth';
        
        // 2-Tone oscillating emergency alarm (880Hz - 660Hz)
        const duration = 2.4;
        for (let i = 0; i < 4; i++) {
            const t = now + i * 0.6;
            osc.frequency.setValueAtTime(880, t);
            osc.frequency.setValueAtTime(659.25, t + 0.3);
        }

        // Volume envelope
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

        osc.connect(gain);
        gain.connect(state.audioCtx.destination);

        osc.start(now);
        osc.stop(now + duration);
    } catch (e) {
        console.warn("[Audio] Could not play alert sound:", e);
    }
}

// WebSocket Management
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    console.log(`[WS] Connecting to ${wsUrl}...`);
    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log("[WS] Connected successfully.");
        state.isConnected = true;
        updateConnectionBadge(true);
        addLogEntry("SYSTEM", "Real-time telemetry link established.", "info");
    };

    state.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWsMessage(data);
        } catch (e) {
            console.error("[WS] Parse error:", e);
        }
    };

    state.ws.onclose = () => {
        console.warn("[WS] Disconnected. Reconnecting in 3 seconds...");
        state.isConnected = false;
        updateConnectionBadge(false);
        setTimeout(connectWebSocket, 3000);
    };

    state.ws.onerror = (err) => {
        console.error("[WS] Socket error:", err);
        state.ws.close();
    };
}

// Handle Incoming WebSocket Messages
function handleWsMessage(msg) {
    switch (msg.type) {
        case "initial_state":
            setArmedState(msg.is_armed, false);
            startCooldownTicker(msg.cooldown_remaining);
            if (msg.recent_events) {
                state.recentEvents = msg.recent_events;
                renderEventGallery();
            }
            break;

        case "arm_state_changed":
            setArmedState(msg.is_armed, false);
            addLogEntry("STATE", msg.is_armed ? "System ARMED for intrusion monitoring." : "System DISARMED. Passive streaming active.", msg.is_armed ? "danger" : "success");
            break;

        case "intrusion_alert":
            triggerIntrusionUI(msg.meta, msg.event);
            break;

        case "intrusion_cleared":
            clearIntrusionUI();
            break;

        case "status_update":
            updateTelemetryDisplay(msg.data);
            break;
    }
}

// Arm / Disarm State Handlers
async function toggleArm() {
    const nextState = !state.isArmed;
    try {
        const res = await fetch("/api/arm", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ armed: nextState })
        });
        const data = await res.json();
        if (data.success) {
            setArmedState(data.is_armed, true);
        }
    } catch (e) {
        console.error("[API] Error toggling arm state:", e);
        showToast("Error updating system state", "error");
    }
}

function setArmedState(isArmed, notifyLog = false) {
    state.isArmed = isArmed;
    const switchEl = document.getElementById("armToggleSwitch");
    const switchKnob = document.getElementById("armToggleKnob");
    const statusCard = document.getElementById("systemStatusCard");
    const statusBadge = document.getElementById("statusBadge");
    const statusText = document.getElementById("statusText");
    const videoContainer = document.getElementById("videoContainer");

    if (isArmed) {
        // Armed State (Crimson / Red Pulse)
        switchEl.classList.remove("bg-slate-700");
        switchEl.classList.add("bg-red-600");
        switchKnob.style.transform = "translateX(28px)";

        statusCard.classList.remove("border-emerald-500/30", "disarmed-glow");
        statusCard.classList.add("border-red-500/60", "armed-pulse");

        statusBadge.innerHTML = `<span class="relative flex h-3 w-3 mr-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
        </span> ARMED & ACTIVE`;
        statusBadge.className = "inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-red-950/80 text-red-300 border border-red-700/60";

        statusText.innerHTML = "Monitoring space. Intruder detection and alert triggers are ACTIVE.";
        videoContainer.classList.add("border-red-900/60");
        videoContainer.classList.remove("border-slate-800");
    } else {
        // Disarmed State (Emerald Green / Passive)
        switchEl.classList.remove("bg-red-600");
        switchEl.classList.add("bg-slate-700");
        switchKnob.style.transform = "translateX(0px)";

        statusCard.classList.remove("border-red-500/60", "armed-pulse");
        statusCard.classList.add("border-emerald-500/30", "disarmed-glow");

        statusBadge.innerHTML = `<span class="inline-flex rounded-full h-3 w-3 bg-emerald-500 mr-2"></span> DISARMED (PASSIVE)`;
        statusBadge.className = "inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700/60";

        statusText.innerHTML = "Passive video streaming. Intrusion checks and email alerts are paused.";
        videoContainer.classList.remove("border-red-900/60");
        videoContainer.classList.add("border-slate-800");

        clearIntrusionUI();
    }
}

// Intrusion Alert Trigger
function triggerIntrusionUI(meta, eventRecord) {
    state.isIntrusionActive = true;
    const banner = document.getElementById("breachBanner");
    const videoContainer = document.getElementById("videoContainer");

    banner.classList.remove("hidden");
    videoContainer.classList.add("breach-flash");

    document.getElementById("breachCount").textContent = meta.zone_person_count || 1;
    document.getElementById("breachConfidence").textContent = `${Math.round((meta.highest_confidence || 0.8) * 100)}%`;
    document.getElementById("breachTime").textContent = meta.formatted_time || new Date().toLocaleTimeString();

    // Trigger Audio Alert
    playSecurityAlarm();

    // Start anti-spam cooldown display if email sent
    if (eventRecord && eventRecord.email_sent) {
        startCooldownTicker(45);
    }

    // Add to event gallery
    if (eventRecord) {
        state.recentEvents.unshift(eventRecord);
        renderEventGallery();
    }

    addLogEntry(
        "BREACH",
        `Unauthorized human detected (${meta.zone_person_count} in zone, ${Math.round(meta.highest_confidence * 100)}% conf). Snapshot captured.`,
        "danger"
    );
}

function clearIntrusionUI() {
    state.isIntrusionActive = false;
    const banner = document.getElementById("breachBanner");
    const videoContainer = document.getElementById("videoContainer");
    if (banner) banner.classList.add("hidden");
    if (videoContainer) videoContainer.classList.remove("breach-flash");
}

// Anti-Spam Email Cooldown Ticker
function startCooldownTicker(seconds) {
    state.cooldownRemaining = seconds;
    const badge = document.getElementById("cooldownBadge");
    const text = document.getElementById("cooldownText");

    if (state.cooldownInterval) {
        clearInterval(state.cooldownInterval);
    }

    if (seconds <= 0) {
        text.textContent = "Email Alert Ready";
        badge.className = "inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/40";
        return;
    }

    badge.className = "inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-amber-950/60 text-amber-400 border border-amber-800/40";

    state.cooldownInterval = setInterval(() => {
        state.cooldownRemaining--;
        if (state.cooldownRemaining <= 0) {
            clearInterval(state.cooldownInterval);
            text.textContent = "Email Alert Ready";
            badge.className = "inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/40";
        } else {
            text.textContent = `Cooldown: ${state.cooldownRemaining}s`;
        }
    }, 1000);
}

// Event Gallery Rendering
function renderEventGallery() {
    const gallery = document.getElementById("snapshotGallery");
    if (!gallery) return;

    if (state.recentEvents.length === 0) {
        gallery.innerHTML = `
            <div class="col-span-full py-8 text-center text-slate-500 text-sm">
                <i data-lucide="shield-check" class="w-8 h-8 mx-auto mb-2 opacity-40"></i>
                No intrusion incidents logged yet.
            </div>`;
        refreshIcons();
        return;
    }

    gallery.innerHTML = state.recentEvents.slice(0, 6).map((ev) => `
        <div class="group relative rounded-lg overflow-hidden border border-slate-700/60 bg-slate-800/80 cursor-pointer transition hover:border-red-500/60"
             onclick="openLightbox('${ev.snapshot_url}', '${ev.timestamp}', ${ev.confidence})">
            <img src="${ev.snapshot_url}" alt="Incident Snapshot" class="w-full h-24 object-cover group-hover:scale-105 transition duration-300">
            <div class="p-2 text-xs">
                <div class="flex justify-between items-center text-slate-400 font-mono text-[10px]">
                    <span>${ev.timestamp.split(' ')[1] || ev.timestamp}</span>
                    <span class="text-red-400 font-bold">${Math.round(ev.confidence * 100)}%</span>
                </div>
            </div>
            <div class="absolute inset-0 bg-red-600/20 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                <i data-lucide="maximize-2" class="w-5 h-5 text-white"></i>
            </div>
        </div>
    `).join("");

    refreshIcons();
}

// Real-Time Event Log Terminal
function addLogEntry(tag, message, level = "info") {
    const logContainer = document.getElementById("eventLogEntries");
    if (!logContainer) return;

    const timeStr = new Date().toLocaleTimeString();
    let badgeClass = "bg-blue-950/80 text-blue-300 border-blue-800/50";
    if (level === "danger") badgeClass = "bg-red-950/80 text-red-300 border-red-800/50";
    if (level === "success") badgeClass = "bg-emerald-950/80 text-emerald-300 border-emerald-800/50";
    if (level === "warning") badgeClass = "bg-amber-950/80 text-amber-300 border-amber-800/50";

    const entry = document.createElement("div");
    entry.className = "flex items-start space-x-2 py-1 text-xs font-mono border-b border-slate-800/60";
    entry.innerHTML = `
        <span class="text-slate-500 text-[11px]">${timeStr}</span>
        <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold border ${badgeClass}">[${tag}]</span>
        <span class="text-slate-300 flex-1">${message}</span>
    `;

    logContainer.prepend(entry);

    // Keep log to max 40 entries
    while (logContainer.children.length > 40) {
        logContainer.removeChild(logContainer.lastChild);
    }
}

// Telemetry Polling Backup
async function pollTelemetry() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        updateTelemetryDisplay(data);
    } catch (e) {
        // Quiet fail on network hiccup
    }
}

function updateTelemetryDisplay(data) {
    if (!data) return;
    const fpsEl = document.getElementById("telemetryFps");
    const countEl = document.getElementById("telemetryCount");
    const debounceEl = document.getElementById("telemetryDebounce");

    if (fpsEl) fpsEl.textContent = `${data.camera_fps || 30} FPS`;
    if (countEl) countEl.textContent = data.zone_person_count || 0;
    if (debounceEl) debounceEl.textContent = `${data.consecutive_detections || 0}/4`;

    if (data.is_mock_camera) {
        const mockPill = document.getElementById("mockCameraIndicator");
        if (mockPill) mockPill.classList.remove("hidden");
    }
}

function updateConnectionBadge(online) {
    const badge = document.getElementById("connectionBadge");
    if (!badge) return;
    if (online) {
        badge.innerHTML = `<span class="h-2 w-2 rounded-full bg-emerald-400 mr-1.5"></span> LIVE`;
        badge.className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/50";
    } else {
        badge.innerHTML = `<span class="h-2 w-2 rounded-full bg-amber-400 mr-1.5"></span> RECONNECTING`;
        badge.className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-950/60 text-amber-400 border border-amber-800/50";
    }
}

// Lightbox Snapshot Modal
function openLightbox(url, timestamp, conf) {
    const modal = document.getElementById("lightboxModal");
    const img = document.getElementById("lightboxImg");
    const info = document.getElementById("lightboxInfo");
    const dlBtn = document.getElementById("lightboxDownload");

    img.src = url;
    info.textContent = `Timestamp: ${timestamp} | Detection Confidence: ${Math.round(conf * 100)}%`;
    dlBtn.href = url;
    modal.classList.remove("hidden");
}

function closeLightbox() {
    document.getElementById("lightboxModal").classList.add("hidden");
}

// Manual Snapshot Trigger
async function triggerManualSnapshot() {
    try {
        const res = await fetch("/api/manual-snapshot", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Snapshot saved to gallery", "success");
            state.recentEvents.unshift({
                snapshot_url: data.snapshot_url,
                timestamp: data.timestamp,
                confidence: 1.0
            });
            renderEventGallery();
            addLogEntry("SNAPSHOT", `Manual snapshot captured: ${data.snapshot_url}`, "info");
        }
    } catch (e) {
        showToast("Failed to take snapshot", "error");
    }
}

// Audio Mute Toggle
function toggleAudioMute() {
    state.isAudioMuted = !state.isAudioMuted;
    const icon = document.getElementById("audioMuteIcon");
    const text = document.getElementById("audioMuteText");
    if (state.isAudioMuted) {
        icon.setAttribute("data-lucide", "volume-x");
        text.textContent = "Unmute Siren";
        showToast("Security siren muted", "info");
    } else {
        icon.setAttribute("data-lucide", "volume-2");
        text.textContent = "Mute Siren";
        showToast("Security siren enabled", "info");
    }
    refreshIcons();
}

// Settings Modal Management
async function openSettingsModal() {
    try {
        const res = await fetch("/api/settings");
        const cfg = await res.json();

        document.getElementById("cfgSmtpServer").value = cfg.smtp_server || "smtp.gmail.com";
        document.getElementById("cfgSmtpPort").value = cfg.smtp_port || 587;
        document.getElementById("cfgSmtpUser").value = cfg.smtp_username || "";
        document.getElementById("cfgSmtpPass").value = cfg.smtp_password || "";
        document.getElementById("cfgSmtpRecipient").value = cfg.smtp_recipient || "";
        document.getElementById("cfgCooldown").value = cfg.email_cooldown_seconds || 45;
        document.getElementById("cooldownValDisplay").textContent = `${cfg.email_cooldown_seconds || 45}s`;

        document.getElementById("cfgConfidence").value = Math.round((cfg.confidence_threshold || 0.5) * 100);
        document.getElementById("confValDisplay").textContent = `${Math.round((cfg.confidence_threshold || 0.5) * 100)}%`;

        document.getElementById("cfgDebounce").value = cfg.debounce_frames || 4;
        document.getElementById("debounceValDisplay").textContent = `${cfg.debounce_frames || 4} frames`;

        document.getElementById("settingsModal").classList.remove("hidden");
    } catch (e) {
        showToast("Could not load settings", "error");
    }
}

function closeSettingsModal() {
    document.getElementById("settingsModal").classList.add("hidden");
}

async function saveSettings(e) {
    if (e) e.preventDefault();

    const payload = {
        smtp_server: document.getElementById("cfgSmtpServer").value.trim(),
        smtp_port: parseInt(document.getElementById("cfgSmtpPort").value, 10),
        smtp_username: document.getElementById("cfgSmtpUser").value.trim(),
        smtp_password: document.getElementById("cfgSmtpPass").value,
        smtp_recipient: document.getElementById("cfgSmtpRecipient").value.trim(),
        email_cooldown_seconds: parseInt(document.getElementById("cfgCooldown").value, 10),
        confidence_threshold: parseFloat(document.getElementById("cfgConfidence").value) / 100.0,
        debounce_frames: parseInt(document.getElementById("cfgDebounce").value, 10)
    };

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast("Settings saved successfully!", "success");
            closeSettingsModal();
            addLogEntry("CONFIG", "Updated detection and alert parameters.", "info");
        }
    } catch (e) {
        showToast("Error saving settings", "error");
    }
}

async function testEmailDispatch() {
    const btn = document.getElementById("testEmailBtn");
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin mr-2">⏳</span> Testing SMTP...`;

    try {
        const res = await fetch("/api/test-email", { method: "POST" });
        const result = await res.json();
        if (result.success) {
            showToast(result.message, "success");
            addLogEntry("SMTP", "Test email delivered successfully.", "success");
        } else {
            showToast(result.message, "error");
            addLogEntry("SMTP", `Test email failed: ${result.message}`, "danger");
        }
    } catch (e) {
        showToast("Test email request failed.", "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
        refreshIcons();
    }
}

// UI Notification Toast
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    let bg = "bg-slate-800 text-slate-100 border-slate-700";
    if (type === "success") bg = "bg-emerald-900 text-emerald-100 border-emerald-700";
    if (type === "error") bg = "bg-red-900 text-red-100 border-red-700";

    toast.className = `p-3 rounded-lg border text-xs shadow-xl transition-all duration-300 flex items-center space-x-2 ${bg}`;
    toast.innerHTML = `<span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Fullscreen Video View
function toggleFullscreen() {
    const el = document.getElementById("videoContainer");
    if (!document.fullscreenElement) {
        el.requestFullscreen().catch((err) => {
            console.warn("Fullscreen request error:", err);
        });
    } else {
        document.exitFullscreen();
    }
}

// Initialization on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
    refreshIcons();
    connectWebSocket();
    setInterval(pollTelemetry, 2500);

    // Initial log entry
    addLogEntry("SYSTEM", "Argus Intruder Detection Core online.", "info");

    // Slider display updates
    const confSlider = document.getElementById("cfgConfidence");
    if (confSlider) {
        confSlider.oninput = (e) => {
            document.getElementById("confValDisplay").textContent = `${e.target.value}%`;
        };
    }
    const debSlider = document.getElementById("cfgDebounce");
    if (debSlider) {
        debSlider.oninput = (e) => {
            document.getElementById("debounceValDisplay").textContent = `${e.target.value} frames`;
        };
    }
    const cdSlider = document.getElementById("cfgCooldown");
    if (cdSlider) {
        cdSlider.oninput = (e) => {
            document.getElementById("cooldownValDisplay").textContent = `${e.target.value}s`;
        };
    }
});
