from flask import Flask, render_template, render_template_string, Response, request, jsonify, redirect, url_for
import cv2
import numpy as np
import time
import threading
from datetime import datetime
import sqlite3
import pickle
import uuid
import base64

from config import Config
from modules.database import AttendanceDB
from modules.face_processor import FaceProcessor
from modules.camera_manager import CameraManager

app = Flask(__name__)
app.config.from_object(Config)

# Global instances
db = AttendanceDB()
processor = FaceProcessor()
processor.load_known_faces(db)
camera_manager = CameraManager()

# State variables
registration_encodings = {}
current_registration_name = None
current_registration_id = None
last_marked = {}
cooldown = 30
evacuation_event_id = None
total_building = 0
evacuated_persons = set()
evacuation_cooldown = {}
EVACUATION_COOLDOWN_TIME = 30
full_view_progress = 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/login')
def login_page():
    processor.load_known_faces(db)
    camera_manager.mode = 'login'
    camera_manager.start_camera()
    return render_template('login.html')

@app.route('/view_attendance')
def view_attendance():
    attendance = db.get_today_attendance()
    now = datetime.now().strftime("%A, %B %d, %Y")
    return render_template('view_attendance.html', attendance=attendance, now=now)

@app.route('/view_persons')
def view_persons():
    persons = db.get_all_persons()
    return render_template('view_persons.html', persons=persons)


@app.route('/view_logins')
def view_logins():
    conn = sqlite3.connect('last_attendance_system.db')
    c = conn.cursor()
    c.execute("SELECT name, employee_id, date, login_time FROM login_logs ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()

    if not row:
        return "<h2 style='text-align:center; color:red;'>No recent logins found.</h2>"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Login Successful</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #DFE9EF, #ffffff);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }}
            .success-container {{
                background: white;
                border-radius: 25px;
                padding: 60px 80px;
                text-align: center;
                box-shadow: 0 0px 0px rgba(0,0,0,0.25);
                position: relative;
                animation: slideUp 0.8s ease forwards;
            }}
            @keyframes slideUp {{
                from {{ opacity: 0; transform: translateY(50px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .scanner {{
                width: 150px;
                height: 150px;
                margin: 0 auto 30px;
                border-radius: 50%;
                background: radial-gradient(circle at center, #004e92 0%, #003270 70%);
                animation: pulseGlow 2s infinite ease-in-out;
                position: relative;
            }}
            @keyframes pulseGlow {{
                0%, 100% {{ box-shadow: 0 0 30px #004e92; transform: scale(1); }}
                50% {{ box-shadow: 0 0 50px #007bff; transform: scale(1.05); }}
            }}
            .scanner::after {{
                content: '✓';
                color: white;
                font-size: 75px;
                font-weight: bold;
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                animation: appear 1s ease-out;
            }}
            @keyframes appear {{
                from {{ opacity: 0; transform: translate(-50%, -50%) scale(0.5); }}
                to {{ opacity: 1; transform: translate(-50%, -50%) scale(1); }}
            }}
            h1 {{
                color: #004e92;
                font-size: 2.2em;
                font-weight: 700;
                margin-bottom: 25px;
            }}
            .info {{
                background: #DFE9EF;
                border-radius: 15px;
                padding: 20px 30px;
                text-align: left;
                line-height: 1.8;
                font-size: 1.1em;
                margin-top: 20px;
            }}
            .info span {{
                font-weight: 600;
                color: #004e92;
            }}
            button {{
                background: linear-gradient(135deg, #004e92, #007bff);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px 40px;
                margin-top: 30px;
                cursor: pointer;
                font-size: 1rem;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            button:hover {{
                transform: scale(1.07);
                background: linear-gradient(135deg, #003b73, #004e92);
            }}
        </style>

        <!-- ✅ Keep only this one redirect script -->
        <script>
            // Automatically redirect to home after 5 seconds
            setTimeout(function() {{
                window.location.href = '/';
            }}, 2000);
        </script>
    </head>
    <body>
        <div class="success-container">
            <div class="scanner"></div>
            <h1>Login Successful</h1>
            <div class="info">
                <p><span>Name:</span> {row[0]}</p>
                <p><span>Employee ID:</span> {row[1]}</p>
                <p><span>Date:</span> {row[2]}</p>
                <p><span>Login Time:</span> {row[3]}</p>
            </div>
            <button onclick="window.location.href='/'">🏠 Back to Home</button>
            <div class="footer">Smart Login System</div>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/stop_camera')
def stop_camera():
    camera_manager.stop_camera()
    return redirect(url_for('index'))

# API Routes
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
    
    max_attempts = 10
    frame = None
    
    for attempt in range(max_attempts):
        frame = camera_manager.read_frame()
        if frame is not None and frame.size > 0:
            break
        time.sleep(0.1)
    
    if frame is None or frame.size == 0:
        return jsonify({'success': False, 'message': 'Camera not ready. Please ensure camera is connected and try again.'})
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # ✅ Ensure the cascade is loaded properly
    if not hasattr(processor, 'face_cascade') or processor.face_cascade.empty():
        print("⚠️ Reinitializing face cascade...")
        processor.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    # ✅ Detect faces safely
    faces = []
    try:
        faces = processor.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )
    except cv2.error as e:
        print(f"⚠️ Face detection failed: {e}")
        faces = []
    
    if len(faces) == 0:
        return jsonify({'success': False, 'message': 'No face detected! Please position your face clearly.'})
    
    if len(faces) > 1:
        return jsonify({'success': False, 'message': 'Multiple faces detected! Only one face allowed.'})
    
    (x, y, w, h) = faces[0]
    face_roi = gray[y:y+h, x:x+w]
    face_resized = cv2.resize(face_roi, (200, 200))
    
    registration_encodings[angle] = face_resized
    
    return jsonify({
        'success': True,
        'angle': angle,
        'count': len(registration_encodings),
        'total': 5
    })

@app.route('/api/complete_registration', methods=['POST'])
def complete_registration():
    global registration_encodings, current_registration_name, current_registration_id
    
    try:
        print(f"🔄 Completing registration for: {current_registration_name}")
        print(f"   Total encodings captured: {len(registration_encodings)}")
        
        manual_angles = ['front', 'left', 'right', 'up', 'down']
        manual_count = sum(1 for angle in manual_angles if angle in registration_encodings)
        
        print(f"   Manual angles: {manual_count}/5")
        
        if manual_count < 5:
            return jsonify({'success': False, 'message': f'Need all 5 manual angles. Got {manual_count}'})
        
        success = db.register_person(current_registration_name, current_registration_id, registration_encodings)
        
        camera_manager.stop_camera()
        registration_encodings = {}
        current_registration_name = None
        current_registration_id = None
        
        if success:
            print(f"✅ Registration completed successfully with {manual_count} images")
            processor.load_known_faces(db)
            return jsonify({'success': True, 'message': 'Registration completed successfully'})
        else:
            print(f"❌ Registration failed - person may already exist")
            return jsonify({'success': False, 'message': 'Person already registered or database error'})
            
    except Exception as e:
        print(f"❌ Error in complete_registration: {e}")
        import traceback
        traceback.print_exc()
        camera_manager.stop_camera()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

@app.route('/api/login_status')
def login_status():
    frame = camera_manager.read_frame()
    if frame is None:
        return jsonify({'success': False, 'detected': False, 'message': 'No camera frame'})

    results = processor.recognize_face(frame)

    for result in results:
        if result['person_id'] and result['confidence'] > 0.6:
            person_id = result['person_id']
            name = result['name']

            conn = sqlite3.connect(db.db_path)
            c = conn.cursor()
            c.execute("SELECT employee_id FROM persons WHERE id=?", (person_id,))
            row = c.fetchone()
            conn.close()
            employee_id = row[0] if row else "N/A"

            db.log_login(person_id, name, employee_id)

            print(f"✅ Login logged: {name} ({employee_id}) at {datetime.now().strftime('%H:%M:%S')}")

            return jsonify({
                'success': True,
                'name': name,
                'employee_id': employee_id,
                'message': f'Welcome {name}!'
            })

    if results:
        return jsonify({'success': False, 'detected': True, 'message': 'Unauthorized person'})

    return jsonify({'success': False, 'detected': False, 'message': 'No face detected'})

def generate_frames(mode='login'):
    global last_marked, evacuation_event_id
    
    frame_count = 0
    
    while camera_manager.is_running:
        frame = camera_manager.read_frame()
        
        if frame is None:
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
        
        if camera_manager.mode == 'registration':
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            faces = processor.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(80, 80)
            )
            
            for (x, y, w, h) in faces:
                if len(faces) == 1:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                else:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 3)
                
                cv2.rectangle(frame, (x-2, y-2), (x+w+2, y+h+2), (255, 255, 255), 2)
                
                center_x = x + w // 2
                center_y = y + h // 2
                cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
                cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)
            
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
            
            (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.rectangle(frame, (15, 10), (25 + text_width, 50), bg_color, -1)
            cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            count_text = f"Captured: {len(registration_encodings)}/5"
            (count_width, count_height), _ = cv2.getTextSize(count_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(frame, (15, 55), (25 + count_width, 95), (0, 0, 0), -1)
            cv2.putText(frame, count_text, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        elif camera_manager.mode == 'login':
            if frame_count % 3 == 0:
                results = processor.recognize_face(frame)
                
                for result in results:
                    (x1, y1, x2, y2) = result['box']
                    if result['person_id'] and result['confidence'] > 0.6:
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
            
            cv2.putText(frame, "LOGIN MODE ACTIVE", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        

        
@app.route('/video_feed')
def video_feed():
    # Get the mode from URL (like ?t=login or ?t=registration)
    mode = request.args.get('t', 'login')  # default is 'login'

    # Tell the camera manager which mode to use
    camera_manager.mode = mode

    # Start generating frames for that mode
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

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