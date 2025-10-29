import os

class Config:
    SECRET_KEY = 'your-secret-key-here-change-in-production'
    DATABASE_PATH = "last_attendance_system.db"
    CAMERA_INDEX = 0
    FRAME_WIDTH = 1280
    FRAME_HEIGHT = 720
    COOLDOWN_TIME = 30
    EVACUATION_COOLDOWN_TIME = 30
    