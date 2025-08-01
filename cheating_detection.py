import cv2
import numpy as np
import datetime
import uuid
import os
import json

class CheatingDetector:
    def __init__(self):
        # Load face detection model
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Settings
        self.detection_threshold = 1  # More than one face is considered cheating
        
        # Ensure logs directory exists
        os.makedirs("uploads/logs", exist_ok=True)
    
    def detect_multiple_faces(self, frame):
        """
        Detect faces in a frame and return the count and marked frame
        """
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        # Make a copy of the frame to mark faces on
        marked_frame = frame.copy()
        
        # Draw rectangles around detected faces
        for (x, y, w, h) in faces:
            cv2.rectangle(marked_frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
            
        return len(faces), marked_frame
    
    def log_cheating_attempt(self, cheating_type, details):
        """
        Log a cheating attempt with timestamp and details
        
        Args:
            cheating_type (str): Type of cheating (e.g., 'multiple_faces', 'tab_switch')
            details (dict): Additional details about the cheating attempt
            
        Returns:
            dict: Log entry
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_id = str(uuid.uuid4())
        
        log_entry = {
            "id": log_id,
            "timestamp": timestamp,
            "type": cheating_type,
            "details": details
        }
        
        return log_entry
    
    def analyze_behavior(self, video_path, candidate_id="unknown"):
        """
        Analyze a full video for suspicious behavior
        
        Args:
            video_path (str): Path to the video file
            candidate_id (str): ID of the candidate
            
        Returns:
            dict: Analysis results
        """
        cap = cv2.VideoCapture(video_path)
        
        # Variables to track
        total_frames = 0
        suspicious_frames = 0
        face_counts = []
        cheating_timestamps = []
        sample_rate = 10  # Only analyze every 10th frame for performance
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            total_frames += 1
            
            # Skip frames based on sample rate
            if total_frames % sample_rate != 0:
                continue
                
            # Detect faces
            face_count, _ = self.detect_multiple_faces(frame)
            face_counts.append(face_count)
            
            # Check for cheating
            if face_count > self.detection_threshold:
                suspicious_frames += 1
                timestamp = total_frames / cap.get(cv2.CAP_PROP_FPS)  # Convert to seconds
                cheating_timestamps.append(timestamp)
                
                # Log this instance
                log_entry = self.log_cheating_attempt('multiple_faces', {
                    'count': face_count,
                    'frame_number': total_frames,
                    'timestamp_seconds': timestamp
                })
                
                # Save log entry to file
                self._append_to_log_file(log_entry, candidate_id)
        
        cap.release()
        
        # Calculate statistics
        analyzed_frames = total_frames // sample_rate
        suspicious_percentage = (suspicious_frames / analyzed_frames * 100) if analyzed_frames > 0 else 0
        avg_face_count = sum(face_counts) / len(face_counts) if face_counts else 0
        
        return {
            "total_frames": total_frames,
            "analyzed_frames": analyzed_frames,
            "suspicious_frames": suspicious_frames,
            "suspicious_percentage": round(suspicious_percentage, 2),
            "average_face_count": round(avg_face_count, 2),
            "cheating_timestamps": cheating_timestamps
        }
    
    def _append_to_log_file(self, log_entry, candidate_id):
        """Helper method to append a log entry to a candidate's log file"""
        log_file_path = f'uploads/logs/{candidate_id}_cheating_logs.json'
        
        try:
            # Read existing logs or create new log array
            if os.path.exists(log_file_path):
                with open(log_file_path, 'r') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
            else:
                logs = []
                
            # Append new log and write back
            logs.append(log_entry)
            
            with open(log_file_path, 'w') as f:
                json.dump(logs, f)
                
        except Exception as e:
            print(f"Error saving log: {e}")