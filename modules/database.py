import sqlite3
import pickle
from datetime import datetime
import uuid

class AttendanceDB:
    def __init__(self, db_path="last_attendance_system.db"):
        self.db_path = db_path
        self.init_db()
        self.migrate_db()
    
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