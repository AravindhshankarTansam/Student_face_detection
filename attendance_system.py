"""
Enhanced AI-Powered Facial Recognition Attendance and Fire Evacuation System
Complete Flask Web Application with Interactive Camera Module
"""

import cv2
import face_recognition
import numpy as np
import sqlite3
import pickle
from datetime import datetime
from flask import Flask, render_template_string, Response, request, jsonify, redirect, url_for
import time
import uuid
import threading

# ============================================================================
# Database Manager
# ============================================================================

class AttendanceDB:
    def __init__(self, db_path="last_attendance_system.db"):
        self.db_path = db_path
        self.init_db()
        self.migrate_db()  # Add migration support
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                employee_id TEXT UNIQUE NOT NULL,
                registered_date TEXT NOT NULL
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS face_encodings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                encoding BLOB NOT NULL,
                angle TEXT NOT NULL,
                FOREIGN KEY (person_id) REFERENCES persons(id)
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                FOREIGN KEY (person_id) REFERENCES persons(id),
                UNIQUE(person_id, date)
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS evacuation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                total_building INTEGER NOT NULL,
                total_evacuated INTEGER DEFAULT 0
            )
        """)
                # New table for storing login logs
        c.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                login_time TEXT NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (person_id) REFERENCES persons(id)
            )
        """)

        conn.commit()
        conn.close()
    
    def migrate_db(self):
        """Add missing columns to existing database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Check if angle column exists
            c.execute("PRAGMA table_info(face_encodings)")
            columns = [column[1] for column in c.fetchall()]
            
            if 'angle' not in columns:
                print("⚙️  Migrating database: Adding 'angle' column...")
                c.execute("ALTER TABLE face_encodings ADD COLUMN angle TEXT DEFAULT 'front'")
                conn.commit()
                print("✓ Database migration completed successfully")
        except Exception as e:
            print(f"⚠️  Migration error: {e}")
        finally:
            conn.close()
    
    def register_person(self, name, employee_id, face_encodings_dict):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO persons (name, employee_id, registered_date)
                VALUES (?, ?, ?)
            """, (name, employee_id, datetime.now().isoformat()))
            
            person_id = c.lastrowid
            
            for angle, face_image in face_encodings_dict.items():
                # Store face image as pickle blob
                encoding_blob = pickle.dumps(face_image)
                c.execute("""
                    INSERT INTO face_encodings (person_id, encoding, angle)
                    VALUES (?, ?, ?)
                """, (person_id, encoding_blob, angle))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_all_face_encodings(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT p.id, p.name, p.employee_id, fe.encoding
            FROM persons p
            JOIN face_encodings fe ON p.id = fe.person_id
        """)
        
        rows = c.fetchall()
        encodings, person_ids, names = [], [], []
        
        for row in rows:
            person_ids.append(row[0])
            names.append(row[1])
            encodings.append(pickle.loads(row[3]))
        
        conn.close()
        return encodings, person_ids, names
    
    def mark_attendance(self, person_id):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            today = datetime.now().date().isoformat()
            now = datetime.now().isoformat()
            
            c.execute("""
                INSERT INTO attendance (person_id, date, entry_time)
                VALUES (?, ?, ?)
            """, (person_id, today, now))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def log_login(self, person_id, name, employee_id):
        """Store a login record when a face is successfully recognized"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now()
        date = now.date().isoformat()
        time_now = now.strftime("%H:%M:%S")

        c.execute("""
            INSERT INTO login_logs (person_id, name, employee_id, login_time, date)
            VALUES (?, ?, ?, ?, ?)
        """, (person_id, name, employee_id, time_now, date))

        conn.commit()
        conn.close()


    def get_today_attendance(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        c.execute("""
            SELECT p.id, p.name, p.employee_id, a.entry_time
            FROM persons p
            JOIN attendance a ON p.id = a.person_id
            WHERE a.date = ?
        """, (today,))
        
        rows = c.fetchall()
        conn.close()
        
        return [{'id': r[0], 'name': r[1], 'employee_id': r[2], 'entry_time': r[3]} for r in rows]
    
    def get_all_persons(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT id, name, employee_id, registered_date FROM persons")
        rows = c.fetchall()
        conn.close()
        
        return [{'id': r[0], 'name': r[1], 'employee_id': r[2], 'registered_date': r[3]} for r in rows]
    
    def start_evacuation_event(self, total_building):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        event_id = str(uuid.uuid4())[:8]
        
        c.execute("""
            INSERT INTO evacuation_events (event_id, start_time, total_building)
            VALUES (?, ?, ?)
        """, (event_id, datetime.now().isoformat(), total_building))
        
        conn.commit()
        conn.close()
        return event_id
    
    def update_evacuation_count(self, event_id, count):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            UPDATE evacuation_events
            SET total_evacuated = ?
            WHERE event_id = ?
        """, (count, event_id))
        
        conn.commit()
        conn.close()


# ============================================================================
# Face Processor
# ============================================================================

class FaceProcessor:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        # ADD THIS LINE:
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )

        # Initialize LBPH Face Recognizer
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create(
                radius=1,
                neighbors=8,
                grid_x=8,
                grid_y=8
            )
        except AttributeError:
            print("ERROR: opencv-contrib-python not installed!")
            print("Run: pip install opencv-contrib-python")
            self.recognizer = None

        self.is_trained = False
        self.label_map = {}
    def detect_faces(self, frame):
        """Detect faces using Haar Cascade"""
        if frame is None or frame.size == 0:
            return []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )
        
        # Convert to format: [(top, right, bottom, left), ...]
        face_locations = []
        for (x, y, w, h) in faces:
            face_locations.append((y, x+w, y+h, x))
        
        return face_locations
    
    def load_known_faces(self, db):
        """Load known faces and train recognizer"""
        if self.recognizer is None:
            return
            
        encodings, ids, names = db.get_all_face_encodings()
        
        if not encodings:
            self.is_trained = False
            return
        
        self.label_map = {}
        faces = []
        labels = []
        
        # Build unique person map
        person_map = {}
        for person_id, name, encoding in zip(ids, names, encodings):
            if person_id not in person_map:
                person_map[person_id] = name
            
            faces.append(encoding)
            labels.append(person_id)
        
        self.label_map = person_map
        
        if faces and labels:
            self.recognizer.train(faces, np.array(labels))
            self.is_trained = True
            print(f"✓ Trained recognizer with {len(faces)} face samples from {len(person_map)} people")
    
    def recognize_face(self, frame):
        """Recognize faces in frame with enhanced validation"""
        if frame is None or frame.size == 0:
            return []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # More conservative face detection parameters
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.3,  # Increased from 1.2 for fewer false positives
            minNeighbors=6,   # Increased from 5 for stricter detection
            minSize=(60, 60),  # Increased minimum size
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        results = []
        
        for (x, y, w, h) in faces:
            # VALIDATION 1: Aspect ratio check (faces are roughly square)
            aspect_ratio = w / float(h)
            if aspect_ratio < 0.7 or aspect_ratio > 1.3:
                continue  # Skip non-face-like rectangles
            
            # VALIDATION 2: Check if region has face-like characteristics
            face_roi = gray[y:y+h, x:x+w]
            
            # Check variance - faces have more texture than uniform objects
            variance = np.var(face_roi)
            if variance < 200:  # Too uniform, likely not a face
                continue
            
            # VALIDATION 3: Eye detection (optional but very effective)
            # Load eye cascade if not already loaded
            if not hasattr(self, 'eye_cascade'):
                self.eye_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_eye.xml'
                )
            
            # Look for eyes in upper half of detected region
            eye_region = face_roi[0:int(h*0.6), :]
            eyes = self.eye_cascade.detectMultiScale(
                eye_region,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(15, 15)
            )
            
            # If no eyes detected, likely not a face
            if len(eyes) < 1:
                continue
            
            person_id = None
            name = "Unknown"
            confidence = 0.0
            
            if self.is_trained and self.recognizer is not None:
                face_resized = cv2.resize(face_roi, (200, 200))
                
                try:
                    label, conf = self.recognizer.predict(face_resized)
                    
                    # Stricter confidence threshold
                    if conf < 50:  # Reduced from 60 for better accuracy
                        person_id = label
                        name = self.label_map.get(label, "Unknown")
                        confidence = 1 - (conf / 100)
                except Exception as e:
                    print(f"Recognition error: {e}")
            
            results.append({
                'person_id': person_id,
                'name': name,
                'confidence': confidence,
                'box': (x, y, x+w, y+h)
            })
        
        return results
        

# ============================================================================
# Line Crossing Detector
# ============================================================================



# ============================================================================
# Camera Manager
# ============================================================================

class CameraManager:
    def __init__(self):
        self.camera = None
        self.is_running = False
        self.mode = None
        self.frame = None
        self.lock = threading.Lock()
        self.frame_thread = None
    
    def start_camera(self, camera_index=0):
        if self.camera is None or not self.camera.isOpened():
            # Try different camera indices
            for idx in [camera_index, 0, 1]:
                self.camera = cv2.VideoCapture(idx)
                if self.camera.isOpened():
                    print(f"✓ Camera opened successfully on index {idx}")
                    break
                self.camera.release()
            
            if not self.camera.isOpened():
                print("✗ Failed to open camera")
                return False
            
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.is_running = True
            
            # Start continuous frame capture thread
            self.frame_thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.frame_thread.start()
            
            # Wait for first frame
            time.sleep(0.5)
            return True
        return True
    
    def _capture_frames(self):
        """Continuously capture frames in background thread"""
        while self.is_running:
            if self.camera and self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret:
                    with self.lock:
                        self.frame = frame.copy()
            time.sleep(0.03)  # ~30 FPS
    
    def stop_camera(self):
        self.is_running = False
        if self.frame_thread:
            self.frame_thread.join(timeout=1.0)
        if self.camera:
            self.camera.release()
            self.camera = None
        self.frame = None
    
    def read_frame(self):
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
        return None

# ============================================================================
# Flask Application
# ============================================================================

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Global instances
db = AttendanceDB()
processor = FaceProcessor()
camera_manager = CameraManager()


# State variables
registration_encodings = {}
current_registration_name = None
current_registration_id = None
last_marked = {}
cooldown = 30
evacuation_event_id = None
total_building = 0
evacuated_persons = set()  # ADD THIS - Track unique evacuated person IDs
evacuation_cooldown = {}   # ADD THIS - Prevent duplicate counting
EVACUATION_COOLDOWN_TIME = 30  # ADD THIS - 30 seconds cooldown
total_building = 0
full_view_capturing = False
full_view_progress = 0


# ============================================================================
# HTML Templates
# ============================================================================
INDEX_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TANSAM - Smart Attendance & Evacuation System</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: 'Segoe UI', Roboto, sans-serif;
    }

    body {
      background: linear-gradient(135deg, #eef2f3, #dfe9f3);
      color: #333;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* 🔹 Navbar */
    header {
      background: #ffffff;
      color: #004e92;
      padding: 15px 50px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
      position: sticky;
      top: 0;
      z-index: 1000;
      border-bottom: 3px solid #00b4db;
    }

    .logo {
      display: flex;
      align-items: baseline;
      gap: 8px;
    }

    .logo .main-text {
      font-size: 1.8em;
      font-weight: 700;
      color: #004e92;
      letter-spacing: 1px;
    }

    .logo .sub-text {
      font-size: 0.9em;
      font-weight: 500;
      color: #00b4db;
      letter-spacing: 0.5px;
    }

    nav {
      display: flex;
      gap: 30px;
      align-items: center;
    }

    nav a {
      color: #004e92;
      text-decoration: none;
      font-weight: 500;
      position: relative;
      padding-bottom: 3px;
      transition: all 0.3s ease;
    }

    nav a:hover {
      color: #00b4db;
    }

    nav a::after {
      content: '';
      position: absolute;
      left: 0;
      bottom: 0;
      height: 2px;
      width: 0%;
      background: #00b4db;
      transition: width 0.3s ease;
    }

    nav a:hover::after {
      width: 100%;
    }

    /* 🔹 Hamburger Menu */
    .menu-toggle {
      display: none;
      flex-direction: column;
      cursor: pointer;
      gap: 5px;
    }

    .menu-toggle span {
      width: 25px;
      height: 3px;
      background: #004e92;
      border-radius: 5px;
      transition: all 0.3s ease;
    }

    /* 🔹 Hero Section */
    .hero {
      text-align: center;
      padding: 80px 20px 50px;
      background: linear-gradient(135deg, #e0f7fa, #f0faff);
      border-bottom: 3px solid #00b4db;
      animation: fadeUp 1.2s ease;
    }

    .hero h1 {
      font-size: 2em;
      color: #004e92;
      margin-bottom: 10px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }

    .hero h2 {
      font-size: 1.2em;
      color: #00b4db;
      margin-bottom: 20px;
      font-weight: 600;
    }

    .hero p {
      font-size: 1em;
      color: #333;
      max-width: 700px;
      margin: 0 auto 20px;
      line-height: 1.6;
      font-weight: 500;
    }

    .hero .keywords {
      color: #004e92;
      font-weight: 600;
      letter-spacing: 0.5px;
    }

    .hero .highlight {
      color: #00b4db;
      font-weight: 700;
    }

    /* 🔹 Glowing separator */
    .hero::after {
      content: "";
      display: block;
      width: 100px;
      height: 3px;
      background: linear-gradient(90deg, #004e92, #00b4db);
      margin: 25px auto 0;
      border-radius: 5px;
    }

    /* 🔹 Main Container */
    .container {
      flex: 1;
      margin: 60px auto;
      background: #fff;
      border-radius: 20px;
      padding: 40px;
      max-width: 1200px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
      animation: fadeUp 1s ease;
    }

    h2.title {
      text-align: center;
      margin-bottom: 40px;
      font-size: 1.9em;
      color: #004e92;
      position: relative;
    }

    h2.title::after {
      content: "";
      width: 80px;
      height: 3px;
      background: linear-gradient(90deg, #004e92, #00b4db);
      display: block;
      margin: 10px auto 0;
      border-radius: 10px;
    }

    .top-row, .bottom-row {
      display: flex;
      justify-content: center;
      flex-wrap: wrap;
      gap: 30px;
      margin-bottom: 40px;
    }

    .bottom-row { gap: 60px; }

    .card {
      width: 230px;
      background: linear-gradient(145deg, #ffffff, #f3f3f3);
      border-radius: 18px;
      text-align: center;
      padding: 40px 20px;
      text-decoration: none;
      color: #333;
      box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
      transition: all 0.3s ease;
      border: 1px solid #e0e8ff;
    }

    .card:hover {
      transform: translateY(-6px);
      box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
      border-color: #00b4db;
    }

    .icon {
      font-size: 2.8em;
      margin-bottom: 15px;
      color: #004e92;
      transition: transform 0.3s ease;
    }

    .card:hover .icon {
      transform: scale(1.1);
      color: #00b4db;
    }

    .card h3 {
      font-size: 1.2em;
      margin-bottom: 10px;
    }

    .card p {
      font-size: 0.9em;
      opacity: 0.8;
      line-height: 1.4;
    }

    /* 🔹 Footer */
    footer {
      background: #ffffff;
      color: #004e92;
      text-align: center;
      padding: 15px;
      font-size: 0.9em;
      letter-spacing: 0.4px;
      border-top: 2px solid #00b4db;
      box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
    }

    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(30px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 768px) {
      nav {
        position: absolute;
        top: 65px;
        right: 0;
        background: #ffffff;
        flex-direction: column;
        width: 200px;
        padding: 15px;
        gap: 15px;
        display: none;
        border-radius: 10px 0 0 10px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.15);
      }

      nav.show {
        display: flex;
      }

      .menu-toggle {
        display: flex;
      }
    }
  </style>
</head>
<body>

<header>
  <div class="logo">
    <div class="main-text">TANSAM</div>
    <div class="sub-text">Powered by Siemens</div>
  </div>

  <div class="menu-toggle" onclick="toggleMenu()">
    <span></span>
    <span></span>
    <span></span>
  </div>

  <nav id="nav">
    <a href="/">Home</a>
    <a href="/register">Register</a>
    <a href="/attendance">Attendance</a>
    <a href="/login">Login</a>
    <a href="/view_attendance">Reports</a>
    <a href="/view_persons">Employees</a>
  </nav>
</header>


<div class="container">
  <h2 class="title">Smart Attendance System</h2>


  <div class="top-row">
    <a href="/register" class="card">
      <div class="icon">🧑‍💻</div>
      <h3>Register</h3>
      <p>Register new employees with face data securely.</p>
    </a>

    <a href="/attendance" class="card">
      <div class="icon">📋</div>
      <h3>Attendance</h3>
      <p>Mark attendance automatically via face recognition.</p>
    </a>

    <a href="/login" class="card">
      <div class="icon">🔐</div>
      <h3>Face Login</h3>
      <p>Authenticate users through facial verification.</p>
    </a>

    <a href="/evacuation" class="card">
      <div class="icon">🚨</div>
      <h3>Evacuation</h3>
      <p>Detect emergencies and ensure safe evacuation.</p>
    </a>
  </div>

  <div class="bottom-row">
    <a href="/view_attendance" class="card">
      <div class="icon">📊</div>
      <h3>Reports</h3>
      <p>Analyze attendance reports and daily trends.</p>
    </a>

    <a href="/view_persons" class="card">
      <div class="icon">👥</div>
      <h3>Employees</h3>
      <p>Manage and view registered employee profiles.</p>
    </a>
  </div>
</div>

<footer>
  © 2025 TANSAM | Designed by Digital Technology
</footer>

<script>
  function toggleMenu() {
    const nav = document.getElementById('nav');
    nav.classList.toggle('show');
  }
</script>

</body>
</html>
'''

REGISTER_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Register Person</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            background: white;
            border-radius: 25px;
            padding: 40px;
            box-shadow: 0 25px 70px rgba(0,0,0,0.4);
            animation: slideIn 0.5s ease-out;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-50px); }
            to { opacity: 1; transform: translateX(0); }
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 40px;
            font-size: 2.5em;
            font-weight: 700;
        }
        .form-group {
            margin-bottom: 25px;
        }
        label {
            display: block;
            margin-bottom: 10px;
            font-weight: 600;
            color: #333;
            font-size: 1.1em;
        }
        input {
            width: 100%;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .camera-container {
            margin: 30px 0;
            background: #000;
            border-radius: 15px;
            overflow: hidden;
            position: relative;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        #video-feed {
            width: 100%;
            height: auto;
            display: block;
        }
        .angle-buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }
        .angle-btn {
            padding: 20px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            color: white;
            position: relative;
            overflow: hidden;
        }
        .angle-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .angle-btn.front {
            background: linear-gradient(135deg, #667eea, #764ba2);
        }
        .angle-btn.left {
            background: linear-gradient(135deg, #f093fb, #f5576c);
        }
        .angle-btn.right {
            background: linear-gradient(135deg, #4facfe, #00f2fe);
        }
        .angle-btn.up {
            background: linear-gradient(135deg, #43e97b, #38f9d7);
        }
        .angle-btn.down {
            background: linear-gradient(135deg, #fa709a, #fee140);
        }
        .angle-btn:not(:disabled):hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }
        .angle-btn.captured {
            background: linear-gradient(135deg, #56ab2f, #a8e063);
            position: relative;
        }
        .angle-btn.captured::after {
            content: '✓';
            position: absolute;
            top: 5px;
            right: 10px;
            font-size: 24px;
        }
        .button-group {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 30px;
            flex-wrap: wrap;
        }
        button {
            padding: 15px 35px;
            font-size: 17px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background: #5a6268;
            transform: translateY(-2px);
        }
        .btn-success {
            background: linear-gradient(135deg, #56ab2f, #a8e063);
            color: white;
            font-size: 18px;
            padding: 18px 40px;
        }
        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(86, 171, 47, 0.4);
        }
        .status {
            text-align: center;
            padding: 20px;
            margin: 25px 0;
            border-radius: 12px;
            font-weight: 600;
            font-size: 1.1em;
            animation: fadeIn 0.5s;
        }
        .status.info {
            background: linear-gradient(135deg, #d1ecf1, #bee5eb);
            color: #0c5460;
        }
        .status.success {
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            color: #155724;
        }
        .status.error {
            background: linear-gradient(135deg, #f8d7da, #f5c6cb);
            color: #721c24;
        }
        .status.warning {
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            color: #856404;
        }
        #step1, #step2, #step3 {
            display: none;
        }
        .progress-container {
            margin: 25px 0;
        }
        .progress {
            width: 100%;
            height: 40px;
            background: #e9ecef;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.1);
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 16px;
        }
        .instructions {
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            border-left: 5px solid #ffc107;
        }
        .instructions h3 {
            color: #856404;
            margin-bottom: 10px;
            font-size: 1.2em;
        }
        .instructions ul {
            margin-left: 20px;
            color: #856404;
        }
        .instructions li {
            margin: 8px 0;
            line-height: 1.6;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .pulse {
            animation: pulse 2s infinite;
        }
        .capture-mode-selector {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 15px;
        }

        .mode-info {
            animation: fadeIn 0.5s ease-in;
        }

        .arrow-track {
            position: relative;
            width: 100%;
            height: 60px;
            background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb, #1dd1a1);
            border-radius: 30px;
            margin: 20px 0;
            overflow: hidden;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.2);
        }

        .moving-arrow {
            position: absolute;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            font-size: 40px;
            transition: right 15s linear;
            filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));
        }

        .moving-arrow.animating {
            right: calc(100% - 50px);
        }

        .capture-counter {
            text-align: center;
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
            padding: 15px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        #current-capture {
            color: #667eea;
            font-size: 1.2em;
        }

        .full-view-progress {
            margin: 20px 0;
        }

        #progress-text {
            white-space: nowrap;
            padding: 0 10px;
        }

        .progress-bar {
            min-width: 200px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>👤 Register New Person</h1>
        <div id="step1" style="display: block;">
            <div class="instructions">
                <h3>📝 Registration Instructions</h3>
                <ul>
                    <li>Enter your full name and ID</li>
                    <li>You'll capture 5 photos from different angles</li>
                    <li>Follow the on-screen prompts for each angle</li>
                    <li>Ensure good lighting and clear face visibility</li>
                </ul>
            </div>
            <div class="form-group">
                <label>Full Name:</label>
                <input type="text" id="name" placeholder="Enter your full name">
            </div>
            <div class="form-group">
                <label>Employee/Student ID:</label>
                <input type="text" id="employee_id" placeholder="Enter your unique ID">
            </div>
            <div class="button-group">
                <button class="btn-primary" onclick="startRegistration()">🚀 Start Registration</button>
                <button class="btn-secondary" onclick="window.location.href='/'">❌ Cancel</button>
            </div>
        </div>
        <div id="step2">
            <div class="status info" id="capture-status">
                <p>📸 Position your face and select an angle to capture</p>
            </div>
            <div class="progress-container">
                <div class="progress">
                    <div class="progress-bar" id="progress-bar" style="width: 0%">
                      <span id="progress-text">Step 1: 0/5 Manual</span>
                    </div>
                </div>
            </div>
            <div class="camera-container">
                <img src="/video_feed?t=registration" id="video-feed" alt="Camera Feed" style="display:block;">
            </div>
            <div class="capture-mode-selector">
    <h3 style="text-align: center; margin-bottom: 20px; color: #333;">Registration Process:</h3>
    <div class="mode-info" style="text-align: center; padding: 15px; background: linear-gradient(135deg, #d1f2eb, #a8e6cf); border-radius: 10px; margin-bottom: 20px;">
        <p style="color: #155724; font-weight: 600; font-size: 1.1em;">
            📸 Step 1: Capture 5 Key Angles (Manual)<br>
            <small>Then proceed to Step 2</small>
        </p>
    </div>
</div>

    <!-- STEP 1: Manual 5 Angles -->
    <div id="manual-capture-section">
        <div class="angle-buttons">
            <button class="angle-btn front" id="btn-front" onclick="captureAngle('front')">
                📷 Front<br><small>Look straight ahead</small>
            </button>
            <button class="angle-btn left" id="btn-left" onclick="captureAngle('left')">
                ⬅️ Left<br><small>Turn left 45°</small>
            </button>
            <button class="angle-btn right" id="btn-right" onclick="captureAngle('right')">
                ➡️ Right<br><small>Turn right 45°</small>
            </button>
            <button class="angle-btn up" id="btn-up" onclick="captureAngle('up')">
                ⬆️ Look Up<br><small>Tilt head up</small>
            </button>
            <button class="angle-btn down" id="btn-down" onclick="captureAngle('down')">
                ⬇️ Look Down<br><small>Tilt head down</small>
            </button>
        </div>
    </div>

    <!-- STEP 2: Full View Capture -->
    <div id="auto-capture-section" style="display: none;">
        <div class="mode-info" style="text-align: center; padding: 15px; background: linear-gradient(135deg, #fff3cd, #ffeaa7); border-radius: 10px; margin-bottom: 20px;">
            <p style="color: #856404; font-weight: 600; font-size: 1.1em;">
                🎬 Step 2: Full View Capture (45 images)<br>
                <small>Move from RIGHT to LEFT</small>
            </p>
        </div>
        
        <div class="instructions" style="background: linear-gradient(135deg, #d1f2eb, #a8e6cf);">
            <h3 style="color: #155724;">🎬 Full View Instructions</h3>
            <ul style="color: #155724;">
                <li>Click "Start Full Capture" below</li>
                <li>Stand on the RIGHT side of the camera view</li>
                <li>Slowly move from RIGHT to LEFT following the arrow</li>
                <li>Keep your face visible at all times</li>
                <li>Complete the movement within 15 seconds</li>
            </ul>
        </div>
        
        <div class="full-view-progress" id="full-view-progress" style="display: none;">
            <div class="arrow-track">
                <div class="moving-arrow" id="moving-arrow">➡️</div>
            </div>
            <div class="capture-counter" id="capture-counter">
                Capturing: <span id="current-capture">0</span> / 45
            </div>
        </div>
        
        <button class="angle-btn" id="start-full-capture-btn" onclick="startFullCapture()" 
                style="background: linear-gradient(135deg, #56ab2f, #a8e063); width: 100%; max-width: 400px; margin: 20px auto; display: block; padding: 25px;">
            🎬 Start Full Capture<br><small>45 images in 15 seconds</small>
        </button>
        
        <div style="text-align: center; margin-top: 20px;">
            <p style="color: #666; font-size: 0.9em;">After full capture completes, click "Complete Registration" below</p>
        </div>
    </div>
            <div class="button-group">
                <button class="btn-success" onclick="completeRegistration()" id="complete-btn" disabled>
                    ✅ Complete Registration
                </button>
                <button class="btn-secondary" onclick="cancelRegistration()">❌ Cancel</button>
            </div>
        </div>
        <div id="step3">
            <div class="status success">
                <p>🎉 Registration Completed Successfully!</p>
                <p style="margin-top: 10px; font-size: 0.9em;">You can now use the attendance system</p>
            </div>
            <div class="button-group">
                <button class="btn-primary" onclick="window.location.href='/'">🏠 Back to Home</button>
                <button class="btn-secondary" onclick="window.location.reload()">➕ Register Another Person</button>
            </div>
        </div>
    </div>
    <script>
        let name, employee_id;
        let capturedAngles = [];
        const requiredAngles = ['front', 'left', 'right', 'up', 'down'];
        let manualCapturesComplete = false;
        let fullViewCapturesComplete = false;
        let fullViewInterval = null;
        const REQUIRED_MANUAL = 5;
        const REQUIRED_FULL_VIEW = 45;
        
    function startRegistration() {
     name = document.getElementById('name').value.trim();
     employee_id = document.getElementById('employee_id').value.trim();

     if (!name || !employee_id) {
      alert('⚠️ Please enter both name and ID');
      return;
     }

     if (name.length < 2) {
       alert('⚠️ Name must be at least 2 characters');
       return;
     }

     fetch('/api/start_registration', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, employee_id})
     })
     .then(res => res.json())
     .then(data => {
     if (data.success) {
        document.getElementById('step1').style.display = 'none';
        document.getElementById('step2').style.display = 'block';
        updateStatus('info', '⏳ Initializing camera... Please wait.');
        
        // Force reload video feed with cache buster
        const videoFeed = document.getElementById('video-feed');
        videoFeed.src = '/video_feed?t=registration&' + new Date().getTime();
        
        // Wait for camera to be ready
        setTimeout(() => {
            updateStatus('info', '📸 Camera ready! Capture your face from all 5 angles. Start with the FRONT view!');
        }, 2000);
     } else {
        alert('❌ ' + data.message);
     }
     })
     .catch(err => {
      alert('❌ Error: ' + err.message);
      });
    }
        
        function captureAngle(angle) {
            if (capturedAngles.includes(angle)) {
                alert('✓ This angle has already been captured!');
                return;
            }
            
            const btn = document.getElementById('btn-' + angle);
            btn.disabled = true;
            btn.textContent = 'Capturing...';
            
            fetch('/api/capture_face', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({angle: angle})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    capturedAngles.push(angle);
                    btn.classList.add('captured');
                    btn.disabled = false;
                    
                    const angleNames = {
                        'front': 'Front',
                        'left': 'Left',
                        'right': 'Right',
                        'up': 'Look Up',
                        'down': 'Look Down'
                    };
                    btn.innerHTML = `✓ ${angleNames[angle]}<br><small>Captured!</small>`;
                    
                    // Update progress
                    updateOverallProgress();
                    
                    if (capturedAngles.length >= REQUIRED_MANUAL) {
                        manualCapturesComplete = true;
                        updateStatus('success', '🎉 Step 1 Complete! Now proceed to Step 2 - Full View Capture');
                        
                        // Show Step 2
                        document.getElementById('auto-capture-section').style.display = 'block';
                        
                        // Scroll to Step 2
                        document.getElementById('auto-capture-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
                    } else {
                        const remaining = REQUIRED_MANUAL - capturedAngles.length;
                        updateStatus('info', `✅ ${angleNames[angle]} captured! ${remaining} more angle(s) to go.`);
                    }
                } else {
                    btn.disabled = false;
                    btn.innerHTML = `${btn.innerHTML.split('<br>')[0]}<br><small>Try again</small>`;
                    alert('❌ ' + data.message);
                }
            })
            .catch(err => {
                btn.disabled = false;
                alert('❌ Error: ' + err.message);
            });
        }
        
        function completeRegistration() {
            if (!manualCapturesComplete) {
                alert('⚠️ Please complete Step 1 (5 manual angles) first!');
                return;
            }
            
            if (!fullViewCapturesComplete) {
                alert('⚠️ Please complete Step 2 (full view capture) first!');
                return;
            }
            
            updateStatus('info', '⏳ Processing all 50 images... Please wait.');
            document.getElementById('complete-btn').disabled = true;
            
            fetch('/api/complete_registration', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, employee_id})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('step2').style.display = 'none';
                    document.getElementById('step3').style.display = 'block';
                } else {
                    alert('❌ Registration failed: ' + data.message);
                    document.getElementById('complete-btn').disabled = false;
                }
            })
            .catch(err => {
                alert('❌ Error: ' + err.message);
                document.getElementById('complete-btn').disabled = false;
            });
        }
        function cancelRegistration() {
            if (confirm('⚠️ Are you sure you want to cancel? All captured photos will be lost.')) {
                window.location.href = '/stop_camera';
            }
        }
        
        function updateStatus(type, message) {
            const statusDiv = document.getElementById('capture-status');
            statusDiv.className = 'status ' + type;
            statusDiv.innerHTML = '<p>' + message + '</p>';
        }

        function updateOverallProgress() {
            const manualCount = capturedAngles.length;
            const fullViewCount = fullViewCapturesComplete ? REQUIRED_FULL_VIEW : 0;
            const totalCaptured = manualCount + fullViewCount;
            const totalRequired = REQUIRED_MANUAL + REQUIRED_FULL_VIEW;
            
            const percentage = (totalCaptured / totalRequired) * 100;
            document.getElementById('progress-bar').style.width = percentage + '%';
            
            let progressText = '';
            if (!manualCapturesComplete) {
                progressText = `Step 1: ${manualCount}/${REQUIRED_MANUAL} Manual`;
            } else if (!fullViewCapturesComplete) {
                progressText = `Step 1: ✓ | Step 2: In Progress`;
            } else {
                progressText = `Complete: ${totalCaptured}/${totalRequired} Images`;
            }
            
            document.getElementById('progress-text').textContent = progressText;
            
            // Enable complete button only when both steps are done
            const completeBtn = document.getElementById('complete-btn');
            if (manualCapturesComplete && fullViewCapturesComplete) {
                completeBtn.disabled = false;
                completeBtn.classList.add('pulse');
                updateStatus('success', '🎉 All 50 images captured! Click "Complete Registration" to finish.');
            }
        }

        function startFullCapture() {
            if (!manualCapturesComplete) {
                alert('⚠️ Please complete Step 1 (5 manual angles) first!');
                return;
            }
            
            const btn = document.getElementById('start-full-capture-btn');
            btn.disabled = true;
            btn.innerHTML = '⏳ Preparing...<br><small>Get ready!</small>';
            
            updateStatus('warning', '🎬 Get ready! Stand on the RIGHT side of the camera...');
            
            // 3 second countdown
            let countdown = 3;
            const countdownInterval = setInterval(() => {
                updateStatus('warning', `🎬 Starting in ${countdown}...`);
                countdown--;
                
                if (countdown < 0) {
                    clearInterval(countdownInterval);
                    beginFullCapture();
                }
            }, 1000);
        }

        function beginFullCapture() {
            updateStatus('info', '🎬 CAPTURING! Move slowly from RIGHT to LEFT following the arrow!');
            
            // Show progress indicators
            document.getElementById('full-view-progress').style.display = 'block';
            document.getElementById('moving-arrow').classList.add('animating');
            
            let captureCount = 0;
            const captureInterval = 333; // ~15 seconds / 45 captures = 333ms
            
            fullViewInterval = setInterval(() => {
                captureFullViewFrame(captureCount);
                captureCount++;
                
                document.getElementById('current-capture').textContent = captureCount;
                
                if (captureCount >= REQUIRED_FULL_VIEW) {
                    clearInterval(fullViewInterval);
                    completeFullCapture();
                }
            }, captureInterval);
        }

        function captureFullViewFrame(index) {
            fetch('/api/capture_full_view_frame', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({frame_index: index})
            })
            .then(res => res.json())
            .then(data => {
                if (!data.success) {
                    console.error('Frame capture failed:', data.message);
                }
            })
            .catch(err => {
                console.error('Error capturing frame:', err);
            });
        }

        function completeFullCapture() {
            document.getElementById('moving-arrow').classList.remove('animating');
            fullViewCapturesComplete = true;
            
            updateOverallProgress();
            updateStatus('success', '🎉 Step 2 Complete! All 50 images captured. Click "Complete Registration" below.');
            
            document.getElementById('start-full-capture-btn').disabled = true;
            document.getElementById('start-full-capture-btn').innerHTML = '✅ Captured<br><small>45 images complete!</small>';
            document.getElementById('start-full-capture-btn').style.background = 'linear-gradient(135deg, #28a745, #20c997)';
            
            // Scroll to complete button
            document.getElementById('complete-btn').scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
          // Auto-refresh video feed to prevent freezing
        setInterval(function() {
            if (document.getElementById('step2').style.display === 'block') {
             const videoFeed = document.getElementById('video-feed');
             const currentTime = new Date().getTime();
             // Update src with cache buster
             const baseSrc = '/video_feed?t=registration';
             videoFeed.src = baseSrc + '&rand=' + currentTime;
             }
         }, 15000); // Refresh every 15 seconds


        const observer = new MutationObserver(function(mutations) {
             mutations.forEach(function(mutation) {
               if (mutation.target.id === 'step2' && 
                  mutation.target.style.display === 'block') {
                  const videoFeed = document.getElementById('video-feed');
                  videoFeed.src = '/video_feed?t=registration&rand=' + new Date().getTime();
                }
             });
        });

         const step2Element = document.getElementById('step2');
            if (step2Element) {
                observer.observe(step2Element, {
                  attributes: true,
                  attributeFilter: ['style']
                 });
         }
    </script>
</body>
</html>'''

ATTENDANCE_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Attendance Mode</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 25px;
            padding: 40px;
            box-shadow: 0 25px 70px rgba(0,0,0,0.4);
            animation: fadeIn 0.6s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
            font-weight: 700;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-bottom: 35px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 15px;
            color: white;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-card h3 {
            font-size: 3.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        .stat-card p {
            opacity: 0.95;
            font-size: 1.1em;
            letter-spacing: 0.5px;
        }
        .camera-container {
            background: #000;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 30px;
            box-shadow: 0 15px 50px rgba(0,0,0,0.4);
            border: 3px solid #667eea;
            position: relative;
        }
        .camera-container::before {
            content: '🔴 LIVE';
            position: absolute;
            top: 15px;
            left: 15px;
            background: rgba(255, 0, 0, 0.8);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: bold;
            z-index: 10;
            font-size: 14px;
            animation: blink 2s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        #video-feed {
            width: 100%;
            height: auto;
            display: block;
        }
        .button-group {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        button {
            padding: 15px 35px;
            font-size: 17px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }
        .btn-danger {
            background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
            color: white;
        }
        .btn-primary:hover, .btn-danger:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        }
        .people-list {
            max-height: 400px;
            overflow-y: auto;
            margin-top: 30px;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            padding: 20px;
            background: #f8f9fa;
        }
        .people-list h3 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        .person-item {
            padding: 15px;
            margin-bottom: 12px;
            background: white;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s;
            animation: slideIn 0.5s ease-out;
        }
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        .person-item:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .person-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .person-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.5em;
            font-weight: bold;
        }
        .person-details strong {
            display: block;
            color: #333;
            font-size: 1.1em;
        }
        .person-details small {
            color: #666;
        }
        .person-time {
            color: #667eea;
            font-weight: 600;
        }
        .no-data {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        .people-list::-webkit-scrollbar {
            width: 8px;
        }
        .people-list::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        .people-list::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Attendance Monitoring</h1>
        <div class="stats">
            <div class="stat-card">
                <h3 id="total-count">0</h3>
                <p>📊 People Present Today</p>
            </div>
        </div>
        <div class="camera-container">
            <img src="/video_feed" id="video-feed" alt="Live Camera Feed">
        </div>
        <div class="button-group">
            <button class="btn-primary" onclick="window.location.href='/view_attendance'">
                📊 View Full Report
            </button>
            <button class="btn-danger" onclick="stopAttendance()">
                ⏹️ Stop & Return Home
            </button>
        </div>
        <div class="people-list" id="people-list">
            <h3>👥 Today's Attendance</h3>
            <div class="no-data">No attendance records yet...</div>
        </div>
    </div>
    <script>
        function updateStats() {
            fetch('/api/attendance_stats')
            .then(res => res.json())
            .then(data => {
                document.getElementById('total-count').textContent = data.total;
                const listDiv = document.getElementById('people-list');
                if (data.people.length > 0) {
                    listDiv.innerHTML = '<h3>👥 Today\'s Attendance</h3>';
                    data.people.forEach(person => {
                        const time = new Date(person.entry_time).toLocaleTimeString();
                        const initial = person.name.charAt(0).toUpperCase();
                        listDiv.innerHTML += `
                            <div class="person-item">
                                <div class="person-info">
                                    <div class="person-avatar">${initial}</div>
                                    <div class="person-details">
                                        <strong>${person.name}</strong>
                                        <small>ID: ${person.employee_id}</small>
                                    </div>
                                </div>
                                <span class="person-time">${time}</span>
                            </div>
                        `;
                    });
                } else {
                    listDiv.innerHTML = '<h3>👥 Today\'s Attendance</h3><div class="no-data">No attendance records yet...</div>';
                }
            })
            .catch(err => console.error('Error fetching stats:', err));
        }
        function stopAttendance() {
            if (confirm('⚠️ Stop attendance monitoring and return home?')) {
                window.location.href = '/stop_camera';
            }
        }
        updateStats();
        setInterval(updateStats, 2000);
    </script>
</body>
</html>'''




LOGIN_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Face Login Mode</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f0f0; padding: 20px; text-align:center; }
        .container { max-width: 900px; margin: 0 auto; background: white; border-radius: 25px; padding: 40px; box-shadow: 0 25px 70px rgba(0,0,0,0.4);}
        h1 { margin-bottom: 20px; }
        .camera-container { position: relative; margin-bottom: 20px; }
        .camera-container img { width: 100%; border-radius: 15px; border: 3px solid #667eea; }
        .status { font-size: 1.2em; margin-top: 10px; color: red; }
        button { padding: 12px 30px; font-size: 16px; border-radius: 12px; border:none; background:#667eea; color:white; cursor:pointer; margin-top:15px; }
        button:hover { background:#764ba2; }
    </style>
</head>
<body>
    <div class="container">
        <h1>👤 Face Login</h1>
        <div class="camera-container">
            <img id="login-feed" src="/video_feed" alt="Live Camera Feed">
        </div>
        <div class="status" id="login-status">Waiting for face recognition...</div>
        <button onclick="stopLogin()">⏹ Stop & Return Home</button>
    </div>

<script>
function stopLogin(){
    fetch('/stop_camera').then(() => { window.location.href = '/'; });
}

// Poll the server for recognition status
async function checkRecognition(){
    try{
        const res = await fetch('/api/login_status');
        const data = await res.json();
        const statusDiv = document.getElementById('login-status');
        if(data.success){
            statusDiv.style.color = 'green';
            statusDiv.innerText = `Welcome ${data.name}! Login Successful.`;
            setTimeout(() => { window.location.href = '/view_logins'; }, 1000);
        } else if(data.detected){
            statusDiv.style.color = 'red';
            statusDiv.innerText = `Unauthorized person detected!`;
        } else {
            statusDiv.style.color = 'blue';
            statusDiv.innerText = 'Waiting for face...';
        }
    } catch(e){
        console.error(e);
    }
}

// Check every 1 second
setInterval(checkRecognition, 1000);
</script>
</body>
</html>'''


EVACUATION_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Evacuation Mode</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 25px;
            padding: 40px;
            box-shadow: 0 25px 70px rgba(0,0,0,0.5);
            animation: shake 0.5s;
        }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }
        h1 {
            text-align: center;
            color: #dc3545;
            margin-bottom: 15px;
            font-size: 2.8em;
            font-weight: 700;
            animation: pulse 2s infinite;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.05); }
        }
        .event-info {
            text-align: center;
            color: #666;
            margin-bottom: 25px;
            padding: 15px;
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            border-radius: 10px;
            border: 2px solid #ffc107;
        }
        .event-info strong {
            color: #856404;
            font-size: 1.1em;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-bottom: 35px;
        }
        .stat-card {
            padding: 30px;
            border-radius: 15px;
            color: white;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px) scale(1.02);
        }
        .stat-card.total {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .stat-card.safe {
            background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
        }
        .stat-card.missing {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
            animation: pulse 2s infinite;
        }
        .stat-card h3 {
            font-size: 4em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        .stat-card p {
            opacity: 0.95;
            font-size: 1.2em;
            font-weight: 600;
        }
        .camera-container {
            background: #000;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 30px;
            border: 4px solid #dc3545;
            box-shadow: 0 15px 50px rgba(220, 53, 69, 0.4);
            position: relative;
        }
        .camera-container::before {
            content: '🚨 FACE RECOGNITION ACTIVE';
            position: absolute;
            top: 15px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(220, 53, 69, 0.9);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            z-index: 10;
            font-size: 16px;
            animation: blink 1.5s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        #video-feed {
            width: 100%;
            height: auto;
            display: block;
        }
        .button-group {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        button {
            padding: 18px 40px;
            font-size: 18px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 700;
        }
        .btn-danger {
            background: linear-gradient(135deg, #dc3545, #c82333);
            color: white;
        }
        .btn-danger:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(220, 53, 69, 0.4);
        }
        .warning {
            text-align: center;
            padding: 25px;
            background: linear-gradient(135deg, #f8d7da, #f5c6cb);
            color: #721c24;
            border-radius: 12px;
            margin-top: 25px;
            font-size: 1.3em;
            font-weight: bold;
            display: none;
            border: 3px solid #dc3545;
            animation: shake 0.5s infinite;
        }
        .success {
            text-align: center;
            padding: 25px;
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            color: #155724;
            border-radius: 12px;
            margin-top: 25px;
            font-size: 1.3em;
            font-weight: bold;
            display: none;
            border: 3px solid #28a745;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚨 FIRE EVACUATION MODE 🚨</h1>
        <div class="event-info">
            <p><strong>Event ID:</strong> {{ event_id }}</p>
            <p><strong>Started:</strong> {{ start_time }}</p>
            <p>📍 Monitoring assembly point - People crossing the line will be counted</p>
        </div>
        <div class="stats">
            <div class="stat-card total">
                <h3 id="total-count">{{ total }}</h3>
                <p>🏢 Total in Building</p>
            </div>
            <div class="stat-card safe">
                <h3 id="safe-count">0</h3>
                <p>✅ Evacuated (Safe)</p>
            </div>
            <div class="stat-card missing">
                <h3 id="missing-count">{{ total }}</h3>
                <p>⚠️ Still Inside</p>
            </div>
        </div>
        <div class="camera-container">
            <img src="/video_feed" id="video-feed" alt="Evacuation Monitoring">
        </div>
        <div class="warning" id="warning">
            ⚠️ WARNING: PEOPLE STILL INSIDE THE BUILDING! ⚠️
        </div>
        <div class="success" id="success">
            ✅ ALL PERSONNEL ACCOUNTED FOR! EVACUATION COMPLETE! ✅
        </div>
        <div class="button-group">
            <button class="btn-danger" onclick="endEvacuation()">
                🛑 End Evacuation & Return Home
            </button>
        </div>
    </div>
    <script>
        function updateStats() {
            fetch('/api/evacuation_stats')
            .then(res => res.json())
            .then(data => {
                document.getElementById('safe-count').textContent = data.evacuated;
                document.getElementById('missing-count').textContent = data.remaining;
                const warning = document.getElementById('warning');
                const success = document.getElementById('success');
                if (data.remaining > 0) {
                    warning.style.display = 'block';
                    success.style.display = 'none';
                    warning.textContent = `⚠️ WARNING: ${data.remaining} PEOPLE STILL INSIDE! ⚠️`;
                } else {
                    warning.style.display = 'none';
                    success.style.display = 'block';
                }
            })
            .catch(err => console.error('Error fetching stats:', err));
        }
        function endEvacuation() {
            if (confirm('⚠️ End evacuation monitoring and return home?')) {
                window.location.href = '/stop_camera';
            }
        }
        updateStats();
        setInterval(updateStats, 1000);
    </script>
</body>
</html>'''

VIEW_ATTENDANCE_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>View Attendance</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 25px;
            padding: 40px;
            box-shadow: 0 25px 70px rgba(0,0,0,0.4);
            animation: fadeIn 0.6s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 15px;
            font-size: 2.5em;
            font-weight: 700;
        }
        .date {
            text-align: center;
            color: #666;
            margin-bottom: 35px;
            font-size: 1.2em;
            font-weight: 500;
        }
        .summary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 35px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .summary h2 {
            font-size: 4em;
            margin-bottom: 15px;
            font-weight: 700;
        }
        .summary p {
            font-size: 1.2em;
            opacity: 0.95;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
        }
        th, td {
            padding: 18px;
            text-align: left;
        }
        th {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            font-weight: 600;
            font-size: 1.1em;
        }
        td {
            border-bottom: 1px solid #e9ecef;
        }
        tr:last-child td {
            border-bottom: none;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .no-data {
            text-align: center;
            padding: 60px 40px;
            color: #999;
            font-size: 1.3em;
        }
        button {
            padding: 15px 35px;
            font-size: 17px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            display: block;
            margin: 30px auto;
            transition: all 0.3s;
            font-weight: 600;
        }
        button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Today's Attendance Report</h1>
        <p class="date">{{ now }}</p>
        <div class="summary">
            <h2>{{ attendance|length }}</h2>
            <p>People Present Today</p>
        </div>
        {% if attendance %}
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Employee ID</th>
                    <th>Entry Time</th>
                </tr>
            </thead>
            <tbody>
                {% for person in attendance %}
                <tr>
                    <td><strong>{{ loop.index }}</strong></td>
                    <td><strong>{{ person.name }}</strong></td>
                    <td>{{ person.employee_id }}</td>
                    <td>{{ person.entry_time }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="no-data">
            📭 No attendance records for today
        </div>
        {% endif %}
        <button onclick="window.location.href='/'">🏠 Back to Home</button>
    </div>
</body>
</html>'''

VIEW_PERSONS_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Registered Persons</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 25px;
            padding: 40px;
            box-shadow: 0 25px 70px rgba(0,0,0,0.4);
            animation: fadeIn 0.6s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 35px;
            font-size: 2.5em;
            font-weight: 700;
        }
        .summary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 35px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .summary h2 {
            font-size: 4em;
            margin-bottom: 15px;
            font-weight: 700;
        }
        .summary p {
            font-size: 1.2em;
            opacity: 0.95;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
        }
        th, td {
            padding: 18px;
            text-align: left;
        }
        th {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            font-weight: 600;
            font-size: 1.1em;
        }
        td {
            border-bottom: 1px solid #e9ecef;
        }
        tr:last-child td {
            border-bottom: none;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .no-data {
            text-align: center;
            padding: 60px 40px;
            color: #999;
            font-size: 1.3em;
        }
        button {
            padding: 15px 35px;
            font-size: 17px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            display: block;
            margin: 30px auto;
            transition: all 0.3s;
            font-weight: 600;
        }
        button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>👥 Registered Persons Database</h1>
        <div class="summary">
            <h2>{{ persons|length }}</h2>
            <p>Total Registered Personnel</p>
        </div>
        {% if persons %}
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Employee ID</th>
                    <th>Registered Date</th>
                </tr>
            </thead>
            <tbody>
                {% for person in persons %}
                <tr>
                    <td><strong>{{ loop.index }}</strong></td>
                    <td><strong>{{ person.name }}</strong></td>
                    <td>{{ person.employee_id }}</td>
                    <td>{{ person.registered_date }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="no-data">
            📭 No persons registered yet
        </div>
        {% endif %}
        <button onclick="window.location.href='/'">🏠 Back to Home</button>
    </div>
</body>
</html>'''

ERROR_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            background: white;
            border-radius: 25px;
            padding: 50px;
            text-align: center;
            box-shadow: 0 25px 70px rgba(0,0,0,0.4);
            animation: shake 0.5s;
        }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }
        h1 {
            color: #dc3545;
            margin-bottom: 25px;
            font-size: 3em;
            font-weight: 700;
        }
        p {
            color: #666;
            font-size: 1.3em;
            margin-bottom: 35px;
            line-height: 1.6;
        }
        button {
            padding: 15px 35px;
            font-size: 17px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            font-weight: 600;
            transition: all 0.3s;
        }
        button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚠️ Error</h1>
        <p>{{ message }}</p>
        <button onclick="window.location.href='/'">🏠 Back to Home</button>
    </div>
</body>
</html>'''


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/register')
def register_page():
    return render_template_string(REGISTER_HTML)

@app.route('/attendance')
def attendance_page():
    processor.load_known_faces(db)
    camera_manager.mode = 'attendance'
    camera_manager.start_camera()
    return render_template_string(ATTENDANCE_HTML)

@app.route('/evacuation')
def evacuation_page():
    global evacuation_event_id, total_building, evacuated_persons, evacuation_cooldown
    
    evacuated_persons = set()  # Reset for new evacuation
    evacuation_cooldown = {}   # Reset cooldown tracking
    
    attendance = db.get_today_attendance()
    total_building = len(attendance)
    
    if total_building == 0:
        return render_template_string(ERROR_HTML, message="No one is in the building today! Please mark attendance first.")
    
    evacuation_event_id = db.start_evacuation_event(total_building)
    processor.load_known_faces(db)  # Load faces for recognition
    camera_manager.mode = 'evacuation'
    camera_manager.start_camera()
    
    start_time = datetime.now().strftime("%I:%M %p")
    return render_template_string(EVACUATION_HTML, total=total_building, event_id=evacuation_event_id, start_time=start_time)

@app.route('/view_attendance')
def view_attendance():
    attendance = db.get_today_attendance()
    now = datetime.now().strftime("%A, %B %d, %Y")
    return render_template_string(VIEW_ATTENDANCE_HTML, attendance=attendance, now=now)

@app.route('/view_persons')
def view_persons():
    persons = db.get_all_persons()
    return render_template_string(VIEW_PERSONS_HTML, persons=persons)

@app.route('/stop_camera')
def stop_camera():
    camera_manager.stop_camera()
    return redirect(url_for('index'))

@app.route('/view_logins')
def view_logins():
    conn = sqlite3.connect('last_attendance_system.db')
    c = conn.cursor()
    c.execute("SELECT name, employee_id, date, login_time FROM login_logs ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    html = """
    <html>
    <head>
        <title>Login Logs</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f4f9; }
            h2 { text-align:center; }
            table { margin:auto; border-collapse: collapse; width: 80%; }
            th, td { padding:10px; border:1px solid #ccc; text-align:center; }
            th { background-color:#007bff; color:white; }
            tr:nth-child(even) { background-color:#f2f2f2; }
        </style>
    </head>
    <body>
        <h2>Login History</h2>
        <table>
            <tr><th>Name</th><th>Employee ID</th><th>Date</th><th>Login Time</th></tr>
            {% for row in rows %}
            <tr><td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td>{{ row[3] }}</td></tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html, rows=rows)


# ============================================================================
# API Routes
# ============================================================================

@app.route('/api/start_registration', methods=['POST'])
def start_registration():
    global registration_encodings, current_registration_name, current_registration_id
    
    data = request.json
    name = data.get('name')
    employee_id = data.get('employee_id')
    
    if not name or not employee_id:
        return jsonify({'success': False, 'message': 'Name and ID required'})
    
    registration_encodings = {}
    current_registration_name = name
    current_registration_id = employee_id
    
    # Start camera in registration mode
    camera_manager.mode = 'registration'
    success = camera_manager.start_camera()
    
    if not success:
        return jsonify({'success': False, 'message': 'Failed to start camera. Please check camera connection.'})
    
    return jsonify({'success': True, 'name': name, 'employee_id': employee_id})

@app.route('/api/capture_face', methods=['POST'])
def capture_face():
    global registration_encodings
    
    data = request.json
    angle = data.get('angle')
    
    if not angle:
        return jsonify({'success': False, 'message': 'Angle required'})
    
    if angle in registration_encodings:
        return jsonify({'success': False, 'message': 'This angle already captured'})
    
    # Wait for camera to be ready and capture a fresh frame
    max_attempts = 10
    frame = None
    
    for attempt in range(max_attempts):
        frame = camera_manager.read_frame()
        if frame is not None and frame.size > 0:
            break
        time.sleep(0.1)
    
    if frame is None or frame.size == 0:
        return jsonify({'success': False, 'message': 'Camera not ready. Please ensure camera is connected and try again.'})
    
    # Convert to grayscale for face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces using Haar Cascade
    faces = processor.face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )
    
    if len(faces) == 0:
        return jsonify({'success': False, 'message': 'No face detected! Please position your face clearly.'})
    
    if len(faces) > 1:
        return jsonify({'success': False, 'message': 'Multiple faces detected! Only one face allowed.'})
    
    # Extract and resize face
    (x, y, w, h) = faces[0]
    face_roi = gray[y:y+h, x:x+w]
    face_resized = cv2.resize(face_roi, (200, 200))
    
    # Store the face encoding (just the resized grayscale face)
    registration_encodings[angle] = face_resized
    
    return jsonify({
        'success': True,
        'angle': angle,
        'count': len(registration_encodings),
        'total': 5
    })

@app.route('/api/capture_full_view_frame', methods=['POST'])
def capture_full_view_frame():
    global registration_encodings, full_view_progress
    
    data = request.json
    frame_index = data.get('frame_index', 0)
    
    # Read current frame
    frame = camera_manager.read_frame()
    
    if frame is None or frame.size == 0:
        return jsonify({'success': False, 'message': 'Camera not ready'})
    
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = processor.face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )
    
    if len(faces) > 0:
        # Take the first (or largest) face
        if len(faces) > 1:
            # Get the largest face
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        
        (x, y, w, h) = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_roi, (200, 200))
        
        # Store with unique angle name
        angle_name = f"full_view_{frame_index:03d}"
        registration_encodings[angle_name] = face_resized
        
        full_view_progress = frame_index + 1
        
        return jsonify({
            'success': True,
            'frame_index': frame_index,
            'total_captured': len(registration_encodings)
        })
    else:
        # Still return success but log no face detected
        return jsonify({
            'success': True,
            'frame_index': frame_index,
            'message': 'No face in this frame',
            'total_captured': len(registration_encodings)
        })
# Global dictionary to store last detected person in login mode
login_last_detected = {'person_id': None, 'name': None, 'timestamp': 0}
LOGIN_COOLDOWN = 5  # seconds

import base64  # Make sure this is imported at the top

@app.route('/api/login_status')
def login_status():
    frame = camera_manager.read_frame()
    if frame is None:
        return jsonify({'success': False, 'detected': False, 'message': 'No camera frame'})

    # Recognize face from the current frame
    results = processor.recognize_face(frame)

    for result in results:
        if result['person_id'] and result['confidence'] > 0.6:
            person_id = result['person_id']
            name = result['name']

            # Get employee_id
            conn = sqlite3.connect(db.db_path)
            c = conn.cursor()
            c.execute("SELECT employee_id FROM persons WHERE id=?", (person_id,))
            row = c.fetchone()
            conn.close()
            employee_id = row[0] if row else "N/A"

            # Log this login to the new table
            db.log_login(person_id, name, employee_id)

            print(f"✅ Login logged: {name} ({employee_id}) at {datetime.now().strftime('%H:%M:%S')}")

            return jsonify({
                'success': True,
                'name': name,
                'employee_id': employee_id,
                'message': f'Welcome {name}!'
            })

    # If a face is detected but not recognized
    if results:
        return jsonify({'success': False, 'detected': True, 'message': 'Unauthorized person'})

    return jsonify({'success': False, 'detected': False, 'message': 'No face detected'})

@app.route('/api/complete_registration', methods=['POST'])
def complete_registration():
    global registration_encodings, current_registration_name, current_registration_id
    
    try:
        print(f"🔄 Completing registration for: {current_registration_name}")
        print(f"   Total encodings captured: {len(registration_encodings)}")
        
        # Check for required captures
        manual_angles = ['front', 'left', 'right', 'up', 'down']
        manual_count = sum(1 for angle in manual_angles if angle in registration_encodings)
        full_view_count = sum(1 for key in registration_encodings.keys() if 'full_view_' in key)
        
        print(f"   Manual angles: {manual_count}/5")
        print(f"   Full view captures: {full_view_count}/45")
        
        if manual_count < 5:
            return jsonify({'success': False, 'message': f'Need all 5 manual angles. Got {manual_count}'}), 200
        
        if full_view_count < 30:  # Require at least 30 good captures from 45 attempts
            return jsonify({'success': False, 'message': f'Need at least 30 full view captures. Got {full_view_count}'}), 200
        
        # Register the person in database
        success = db.register_person(current_registration_name, current_registration_id, registration_encodings)
        
        # Stop camera and clear encodings
        camera_manager.stop_camera()
        registration_encodings = {}
        current_registration_name = None
        current_registration_id = None
        
        if success:
            print(f"✅ Registration completed successfully with {manual_count + full_view_count} total images")
            # Reload face encodings for recognition
            processor.load_known_faces(db)
            return jsonify({'success': True, 'message': 'Registration completed successfully'}), 200
        else:
            print(f"❌ Registration failed - person may already exist")
            return jsonify({'success': False, 'message': 'Person already registered or database error'}), 200
            
    except Exception as e:
        print(f"❌ Error in complete_registration: {e}")
        import traceback
        traceback.print_exc()
        camera_manager.stop_camera()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 200

@app.route('/api/attendance_stats')
def attendance_stats():
    attendance = db.get_today_attendance()
    return jsonify({
        'total': len(attendance),
        'people': attendance
    })

@app.route('/api/evacuation_stats')
def evacuation_stats():
    evacuated_count = len(evacuated_persons)
    remaining = total_building - evacuated_count
    
    return jsonify({
        'total': total_building,
        'evacuated': evacuated_count,
        'remaining': remaining
    })


# ============================================================================
# Video Streaming
# ============================================================================

def generate_frames():
    global last_marked, evacuation_event_id
    
    frame_count = 0
    
    while camera_manager.is_running:
        frame = camera_manager.read_frame()
        
        if frame is None:
            # Generate error frame if camera not available
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "Camera Initializing...", (150, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.1)
            continue
        
        frame_count += 1
        height, width = frame.shape[:2]
        
        # REGISTRATION MODE
        if camera_manager.mode == 'registration':
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces using Haar Cascade
            faces = processor.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(80, 80)
            )
            
            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                # Main face rectangle - green for single face, red for multiple
                if len(faces) == 1:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                else:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 3)
                
                # Draw outer glow effect
                cv2.rectangle(frame, (x-2, y-2), (x+w+2, y+h+2), (255, 255, 255), 2)
                
                # Draw crosshair at center
                center_x = x + w // 2
                center_y = y + h // 2
                cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
                cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)
                
                # Draw corner brackets for better visual
                bracket_size = 15
                # Top-left
                cv2.line(frame, (x, y), (x + bracket_size, y), (255, 255, 0), 3)
                cv2.line(frame, (x, y), (x, y + bracket_size), (255, 255, 0), 3)
                # Top-right
                cv2.line(frame, (x+w, y), (x+w - bracket_size, y), (255, 255, 0), 3)
                cv2.line(frame, (x+w, y), (x+w, y + bracket_size), (255, 255, 0), 3)
                # Bottom-left
                cv2.line(frame, (x, y+h), (x + bracket_size, y+h), (255, 255, 0), 3)
                cv2.line(frame, (x, y+h), (x, y+h - bracket_size), (255, 255, 0), 3)
                # Bottom-right
                cv2.line(frame, (x+w, y+h), (x+w - bracket_size, y+h), (255, 255, 0), 3)
                cv2.line(frame, (x+w, y+h), (x+w, y+h - bracket_size), (255, 255, 0), 3)
            
            # Display status message with background for better visibility
            if len(faces) == 0:
                text = "NO FACE DETECTED"
                color = (0, 0, 255)
                bg_color = (255, 255, 255)
            elif len(faces) > 1:
                text = "MULTIPLE FACES - ONLY ONE ALLOWED"
                color = (0, 0, 255)
                bg_color = (255, 255, 255)
            else:
                text = "FACE DETECTED - READY TO CAPTURE"
                color = (0, 255, 0)
                bg_color = (0, 0, 0)
            
            # Draw background rectangle for main text
            (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.rectangle(frame, (15, 10), (25 + text_width, 50), bg_color, -1)
            cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            # Draw captured count with background
            count_text = f"Captured: {len(registration_encodings)}/5"
            (count_width, count_height), _ = cv2.getTextSize(count_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(frame, (15, 55), (25 + count_width, 95), (0, 0, 0), -1)
            cv2.putText(frame, count_text, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show which angles are captured on the left side
            y_offset = 110
            for angle in ['front', 'left', 'right', 'up', 'down']:
                if angle in registration_encodings:
                    angle_text = f"✓ {angle.upper()}"
                    angle_color = (0, 255, 0)
                    bg = (0, 100, 0)
                else:
                    angle_text = f"○ {angle.upper()}"
                    angle_color = (200, 200, 200)
                    bg = (50, 50, 50)
                
                # Draw background for angle status
                (angle_width, angle_height), _ = cv2.getTextSize(angle_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(frame, (15, y_offset - 18), (25 + angle_width, y_offset + 5), bg, -1)
                cv2.putText(frame, angle_text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, angle_color, 2)
                y_offset += 30
            
            # Add instruction text at bottom
            if len(faces) == 1:
                # Show full view capturing status
                if full_view_progress > 0:
                    cv2.putText(frame, f"FULL VIEW: {full_view_progress}/45", 
                            (20, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                instruction = "Click the angle button below to capture"
                cv2.putText(frame, instruction, (20, height - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # ATTENDANCE MODE
        elif camera_manager.mode == 'attendance':
            # Process every 3rd frame for performance
            if frame_count % 3 == 0:
                results = processor.recognize_face(frame)
                current_time = time.time()
                
                for result in results:
                    if result['person_id']:
                        last_time = last_marked.get(result['person_id'], 0)
                        
                        if current_time - last_time > cooldown:
                            if db.mark_attendance(result['person_id']):
                                last_marked[result['person_id']] = current_time
            
            # Draw faces on every frame
            results = processor.recognize_face(frame)
            
            for result in results:
                left, top, right, bottom = result['box']
                color = (0, 255, 0) if result['person_id'] else (0, 0, 255)
                
                # Draw rectangle
                cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
                
                # Prepare label
                label = f"{result['name']}"
                if result['person_id']:
                    label += f" ({result['confidence']:.2f})"
                
                # Draw label background
                (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame, (left, bottom - 30), (left + label_width + 10, bottom), color, cv2.FILLED)
                cv2.putText(frame, label, (left + 5, bottom - 8),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Display stats
            attendance = db.get_today_attendance()
            cv2.putText(frame, f"Attendance Today: {len(attendance)}", (20, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            cv2.putText(frame, f"Faces Detected: {len(results)}", (20, 85),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        elif camera_manager.mode == 'login':
            # Process every 3rd frame for performance
            if frame_count % 3 == 0:
                results = processor.recognize_face(frame)
                
                recognized = False
                for result in results:
                    (x1, y1, x2, y2) = result['box']
                    if result['person_id'] and result['confidence'] > 0.6:
                        recognized = True
                        name = result['name']
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        cv2.putText(frame, f"LOGIN SUCCESS: {name}", (x1, y1 - 15),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    else:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        cv2.putText(frame, "UNAUTHORIZED PERSON", (x1, y1 - 15),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                if not results:
                    cv2.putText(frame, "Waiting for face...", (50, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            
            # Label at top
            cv2.putText(frame, "LOGIN MODE ACTIVE", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # EVACUATION MODE
        elif camera_manager.mode == 'evacuation':
            current_time = time.time()
            
            # Process every 2nd frame for performance
            if frame_count % 2 == 0:
                results = processor.recognize_face(frame)
                
                # Track recognized persons
                for result in results:
                    if result['person_id'] and result['confidence'] > 0.5:  # Only count if confidence > 50%
                        person_id = result['person_id']
                        
                        # Check if person is in today's attendance
                        attendance_ids = [p['id'] for p in db.get_today_attendance()]
                        
                        if person_id in attendance_ids:
                            # Check cooldown to prevent rapid re-counting
                            last_seen = evacuation_cooldown.get(person_id, 0)
                            
                            if current_time - last_seen > EVACUATION_COOLDOWN_TIME:
                                evacuated_persons.add(person_id)
                                evacuation_cooldown[person_id] = current_time
                                db.update_evacuation_count(evacuation_event_id, len(evacuated_persons))
            
            # Draw all detected faces
            results = processor.recognize_face(frame)
            
            for result in results:
                left, top, right, bottom = result['box']
                person_id = result['person_id']
                
                # Color coding: Green if recognized and in attendance, Red if unknown
                if person_id and person_id in [p['id'] for p in db.get_today_attendance()]:
                    color = (0, 255, 0)  # Green - Valid person
                    status = "RECOGNIZED"
                    
                    # Check if already evacuated
                    if person_id in evacuated_persons:
                        status = "EVACUATED ✓"
                        color = (0, 200, 0)
                else:
                    color = (0, 0, 255)  # Red - Unknown
                    status = "UNKNOWN"
                
                # Draw rectangle
                cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
                
                # Draw corner brackets
                bracket_size = 20
                cv2.line(frame, (left, top), (left + bracket_size, top), (255, 255, 0), 3)
                cv2.line(frame, (left, top), (left, top + bracket_size), (255, 255, 0), 3)
                cv2.line(frame, (right, top), (right - bracket_size, top), (255, 255, 0), 3)
                cv2.line(frame, (right, top), (right, top + bracket_size), (255, 255, 0), 3)
                
                # Prepare label
                label = f"{result['name']}"
                if person_id:
                    label += f" ({result['confidence']:.2f})"
                
                # Draw label background
                (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame, (left, top - 60), (left + max(label_width, 150), top), color, cv2.FILLED)
                
                # Draw name
                cv2.putText(frame, label, (left + 5, top - 35),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Draw status
                cv2.putText(frame, status, (left + 5, top - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            evacuated_count = len(evacuated_persons)
            remaining = total_building - evacuated_count

            # Display stats
            cv2.putText(frame, "EVACUATION MODE ACTIVE", (20, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            cv2.putText(frame, f"Total: {total_building} | Safe: {evacuated_count} | Missing: {remaining}",
                       (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            if remaining > 0:
                cv2.putText(frame, f"WARNING: {remaining} STILL INSIDE!", (20, 140),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            else:
                cv2.putText(frame, "ALL EVACUATED - SAFE!", (20, 140),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
        
        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        
        # Yield frame in proper format for streaming
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route('/login')
def login_page():
    processor.load_known_faces(db)
    camera_manager.mode = 'login'
    camera_manager.start_camera()
    return render_template_string(LOGIN_HTML)


import base64

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    img_data = data.get('image')

    if not img_data:
        return jsonify({'success': False, 'message': 'No image captured'})

    # Convert base64 image to OpenCV frame
    try:
        header, encoded = img_data.split(",", 1)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Image decoding error: {e}'})

    if frame is None or frame.size == 0:
        return jsonify({'success': False, 'message': 'Invalid frame from camera'})

    # Recognize face (reuse your attendance processor)
    results = processor.recognize_face(frame)

    # Check recognized faces against registered users
    for result in results:
        if result['person_id'] and result['confidence'] > 0.6:  # You can adjust the confidence threshold
            person_id = result['person_id']
            name = result['name']

            # ✅ Fetch employee_id from the database
            conn = sqlite3.connect('last_attendance_system.db')
            c = conn.cursor()
            c.execute("SELECT employee_id FROM persons WHERE id = ?", (person_id,))
            row = c.fetchone()
            conn.close()

            if row:
                employee_id = row[0]

                # ✅ Log the successful login
                db.log_login(person_id, name, employee_id)

                return jsonify({'success': True, 'message': f'Welcome {name}!'})

    return jsonify({'success': False, 'message': 'Unauthorized person'})

# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 Enhanced Facial Recognition System Starting...")
    print("="*70)
    print("\n📋 Features:")
    print("   ✓ Multi-angle face registration (5 angles)")
    print("   ✓ Real-time attendance tracking")
    print("   ✓ Fire evacuation monitoring")
    print("   ✓ Interactive camera interface")
    print("   ✓ Modern responsive UI")
    print("\n🌐 Access the application:")
    print("   → http://localhost:5004")
    print("   → http://127.0.0.1:5004")
    print("\n⚠️  Requirements:")
    print("   pip install flask opencv-python face_recognition numpy")
    print("\n" + "="*70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5004, threaded=True)