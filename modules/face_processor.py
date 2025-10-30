import cv2
import numpy as np

class FaceProcessor:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )

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
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.3,
            minNeighbors=6,
            minSize=(60, 60),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        results = []
        
        for (x, y, w, h) in faces:
            aspect_ratio = w / float(h)
            if aspect_ratio < 0.7 or aspect_ratio > 1.3:
                continue
            
            face_roi = gray[y:y+h, x:x+w]
            
            variance = np.var(face_roi)
            if variance < 200:
                continue
            
            eye_region = face_roi[0:int(h*0.6), :]
            eyes = self.eye_cascade.detectMultiScale(
                eye_region,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(15, 15)
            )
            
            if len(eyes) < 1:
                continue
            
            person_id = None
            name = "Unknown"
            confidence = 0.0
            
            if self.is_trained and self.recognizer is not None:
                face_resized = cv2.resize(face_roi, (200, 200))
                
                try:
                    label, conf = self.recognizer.predict(face_resized)
                    
                    if conf < 50:
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