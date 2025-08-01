#!/usr/bin/env python3
"""
Database manager for MockMantra
Handles all database operations
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from config import Config

class DatabaseManager:
    """Handles all database operations for MockMantra"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Config.DATABASE_PATH)
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # Interview sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    job_role TEXT NOT NULL,
                    difficulty_level TEXT NOT NULL,
                    duration INTEGER,
                    score REAL,
                    feedback TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Questions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    question_number INTEGER,
                    question_text TEXT NOT NULL,
                    user_answer TEXT,
                    ai_feedback TEXT,
                    sentiment_score REAL,
                    confidence_score REAL,
                    response_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions (id)
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions (id)
                )
            ''')
            
            conn.commit()
    
    def create_user(self, username: str, email: str) -> int:
        """Create a new user and return user ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    "INSERT INTO users (username, email) VALUES (?, ?)",
                    (username, email)
                )
                user_id = cursor.lastrowid
                conn.commit()
                return user_id
            except sqlite3.IntegrityError as e:
                if "username" in str(e):
                    return self.get_user_by_username(username)["id"]
                elif "email" in str(e):
                    return self.get_user_by_email(email)["id"]
                raise
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "created_at": row[3],
                    "last_login": row[4]
                }
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "created_at": row[3],
                    "last_login": row[4]
                }
            return None
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), user_id)
            )
            conn.commit()
    
    def create_session(self, user_id: int, job_role: str, difficulty: str) -> int:
        """Create a new interview session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO interview_sessions (user_id, job_role, difficulty_level) VALUES (?, ?, ?)",
                (user_id, job_role, difficulty)
            )
            session_id = cursor.lastrowid
            conn.commit()
            return session_id
    
    def update_session(self, session_id: int, **kwargs):
        """Update interview session with provided data"""
        if not kwargs:
            return
        
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['duration', 'score', 'feedback', 'status', 'completed_at']:
                fields.append(f"{key} = ?")
                if key == 'feedback' and isinstance(value, dict):
                    values.append(json.dumps(value))
                else:
                    values.append(value)
        
        if fields:
            query = f"UPDATE interview_sessions SET {', '.join(fields)} WHERE id = ?"
            values.append(session_id)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
    
    def add_question(self, session_id: int, question_num: int, question_text: str, 
                    user_answer: str = None, ai_feedback: str = None, 
                    sentiment_score: float = None, confidence_score: float = None,
                    response_time: float = None) -> int:
        """Add a question and its response to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            feedback_json = json.dumps(ai_feedback) if isinstance(ai_feedback, dict) else ai_feedback
            
            cursor.execute(
                """INSERT INTO questions (session_id, question_number, question_text, 
                   user_answer, ai_feedback, sentiment_score, confidence_score, response_time) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, question_num, question_text, user_answer, feedback_json,
                 sentiment_score, confidence_score, response_time)
            )
            
            question_id = cursor.lastrowid
            conn.commit()
            return question_id
    
    def get_session_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's interview session history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM interview_sessions 
                   WHERE user_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (user_id, limit)
            )
            
            sessions = []
            for row in cursor.fetchall():
                feedback = row[5]
                if feedback:
                    try:
                        feedback = json.loads(feedback)
                    except json.JSONDecodeError:
                        pass
                
                sessions.append({
                    "id": row[0],
                    "user_id": row[1],
                    "job_role": row[2],
                    "difficulty_level": row[3],
                    "duration": row[4],
                    "score": row[5],
                    "feedback": feedback,
                    "status": row[6],
                    "created_at": row[7],
                    "completed_at": row[8]
                })
            
            return sessions
    
    def get_session_questions(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all questions for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM questions 
                   WHERE session_id = ? 
                   ORDER BY question_number""",
                (session_id,)
            )
            
            questions = []
            for row in cursor.fetchall():
                ai_feedback = row[5]
                if ai_feedback:
                    try:
                        ai_feedback = json.loads(ai_feedback)
                    except json.JSONDecodeError:
                        pass
                
                questions.append({
                    "id": row[0],
                    "session_id": row[1],
                    "question_number": row[2],
                    "question_text": row[3],
                    "user_answer": row[4],
                    "ai_feedback": ai_feedback,
                    "sentiment_score": row[6],
                    "confidence_score": row[7],
                    "response_time": row[8],
                    "created_at": row[9]
                })
            
            return questions
    
    def add_performance_metric(self, session_id: int, metric_name: str, metric_value: float):
        """Add a performance metric for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO performance_metrics (session_id, metric_name, metric_value) VALUES (?, ?, ?)",
                (session_id, metric_name, metric_value)
            )
            conn.commit()
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Basic session stats
            cursor.execute(
                """SELECT COUNT(*), AVG(score), AVG(duration), MAX(score) 
                   FROM interview_sessions 
                   WHERE user_id = ? AND status = 'completed'""",
                (user_id,)
            )
            session_stats = cursor.fetchone()
            
            # Recent sessions
            cursor.execute(
                """SELECT job_role, difficulty_level, score, created_at 
                   FROM interview_sessions 
                   WHERE user_id = ? AND status = 'completed'
                   ORDER BY created_at DESC 
                   LIMIT 5""",
                (user_id,)
            )
            recent_sessions = cursor.fetchall()
            
            # Performance trends
            cursor.execute(
                """SELECT DATE(created_at) as date, AVG(score) as avg_score
                   FROM interview_sessions 
                   WHERE user_id = ? AND status = 'completed'
                   GROUP BY DATE(created_at)
                   ORDER BY date DESC 
                   LIMIT 30""",
                (user_id,)
            )
            performance_trend = cursor.fetchall()
            
            return {
                "total_sessions": session_stats[0] or 0,
                "average_score": session_stats[1] or 0,
                "average_duration": session_stats[2] or 0,
                "best_score": session_stats[3] or 0,
                "recent_sessions": [
                    {
                        "job_role": row[0],
                        "difficulty": row[1],
                        "score": row[2],
                        "date": row[3]
                    } for row in recent_sessions
                ],
                "performance_trend": [
                    {"date": row[0], "score": row[1]} 
                    for row in performance_trend
                ]
            }
    
    def cleanup_incomplete_sessions(self, older_than_hours: int = 24):
        """Remove incomplete sessions older than specified hours"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """DELETE FROM interview_sessions 
                   WHERE status = 'pending' 
                   AND datetime(created_at) < datetime('now', '-{} hours')""".format(older_than_hours)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count