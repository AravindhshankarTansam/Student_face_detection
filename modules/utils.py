from datetime import datetime
import time

def get_current_time():
    return datetime.now()

def format_time(dt):
    return dt.strftime("%H:%M:%S")

def format_date(dt):
    return dt.strftime("%Y-%m-%d")

def format_datetime(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")