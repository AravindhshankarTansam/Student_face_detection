# 🔥 Enhanced AI-Powered Facial Recognition Attendance and Fire Evacuation System

A complete Flask-based web application featuring real-time facial recognition for attendance tracking and emergency evacuation monitoring. The system uses advanced computer vision techniques with multi-angle face registration for enhanced accuracy.

---

## 📋 Project Overview

This system provides a comprehensive solution for:
- **Smart Attendance Management**: Automated face recognition-based attendance marking
- **Multi-Angle Registration**: Capture 50 face images (5 key angles + 45 full-view captures) for robust recognition
- **Emergency Evacuation Monitoring**: Real-time tracking of personnel during fire evacuations
- **Interactive Web Interface**: Modern, responsive UI with live camera feeds
- **Database Management**: SQLite-based storage for personnel, attendance, and evacuation records

---

## 🛠️ Technology Stack

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **Python** | 3.7+ | Programming language |
| **Flask** | 2.0.0+ | Web framework |
| **OpenCV (cv2)** | 4.5.0+ | Computer vision and camera handling |
| **opencv-contrib-python** | 4.5.0+ | LBPH face recognizer (required!) |
| **face-recognition** | 1.3.0+ | Face detection utilities |
| **NumPy** | 1.19.0+ | Numerical computing |
| **SQLite3** | Built-in | Database management |

---


pip freeze > requirements.txt


## 📦 Installation

### Step 1: Install Required Packages

```bash
pip install flask opencv-python opencv-contrib-python face-recognition numpy
```

### Step 2: Verify Installation

```python
import cv2
print(cv2.__version__)
print("OpenCV contrib modules:", hasattr(cv2, 'face'))
```

**Important**: You must install `opencv-contrib-python` for the LBPH Face Recognizer to work!

### Step 3: Run the Application

```bash
python app.py
```

### Step 4: Access the Application

Open your browser and navigate to:
- Local: `http://localhost:5004`
- Network: `http://127.0.0.1:5004`

---

## 🎯 Key Features

### 1. **Multi-Angle Face Registration**
- **Step 1**: Capture 5 key angles (Front, Left, Right, Up, Down)
- **Step 2**: Full-view capture of 45 images while moving across camera
- **Total**: 50 face images per person for maximum accuracy
- **Validation**: Eye detection, aspect ratio checks, texture variance analysis

### 2. **Real-Time Attendance Tracking**
- Automatic face detection and recognition
- 30-second cooldown to prevent duplicate entries
- Live attendance count display
- Detailed entry time logging

### 3. **Fire Evacuation Monitoring**
- Emergency mode activation
- Real-time face recognition at evacuation points
- Tracks evacuated vs. remaining personnel
- Color-coded status indicators (Green: Safe, Red: Missing)
- 30-second cooldown per person to prevent re-counting

### 4. **Enhanced Face Recognition**
- **Haar Cascade**: Fast face detection
- **LBPH Recognizer**: Local Binary Pattern Histogram for robust matching
- **Multi-validation**: Eye detection, variance checks, aspect ratio filters
- **Confidence scoring**: Only recognitions above 50% confidence are accepted

### 5. **Modern Web Interface**
- Responsive design for mobile and desktop
- Live camera feed streaming
- Real-time statistics and updates
- Gradient-based modern UI design
- Smooth animations and transitions

---

## 📊 Database Schema

### Tables

#### 1. **persons**
- `id`: Primary key
- `name`: Full name
- `employee_id`: Unique identifier
- `registered_date`: Registration timestamp

#### 2. **face_encodings**
- `id`: Primary key
- `person_id`: Foreign key to persons
- `encoding`: Pickled face data (200x200 grayscale)
- `angle`: Capture angle/position

#### 3. **attendance**
- `id`: Primary key
- `person_id`: Foreign key to persons
- `date`: Attendance date
- `entry_time`: Entry timestamp
- Unique constraint on (person_id, date)

#### 4. **evacuation_events**
- `id`: Primary key
- `event_id`: Unique event identifier
- `start_time`: Event start timestamp
- `end_time`: Event end timestamp (nullable)
- `total_building`: Total people in building
- `total_evacuated`: Count of evacuated people

---

## 🚀 Usage Guide

### Registering a New Person

1. Click **"Register Person"** on home page
2. Enter full name and employee ID
3. **Step 1**: Capture 5 manual angles
   - Click each angle button when properly positioned
   - Ensure good lighting and clear face visibility
   - All 5 angles must be completed
4. **Step 2**: Full view capture
   - Click "Start Full Capture"
   - Stand on RIGHT side of camera
   - Move slowly from RIGHT to LEFT
   - Follow the moving arrow for 15 seconds
   - System captures 45 images automatically
5. Click **"Complete Registration"**
6. System processes all 50 images and trains the recognizer

### Running Attendance Mode

1. Click **"Attendance Mode"** on home page
2. System loads all registered faces
3. Camera activates with live face recognition
4. Recognized persons are automatically marked
5. View live attendance count and recent entries
6. Click **"View Full Report"** for detailed records

### Running Evacuation Mode

1. Ensure attendance has been marked for the day
2. Click **"Evacuation Mode"** on home page
3. System counts total people from today's attendance
4. Camera monitors evacuation point with face recognition
5. Recognized persons crossing the line are counted as safe
6. Real-time display shows: Total, Safe, Missing
7. Color indicators: Green (evacuated), Red (still inside)

---

## ⚙️ Configuration Options

### Camera Settings (in code)

```python
# Camera resolution
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# Face detection parameters
scaleFactor=1.3      # 1.1-1.5 (higher = fewer false positives)
minNeighbors=6       # 3-8 (higher = stricter detection)
minSize=(60, 60)     # Minimum face size in pixels
```

### Recognition Settings

```python
# LBPH Recognizer parameters
radius=1             # Radius for LBP calculation
neighbors=8          # Number of neighbors
grid_x=8             # Grid size X
grid_y=8             # Grid size Y

# Confidence threshold
confidence_threshold = 50  # Lower = stricter (0-100)

# Cooldown periods
attendance_cooldown = 30   # Seconds between re-marks
evacuation_cooldown = 30   # Seconds between evacuation counts
```

### Database Path

```python
db_path = "last_attendance_system.db"  # Change to your preferred path
```

---

## 🔧 Troubleshooting

### Issue: "opencv-contrib-python not installed" error

**Solution**: 
```bash
pip uninstall opencv-python opencv-contrib-python
pip install opencv-contrib-python
```

### Issue: Camera not opening

**Solution**:
- Check camera permissions
- Try different camera indices (0, 1, 2)
- Ensure no other application is using the camera

### Issue: No faces detected during registration

**Solution**:
- Ensure good lighting conditions
- Position face clearly in frame
- Remove glasses/masks if possible
- Check if face is too close or too far

### Issue: Poor recognition accuracy

**Solution**:
- Re-register with better quality images
- Ensure consistent lighting between registration and recognition
- Adjust confidence threshold in code
- Capture all 50 images during registration

### Issue: Video feed freezing

**Solution**:
- Refresh the page
- Check CPU usage (recognition is computationally intensive)
- Reduce frame processing rate in code

---

## 📝 System Requirements

### Minimum Requirements
- **CPU**: Dual-core 2.0 GHz or better
- **RAM**: 4 GB
- **Camera**: 720p webcam (USB or built-in)
- **OS**: Windows 10, macOS 10.14+, Ubuntu 18.04+
- **Python**: 3.7 or higher

### Recommended Requirements
- **CPU**: Quad-core 3.0 GHz
- **RAM**: 8 GB
- **Camera**: 1080p webcam
- **Lighting**: Consistent ambient lighting

---

## 🔒 Security Notes

1. **Data Privacy**: Face encodings are stored as pickled binary data
2. **Database**: SQLite database stored locally (not encrypted by default)
3. **Network**: Application runs on localhost by default
4. **Production**: Change `app.secret_key` before deployment
5. **Access Control**: No authentication implemented (add as needed)

---

## 🌟 Advanced Features

### False Positive Prevention
- Aspect ratio validation (0.7-1.3)
- Texture variance check (minimum 200)
- Eye detection requirement
- Confidence threshold filtering

### Performance Optimization
- Background thread for frame capture
- Frame skipping (process every 2-3 frames)
- JPEG quality optimization (85%)
- Efficient database queries

### User Experience
- Visual feedback during registration
- Real-time progress indicators
- Animated UI elements
- Color-coded status displays
- Auto-refreshing statistics

---

## 📚 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Home page |
| `/register` | GET | Registration interface |
| `/attendance` | GET | Attendance monitoring |
| `/evacuation` | GET | Evacuation monitoring |
| `/view_attendance` | GET | Attendance reports |
| `/view_persons` | GET | Registered persons list |
| `/video_feed` | GET | Live camera stream |
| `/api/start_registration` | POST | Initialize registration |
| `/api/capture_face` | POST | Capture single angle |
| `/api/capture_full_view_frame` | POST | Capture full view frame |
| `/api/complete_registration` | POST | Finalize registration |
| `/api/attendance_stats` | GET | Get attendance statistics |
| `/api/evacuation_stats` | GET | Get evacuation statistics |
| `/stop_camera` | GET | Stop camera and return home |

---

## 🎨 UI Color Scheme

- **Primary**: #667eea (Purple-Blue)
- **Secondary**: #764ba2 (Deep Purple)
- **Success**: #56ab2f (Green)
- **Danger**: #dc3545 (Red)
- **Warning**: #ffc107 (Amber)

---

## 📄 License

This project is provided as-is for educational and commercial use. Modify as needed for your specific requirements.

---

## 👨‍💻 Developer Notes

### Extending the System

1. **Add Authentication**: Implement user login system
2. **Export Reports**: Add CSV/PDF export functionality
3. **Email Notifications**: Send alerts during evacuations
4. **Multi-Camera**: Support multiple camera feeds
5. **Cloud Sync**: Integrate cloud database storage
6. **Mobile App**: Develop companion mobile application

### Code Structure

```
app.py
├── Database Manager (AttendanceDB)
├── Face Processor (FaceProcessor)
├── Camera Manager (CameraManager)
├── Flask Routes (Web Pages)
├── API Routes (JSON Endpoints)
└── Video Streaming (MJPEG)
```

---

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review console output for error messages
3. Verify all dependencies are installed correctly
4. Ensure camera permissions are granted

---

## ✅ Checklist for Deployment

- [ ] Install all dependencies
- [ ] Test camera functionality
- [ ] Register at least one person
- [ ] Test attendance marking
- [ ] Test evacuation mode
- [ ] Change `app.secret_key` in production
- [ ] Configure firewall if needed
- [ ] Set up backup strategy for database
- [ ] Document any custom modifications

---

**Version**: 1.0.0  
**Last Updated**: 2025  
**Flask Port**: 5004  
**Database**: SQLite3

---

🎉 **Ready to use! Start the application and access it at http://localhost:5004**