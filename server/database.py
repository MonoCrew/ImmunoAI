"""
ImmunoAI — SQLite Database Storage for Intruder Incidents & Snapshots
Stores detection history, confidence scores, timestamps, and snapshot file paths.
"""

import sqlite3
import time
from config import DB_PATH


def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        camera TEXT NOT NULL DEFAULT 'Attached System Camera',
        confidence TEXT NOT NULL,
        threat_level TEXT NOT NULL,
        image TEXT NOT NULL,
        details TEXT NOT NULL,
        box_coords TEXT DEFAULT '32,22,34,58',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Seed initial sample incidents if table is empty
    cursor.execute("SELECT COUNT(*) FROM incidents")
    count = cursor.fetchone()[0]

    if count == 0:
        initial_samples = [
            (
                "Today, 10:14 PM",
                "Attached System Camera",
                "98.4%",
                "High Alert",
                "https://images.unsplash.com/photo-1509114397022-ed747cca3f65?w=600&auto=format&fit=crop&q=80",
                "Unauthorized motion detected near main entrance while Protection Mode was ARMED.",
                "32,22,34,58"
            ),
            (
                "Today, 08:35 PM",
                "Attached System Camera",
                "96.2%",
                "Breach Detected",
                "https://images.unsplash.com/photo-1544717305-2782549b5136?w=600&auto=format&fit=crop&q=80",
                "Person detected within perimeter zone during armed surveillance hours.",
                "28,18,38,65"
            ),
            (
                "Yesterday, 11:42 PM",
                "Attached System Camera",
                "94.8%",
                "High Alert",
                "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=600&auto=format&fit=crop&q=80",
                "Night breach detected. Verified with Deep CNN inference.",
                "35,25,30,52"
            ),
            (
                "Yesterday, 09:15 PM",
                "Attached System Camera",
                "97.5%",
                "Breach Detected",
                "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&auto=format&fit=crop&q=80",
                "Perimeter line-crossing event triggered audio siren.",
                "24,20,36,60"
            ),
        ]

        cursor.executemany("""
        INSERT INTO incidents (timestamp, camera, confidence, threat_level, image, details, box_coords)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, initial_samples)

    conn.commit()
    conn.close()


def add_incident(confidence: str, threat_level: str, image_url: str, details: str, box: str = "30,20,35,60"):
    conn = get_db_connection()
    cursor = conn.cursor()

    timestamp_str = f"Today, {time.strftime('%I:%M %p')}"

    cursor.execute("""
    INSERT INTO incidents (timestamp, camera, confidence, threat_level, image, details, box_coords)
    VALUES (?, 'Attached System Camera', ?, ?, ?, ?, ?)
    """, (timestamp_str, confidence, threat_level, image_url, details, box))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": f"snap-{new_id}",
        "timestamp": timestamp_str,
        "camera": "Attached System Camera",
        "confidence": confidence,
        "threatLevel": threat_level,
        "image": image_url,
        "details": details,
        "box": [int(x) for x in box.split(",")]
    }


def get_all_incidents():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM incidents ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        coords = [int(x) for x in row["box_coords"].split(",")] if row["box_coords"] else [30, 20, 35, 60]
        results.append({
            "id": f"snap-{row['id']}",
            "timestamp": row["timestamp"],
            "camera": row["camera"],
            "confidence": row["confidence"],
            "threatLevel": row["threat_level"],
            "image": row["image"],
            "details": row["details"],
            "box": coords
        })

    return results


if __name__ == "__main__":
    init_db()
    print("[Database] Initialized SQLite database successfully!")
