"""
Notification module for Intruder Detection System.
Handles rate-limited email dispatches using standard smtplib and email modules,
saves incident snapshots to disk, and executes dispatches asynchronously to prevent stream lag.
"""

import os
import cv2
import time
import smtplib
import threading
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import Dict, Any, Optional, List, Tuple
from config import SNAPSHOTS_DIR, config_manager


class EmailNotifier:
    """Manages rate-limited alert email dispatching and snapshot archival."""

    def __init__(self):
        self.last_alert_time: float = 0.0
        self.lock = threading.Lock()
        self.event_history: List[Dict[str, Any]] = []
        self.max_history_size = 50

    def get_cooldown_remaining(self) -> int:
        """Returns the number of seconds remaining before another email can be sent."""
        cooldown = config_manager.get("email_cooldown_seconds", 45)
        elapsed = time.time() - self.last_alert_time
        remaining = int(cooldown - elapsed)
        return max(0, remaining)

    def can_send_alert(self) -> bool:
        """Checks if the anti-spam cooldown period has expired."""
        return self.get_cooldown_remaining() == 0

    def save_snapshot(self, frame, prefix: str = "intrusion") -> Tuple[str, str]:
        """
        Saves a frame to static/snapshots directory.
        Returns:
            file_path: Absolute disk path.
            web_url: Relative URL for frontend display.
        """
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp_str}_{int(time.time() * 1000) % 1000}.jpg"
        filepath = SNAPSHOTS_DIR / filename
        
        cv2.imwrite(str(filepath), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        web_url = f"/static/snapshots/{filename}"
        return str(filepath), web_url

    def dispatch_alert(
        self,
        frame,
        meta: Dict[str, Any],
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Processes an intrusion alert:
        - Saves the incident snapshot.
        - Records the event in the history log.
        - Asynchronously dispatches the email if rate limit allows.
        """
        with self.lock:
            can_send = self.can_send_alert() or force

            # Save snapshot
            snapshot_path, snapshot_url = self.save_snapshot(frame, prefix="intrusion")
            
            event_record = {
                "id": len(self.event_history) + 1,
                "timestamp": meta.get("formatted_time", time.strftime("%Y-%m-%d %H:%M:%S")),
                "epoch": time.time(),
                "confidence": meta.get("highest_confidence", 0.0),
                "person_count": meta.get("zone_person_count", 1),
                "snapshot_url": snapshot_url,
                "email_sent": False,
                "status": "DETECTED"
            }

            if can_send:
                self.last_alert_time = time.time()
                event_record["email_sent"] = True
                event_record["status"] = "ALERT_DISPATCHED"
                
                # Launch email worker asynchronously to avoid blocking video thread
                worker = threading.Thread(
                    target=self._send_email_worker,
                    args=(snapshot_path, meta.copy(), force),
                    daemon=True
                )
                worker.start()
            else:
                event_record["status"] = f"RATE_LIMITED ({self.get_cooldown_remaining()}s remaining)"
                print(f"[Notifier] Email suppressed by cooldown. {self.get_cooldown_remaining()}s remaining.")

            self.event_history.insert(0, event_record)
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop()

            return event_record

    def _send_email_worker(self, snapshot_path: str, meta: Dict[str, Any], force: bool = False):
        """Worker thread function executing the SMTP handshake and email transmission."""
        cfg = config_manager.config
        
        smtp_server = cfg.get("smtp_server", "smtp.gmail.com")
        smtp_port = int(cfg.get("smtp_port", 587))
        username = cfg.get("smtp_username", "").strip()
        password = cfg.get("smtp_password", "").strip()
        recipient = cfg.get("smtp_recipient", "").strip()
        use_tls = cfg.get("smtp_use_tls", True)
        use_ssl = cfg.get("smtp_use_ssl", False)
        subject = cfg.get("email_subject", "⚠️ SECURITY ALERT: Intrusion Detected")

        # Fallback simulation if credentials are not configured
        if not username or not password or not recipient:
            print(f"[Notifier SIMULATED] Intrusion snapshot archived at {snapshot_path}.")
            print("[Notifier SIMULATED] SMTP credentials not fully configured; skipped external email dispatch.")
            return

        try:
            print(f"[Notifier] Connecting to SMTP {smtp_server}:{smtp_port} for alert dispatch...")
            
            # Create multipart message
            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = f"Argus Security System <{username}>"
            msg["To"] = recipient

            formatted_time = meta.get("formatted_time", time.strftime("%Y-%m-%d %H:%M:%S"))
            confidence_pct = int(meta.get("highest_confidence", 0.0) * 100)
            person_count = meta.get("zone_person_count", 1)

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 32px 12px; background-color: #f3f4f7; font-family: -apple-system, BlinkMacSystemFont, 'Plus Jakarta Sans', 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; -webkit-font-smoothing: antialiased;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 28px; border: 1px solid #eef1f6; box-shadow: 0 12px 35px -4px rgba(0, 0, 0, 0.05); overflow: hidden;">
                    
                    <!-- Top Brand Header -->
                    <div style="padding: 24px 28px 16px 28px; border-bottom: 1px solid #f1f5f9;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td>
                                    <div style="font-size: 15px; font-weight: 800; letter-spacing: -0.2px; color: #0f172a;">
                                        ARGUS <span style="font-size: 10px; font-weight: 700; background-color: #f1f5f9; color: #475569; padding: 2px 7px; border-radius: 9999px; border: 1px solid #e2e8f0; margin-left: 4px;">SENTINEL</span>
                                    </div>
                                    <div style="font-size: 11px; color: #94a3b8; font-weight: 500; margin-top: 2px;">Smart Perimeter & Security Alert</div>
                                </td>
                                <td style="text-align: right;">
                                    <span style="display: inline-block; background-color: #fff1f2; color: #e11d48; border: 1px solid #fecdd3; border-radius: 9999px; padding: 4px 12px; font-size: 11px; font-weight: 700; letter-spacing: 0.2px;">
                                        ● INTRUSION ALERT
                                    </span>
                                </td>
                            </tr>
                        </table>
                    </div>

                    <!-- Holographic Iridescent Accent Card (Matching UI Smart Card) -->
                    <div style="margin: 20px 24px 16px 24px; padding: 22px 24px; border-radius: 22px; background: linear-gradient(135deg, #a5b4fc 0%, #c4b5fd 30%, #bae6fd 70%, #bbf7d0 100%); border: 1px solid rgba(255, 255, 255, 0.8); box-shadow: 0 6px 20px rgba(165, 180, 252, 0.25);">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td>
                                    <span style="display: inline-block; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.8px; color: #312e81; background-color: rgba(255, 255, 255, 0.65); padding: 3px 8px; border-radius: 9999px; border: 1px solid rgba(255, 255, 255, 0.5);">
                                        UNIT: CAM-01 • 1080P
                                    </span>
                                    <div style="font-size: 18px; font-weight: 900; color: #0f172a; margin-top: 10px; letter-spacing: -0.3px;">
                                        Spatial Breach Detected
                                    </div>
                                    <div style="font-size: 12px; color: #334155; font-weight: 500; margin-top: 2px;">
                                        Real-time YOLOv8 neural evaluation confirmed an unauthorized human in the designated room area.
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </div>

                    <!-- Overview 3-Metric Strip (Matching UI 3-Card Strip) -->
                    <div style="padding: 0 24px; margin-bottom: 20px;">
                        <table style="width: 100%; border-collapse: separate; border-spacing: 8px 0;">
                            <tr>
                                <td style="width: 33.3%; background-color: #f8fafc; border: 1px solid #eef2f6; border-radius: 16px; padding: 12px; vertical-align: top;">
                                    <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.3px;">Timestamp</div>
                                    <div style="font-size: 12px; font-weight: 800; color: #0f172a; margin-top: 4px; font-family: monospace;">
                                        {formatted_time.split(' ')[1] if ' ' in formatted_time else formatted_time}
                                    </div>
                                    <div style="font-size: 10px; color: #64748b; margin-top: 2px;">
                                        {formatted_time.split(' ')[0] if ' ' in formatted_time else ''}
                                    </div>
                                </td>

                                <td style="width: 33.3%; background-color: #f8fafc; border: 1px solid #eef2f6; border-radius: 16px; padding: 12px; vertical-align: top;">
                                    <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.3px;">Targets</div>
                                    <div style="font-size: 13px; font-weight: 800; color: #e11d48; margin-top: 4px;">
                                        {person_count} Person(s)
                                    </div>
                                    <div style="font-size: 10px; color: #e11d48; font-weight: 600; margin-top: 2px;">
                                        In Zone
                                    </div>
                                </td>

                                <td style="width: 33.3%; background-color: #f8fafc; border: 1px solid #eef2f6; border-radius: 16px; padding: 12px; vertical-align: top;">
                                    <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.3px;">Confidence</div>
                                    <div style="font-size: 13px; font-weight: 800; color: #4338ca; margin-top: 4px;">
                                        {confidence_pct}%
                                    </div>
                                    <div style="font-size: 10px; color: #16a34a; font-weight: 600; margin-top: 2px;">
                                        Debounced
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </div>

                    <!-- Incident Snapshot Card -->
                    <div style="padding: 0 24px; margin-bottom: 24px;">
                        <div style="font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 8px;">
                            Camera Optical Snapshot
                        </div>
                        <div style="background-color: #000000; border-radius: 20px; overflow: hidden; border: 1px solid #e2e8f0; text-align: center; box-shadow: inset 0 2px 6px rgba(0,0,0,0.2);">
                            <img src="cid:snapshot_image" style="width: 100%; max-width: 552px; display: block; margin: 0 auto; vertical-align: middle;" alt="Incident Snapshot" />
                        </div>
                    </div>

                    <!-- Action Button -->
                    <div style="text-align: center; padding: 0 24px 28px 24px;">
                        <a href="http://localhost:8000" style="display: inline-block; background-color: #0f172a; color: #ffffff; text-decoration: none; font-size: 13px; font-weight: 700; padding: 12px 32px; border-radius: 9999px; box-shadow: 0 4px 14px rgba(15, 23, 42, 0.25);">
                            Open Security Dashboard →
                        </a>
                    </div>

                    <!-- Sleek Clean Footer -->
                    <div style="background-color: #fafbfc; border-top: 1px solid #f1f5f9; padding: 16px 24px; text-align: center;">
                        <div style="font-size: 11px; font-weight: 600; color: #64748b;">
                            Argus Autonomous Intruder Detection System
                        </div>
                        <div style="font-size: 10px; color: #94a3b8; margin-top: 3px;">
                            Anti-spam rate limit active (45s window) • Debounce verified across 4 frames
                        </div>
                    </div>

                </div>
            </body>
            </html>
            """
            msg_alternative = MIMEMultipart("alternative")
            msg.attach(msg_alternative)
            msg_alternative.attach(MIMEText(html_content, "html"))

            # Attach snapshot image with Content-ID for inline email view
            if os.path.exists(snapshot_path):
                with open(snapshot_path, "rb") as f:
                    img_data = f.read()
                    img = MIMEImage(img_data)
                    img.add_header("Content-ID", "<snapshot_image>")
                    img.add_header("Content-Disposition", "inline", filename=os.path.basename(snapshot_path))
                    msg.attach(img)

            # Transmit via SMTP
            if use_ssl:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=12) as server:
                    server.login(username, password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=12) as server:
                    if use_tls:
                        server.starttls()
                    server.login(username, password)
                    server.send_message(msg)

            print(f"[Notifier] Successfully dispatched security alert email to {recipient}!")
        except Exception as e:
            print(f"[Notifier] Error sending alert email: {e}")

    def test_smtp_connection(self) -> Dict[str, Any]:
        """Performs a test transmission to verify SMTP server credentials."""
        cfg = config_manager.config
        smtp_server = cfg.get("smtp_server", "smtp.gmail.com")
        smtp_port = int(cfg.get("smtp_port", 587))
        username = cfg.get("smtp_username", "").strip()
        password = cfg.get("smtp_password", "").strip()
        recipient = cfg.get("smtp_recipient", "").strip()
        use_tls = cfg.get("smtp_use_tls", True)
        use_ssl = cfg.get("smtp_use_ssl", False)

        if not username or not password or not recipient:
            return {
                "success": False,
                "message": "SMTP Username, Password, and Recipient Email must not be empty."
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Argus System: SMTP Connectivity Verified"
            msg["From"] = f"Argus Security System <{username}>"
            msg["To"] = recipient

            test_html = f"""
            <!DOCTYPE html>
            <html>
            <body style="margin: 0; padding: 32px 12px; background-color: #f3f4f7; font-family: -apple-system, BlinkMacSystemFont, 'Plus Jakarta Sans', 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
                <div style="max-width: 540px; margin: 0 auto; background-color: #ffffff; border-radius: 28px; border: 1px solid #eef1f6; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05); overflow: hidden; padding: 28px;">
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a; margin-bottom: 4px;">
                        ARGUS <span style="font-size: 10px; font-weight: 700; background-color: #f1f5f9; color: #475569; padding: 2px 7px; border-radius: 9999px;">TEST</span>
                    </div>
                    <div style="margin: 18px 0; padding: 18px; border-radius: 18px; background: linear-gradient(135deg, #a5b4fc 0%, #c4b5fd 30%, #bae6fd 70%, #bbf7d0 100%);">
                        <div style="font-size: 16px; font-weight: 900; color: #0f172a;">SMTP Dispatch Verified ✅</div>
                        <div style="font-size: 12px; color: #334155; margin-top: 4px;">Your email alert service is successfully configured and standing by.</div>
                    </div>
                    <p style="font-size: 12px; color: #64748b; line-height: 1.5;">
                        When the perimeter monitoring system is armed and an unauthorized intruder is detected, incident alerts with snapshots will be dispatched to this email address automatically.
                    </p>
                    <div style="margin-top: 20px; font-size: 11px; color: #94a3b8; text-align: center;">
                        Argus Autonomous Security Sentinel • System Test
                    </div>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(test_html, "html"))

            if use_ssl:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10) as server:
                    server.login(username, password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                    if use_tls:
                        server.starttls()
                    server.login(username, password)
                    server.send_message(msg)

            return {"success": True, "message": f"Test email sent successfully to {recipient}!"}
        except Exception as e:
            return {"success": False, "message": f"SMTP Connection Failed: {str(e)}"}


notifier = EmailNotifier()
