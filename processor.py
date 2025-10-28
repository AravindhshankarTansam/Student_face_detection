import face_recognition
import cv2
from attendance_db import AttendanceDB
import numpy as np
import pickle

attendance_db = AttendanceDB()
encodings, person_ids, names = attendance_db.get_all_face_encodings()

def recognize_face(frame):
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    results = []
    for encoding in face_encodings:
        matches = face_recognition.compare_faces(encodings, encoding)
        if True in matches:
            match_index = matches.index(True)
            results.append({'name': names[match_index], 'person_id': person_ids[match_index]})
        else:
            results.append({'name': 'Unknown', 'person_id': None})
    return results
