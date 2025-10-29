import cv2
import threading
import time

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
            
            self.frame_thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.frame_thread.start()
            
            time.sleep(0.5)
            print("🎥 Camera started in mode:", self.mode)
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
            time.sleep(0.03)
    
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