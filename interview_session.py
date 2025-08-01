#!/usr/bin/env python3
"""
Main interview session controller for MockMantra
"""

import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable

from config import Config
from database_manager import DatabaseManager
from gpt_question_generator import GPTQuestionGenerator
from sentiment_analyzer import SentimentAnalyzer
from speech_processor import SpeechProcessor

class InterviewSession:
    """Main interview session controller"""
    
    def __init__(self, user_id: int, job_role: str, difficulty: str, 
                 progress_callback: Optional[Callable] = None,
                 feedback_callback: Optional[Callable] = None):
        self.user_id = user_id
        self.job_role = job_role
        self.difficulty = difficulty
        self.progress_callback = progress_callback
        self.feedback_callback = feedback_callback
        
        # Initialize components
        self.db = DatabaseManager()
        self.gpt_generator = GPTQuestionGenerator()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.speech_processor = SpeechProcessor()
        
        # Session data
        self.session_id = None
        self.questions = []
        self.current_question_index = 0
        self.answers = []
        self.feedback_data = []
        self.scores = []
        self.response_times = []
        
        # Session state
        self.is_active = False
        self.is_paused = False
        self.start_time = None
        self.question_start_time = None
        
        # Threading
        self.session_thread = None
        self.stop_event = threading.Event()
    
    def start_interview(self, num_questions: int = 5) -> bool:
        """Start the interview process"""
        try:
            # Create session in database
            self.session_id = self.db.create_session(self.user_id, self.job_role, self.difficulty)
            
            # Generate questions
            self.questions = self.gpt_generator.generate_questions(
                self.job_role, self.difficulty, num_questions
            )
            
            if not self.questions:
                self._notify_callback("error", "Failed to generate questions")
                return False
            
            # Initialize session
            self.start_time = datetime.now()
            self.is_active = True
            
            # Start session thread
            self.session_thread = threading.Thread(target=self._run_interview, daemon=True)
            self.session_thread.start()
            
            self._notify_callback("started", {
                "total_questions": len(self.questions),
                "estimated_duration": len(self.questions) * 3  # 3 minutes per question
            })
            
            return True
            
        except Exception as e:
            print(f"Error starting interview: {e}")
            self._notify_callback("error", f"Failed to start interview: {e}")
            return False
    
    def _run_interview(self):
        """Main interview loop"""
        try:
            # Welcome message
            welcome_msg = f"Welcome to your {self.job_role} interview at {self.difficulty} level. Let's begin!"
            self.speech_processor.speak_question(welcome_msg)
            
            # Process each question
            for i, question in enumerate(self.questions):
                if self.stop_event.is_set():
                    break
                
                self.current_question_index = i
                self._notify_progress(i, len(self.questions))
                
                # Ask question
                self._ask_question(i + 1, question)
                
                # Get answer
                answer = self._get_answer()
                
                if answer is None:  # User skipped or timeout
                    answer = ""
                
                # Analyze answer
                self._analyze_answer(question, answer, i + 1)
                
                # Brief pause between questions
                if i < len(self.questions) - 1:
                    time.sleep(2)
            
            # Complete interview
            if not self.stop_event.is_set():
                self._complete_interview()
            
        except Exception as e:
            print(f"Error in interview loop: {e}")
            self._notify_callback("error", f"Interview error: {e}")
        finally:
            self.is_active = False
    
    def _ask_question(self, question_number: int, question: str):
        """Ask a single question"""
        self._notify_callback("question", {
            "number": question_number,
            "total": len(self.questions),
            "text": question
        })
        
        question_prompt = f"Question {question_number} of {len(self.questions)}: {question}"
        self.speech_processor.speak_question(question_prompt)
        
        self.question_start_time = time.time()
    
    def _get_answer(self) -> Optional[str]:
        """Get user's answer with multiple attempts"""
        max_attempts = 3
        attempt = 1
        
        while attempt <= max_attempts and not self.stop_event.is_set():
            if self.is_paused:
                time.sleep(1)
                continue
            
            print(f"\n🎤 Attempt {attempt}/{max_attempts} - Please provide your answer...")
            
            # Listen for answer
            answer = self.speech_processor.listen_for_answer(timeout=45)
            
            if answer and len(answer.strip()) > 10:  # Minimum answer length
                response_time = time.time() - self.question_start_time
                self.response_times.append(response_time)
                return answer
            
            elif answer:
                # Answer too short, ask for elaboration
                self.speech_processor.speak_question(
                    "Your answer seems brief. Could you provide more details?"
                )
                attempt += 1
            
            else:
                # No answer detected
                if attempt < max_attempts:
                    self.speech_processor.speak_question(
                        f"I didn't catch that. Let's try again. Attempt {attempt + 1} of {max_attempts}."
                    )
                attempt += 1
        
        # If all attempts failed, record timeout
        self.response_times.append(45.0)  # Max timeout
        return None
    
    def _analyze_answer(self, question: str, answer: str, question_number: int):
        """Analyze user's answer comprehensively"""
        try:
            # GPT analysis
            gpt_analysis = self.gpt_generator.analyze_answer(question, answer, self.job_role)
            
            # Sentiment analysis
            sentiment_scores = self.sentiment_analyzer.analyze_sentiment(answer)
            emotion_scores = self.sentiment_analyzer.analyze_emotions(answer)
            
            # Confidence and communication metrics
            confidence_score = self.sentiment_analyzer.get_confidence_score(answer)
            communication_metrics = self.sentiment_analyzer.get_communication_metrics(answer)
            
            # Store results
            self.answers.append(answer)
            self.scores.append(gpt_analysis["score"])
            
            feedback_data = {
                "gpt_analysis": gpt_analysis,
                "sentiment": sentiment_scores,
                "emotions": emotion_scores,
                "confidence": confidence_score,
                "communication": communication_metrics,
                "response_time": self.response_times[-1] if self.response_times else 0
            }
            self.feedback_data.append(feedback_data)
            
            # Save to database
            self.db.add_question(
                self.session_id,
                question_number,
                question,
                answer,
                gpt_analysis,
                sentiment_scores.get('POSITIVE', 0),
                confidence_score,
                self.response_times[-1] if self.response_times else 0
            )
            
            # Provide immediate feedback
            self._provide_immediate_feedback(gpt_analysis, confidence_score)
            
            # Notify callback
            self._notify_callback("answer_analyzed", {
                "question_number": question_number,
                "score": gpt_analysis["score"],
                "confidence": confidence_score,
                "feedback": gpt_analysis
            })
            
        except Exception as e:
            print(f"Error analyzing answer: {e}")
    
    def _provide_immediate_feedback(self, gpt_analysis: Dict[str, Any], confidence_score: float):
        """Provide immediate feedback after each answer"""
        score = gpt_analysis.get("score", 5)
        strengths = gpt_analysis.get("strengths", "")
        
        if score >= 8:
            feedback_msg = f"Excellent answer! {strengths}"
            tone = "positive"
        elif score >= 6:
            feedback_msg = f"Good response. {strengths}"
            tone = "positive"
        elif score >= 4:
            feedback_msg = f"That's a start. {strengths}"
            tone = "neutral"
        else:
            feedback_msg = "Let's work on providing more detailed examples."
            tone = "constructive"
        
        self.speech_processor.speak_feedback(feedback_msg, tone)
        
        if self.feedback_callback:
            self.feedback_callback(feedback_msg, tone, score)
    
    def _complete_interview(self):
        """Complete the interview and generate final report"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Calculate overall score
        overall_score = sum(self.scores) / len(self.scores) if self.scores else 0
        
        # Generate comprehensive feedback
        final_feedback = self._generate_final_feedback(duration)
        
        # Update session in database
        self.db.update_session(
            self.session_id,
            duration=duration,
            score=overall_score,
            feedback=final_feedback,
            status="completed",
            completed_at=end_time.isoformat()
        )
        
        # Add performance metrics
        self._save_performance_metrics(duration, overall_score)
        
        # Provide final feedback
        self._deliver_final_feedback(final_feedback, duration)
        
        # Notify completion
        self._notify_callback("completed", {
            "overall_score": overall_score,
            "duration": duration,
            "feedback": final_feedback
        })
    
    def _generate_final_feedback(self, duration: float) -> Dict[str, Any]:
        """Generate comprehensive final feedback"""
        avg_score = sum(self.scores) / len(self.scores) if self.scores else 0
        avg_confidence = sum(
            feedback["confidence"] for feedback in self.feedback_data
        ) / len(self.feedback_data) if self.feedback_data else 0
        
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        # Analyze trends
        score_trend = self._analyze_score_trend()
        confidence_trend = self._analyze_confidence_trend()
        
        # Generate insights
        strengths = self._identify_strengths()
        weaknesses = self._identify_weaknesses()
        recommendations = self._generate_recommendations()
        
        return {
            "overall_score": round(avg_score, 1),
            "confidence_level": round(avg_confidence, 2),
            "average_response_time": round(avg_response_time, 1),
            "interview_duration": round(duration / 60, 1),  # Convert to minutes
            "score_trend": score_trend,
            "confidence_trend": confidence_trend,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "detailed_scores": [
                {
                    "question_number": i + 1,
                    "score": score,
                    "confidence": self.feedback_data[i]["confidence"],
                    "response_time": self.response_times[i] if i < len(self.response_times) else 0
                }
                for i, score in enumerate(self.scores)
            ]
        }
    
    def _analyze_score_trend(self) -> str:
        """Analyze how scores changed throughout the interview"""
        if len(self.scores) < 3:
            return "insufficient_data"
        
        first_half = self.scores[:len(self.scores)//2]
        second_half = self.scores[len(self.scores)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg + 0.5:
            return "improving"
        elif first_avg > second_avg + 0.5:
            return "declining"
        else:
            return "consistent"
    
    def _analyze_confidence_trend(self) -> str:
        """Analyze confidence trend throughout interview"""
        if len(self.feedback_data) < 3:
            return "insufficient_data"
        
        confidence_scores = [feedback["confidence"] for feedback in self.feedback_data]
        first_half = confidence_scores[:len(confidence_scores)//2]
        second_half = confidence_scores[len(confidence_scores)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg + 0.1:
            return "building_confidence"
        elif first_avg > second_avg + 0.1:
            return "losing_confidence"
        else:
            return "steady_confidence"
    
    def _identify_strengths(self) -> List[str]:
        """Identify candidate's key strengths"""
        strengths = []
        
        # High scoring areas
        if sum(self.scores) / len(self.scores) >= 7:
            strengths.append("Strong technical knowledge")
        
        # High confidence
        avg_confidence = sum(feedback["confidence"] for feedback in self.feedback_data) / len(self.feedback_data)
        if avg_confidence >= 0.7:
            strengths.append("Confident communication")
        
        # Good response times
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        if avg_response_time <= 30:
            strengths.append("Quick thinking")
        
        # Communication quality
        avg_communication = sum(
            sum(feedback["communication"].values()) / len(feedback["communication"])
            for feedback in self.feedback_data
        ) / len(self.feedback_data)
        
        if avg_communication >= 0.7:
            strengths.append("Clear communication")
        
        # Consistency
        if self._analyze_score_trend() == "consistent" and min(self.scores) >= 6:
            strengths.append("Consistent performance")
        
        return strengths or ["Completed the interview"]
    
    def _identify_weaknesses(self) -> List[str]:
        """Identify areas for improvement"""
        weaknesses = []
        
        # Low scores
        if sum(self.scores) / len(self.scores) < 5:
            weaknesses.append("Need to provide more detailed technical examples")
        
        # Low confidence
        avg_confidence = sum(feedback["confidence"] for feedback in self.feedback_data) / len(self.feedback_data)
        if avg_confidence < 0.5:
            weaknesses.append("Could speak with more confidence")
        
        # Slow responses
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        if avg_response_time > 40:
            weaknesses.append("Take more time to organize thoughts before speaking")
        
        # Communication issues
        communication_issues = []
        for feedback in self.feedback_data:
            comm = feedback["communication"]
            if comm["clarity"] < 0.5:
                communication_issues.append("clarity")
            if comm["structure"] < 0.5:
                communication_issues.append("structure")
            if comm["professionalism"] < 0.6:
                communication_issues.append("professionalism")
        
        if communication_issues:
            if "clarity" in communication_issues:
                weaknesses.append("Improve clarity of explanations")
            if "structure" in communication_issues:
                weaknesses.append("Better organize responses")
            if "professionalism" in communication_issues:
                weaknesses.append("Use more professional language")
        
        return weaknesses[:3]  # Limit to top 3 weaknesses
    
    def _generate_recommendations(self) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Based on job role
        role_specific = {
            "Software Engineer": [
                "Practice explaining technical concepts in simple terms",
                "Prepare examples of challenging debugging experiences",
                "Study system design fundamentals"
            ],
            "Data Scientist": [
                "Practice explaining statistical concepts to non-technical audiences",
                "Prepare examples of end-to-end ML projects",
                "Study business impact of data science work"
            ],
            "Product Manager": [
                "Practice prioritization frameworks",
                "Prepare examples of stakeholder management",
                "Study metrics and KPI selection"
            ]
        }
        
        recommendations.extend(role_specific.get(self.job_role, [
            "Practice behavioral interview questions using STAR method",
            "Prepare specific examples from your experience",
            "Research the company and role thoroughly"
        ]))
        
        # Based on performance
        avg_score = sum(self.scores) / len(self.scores) if self.scores else 0
        if avg_score < 6:
            recommendations.append("Focus on providing concrete examples with measurable results")
        
        if self._analyze_confidence_trend() == "losing_confidence":
            recommendations.append("Practice mock interviews to build confidence")
        
        return recommendations[:4]  # Limit to top 4 recommendations
    
    def _save_performance_metrics(self, duration: float, overall_score: float):
        """Save detailed performance metrics"""
        metrics = {
            "overall_score": overall_score,
            "interview_duration": duration,
            "average_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "questions_completed": len(self.scores),
            "average_confidence": sum(feedback["confidence"] for feedback in self.feedback_data) / len(self.feedback_data) if self.feedback_data else 0
        }
        
        for metric_name, metric_value in metrics.items():
            self.db.add_performance_metric(self.session_id, metric_name, metric_value)
    
    def _deliver_final_feedback(self, feedback: Dict[str, Any], duration: float):
        """Deliver final feedback via speech"""
        score = feedback["overall_score"]
        duration_minutes = round(duration / 60, 1)
        
        if score >= 8:
            overall_msg = f"Excellent work! You scored {score} out of 10."
        elif score >= 6:
            overall_msg = f"Good job! You scored {score} out of 10."
        elif score >= 4:
            overall_msg = f"You scored {score} out of 10. There's room for improvement."
        else:
            overall_msg = f"You scored {score} out of 10. Let's work on building your skills."
        
        self.speech_processor.speak_feedback(overall_msg, "neutral")
        
        # Mention key strengths
        if feedback["strengths"]:
            strengths_msg = f"Your key strengths include: {', '.join(feedback['strengths'][:2])}"
            self.speech_processor.speak_feedback(strengths_msg, "positive")
    
    def _notify_progress(self, current: int, total: int):
        """Notify progress update"""
        if self.progress_callback:
            self.progress_callback(current, total)
    
    def _notify_callback(self, event_type: str, data: Any = None):
        """Notify event callback"""
        if self.feedback_callback:
            self.feedback_callback(event_type, data)
    
    def pause_interview(self):
        """Pause the interview"""
        self.is_paused = True
        self._notify_callback("paused")
    
    def resume_interview(self):
        """Resume the interview"""
        self.is_paused = False
        self._notify_callback("resumed")
    
    def stop_interview(self):
        """Stop the interview"""
        self.stop_event.set()
        self.is_active = False
        self._notify_callback("stopped")
        
        if self.session_id:
            self.db.update_session(self.session_id, status="cancelled")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current interview status"""
        return {
            "is_active": self.is_active,
            "is_paused": self.is_paused,
            "current_question": self.current_question_index + 1,
            "total_questions": len(self.questions),
            "elapsed_time": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "current_score": sum(self.scores) / len(self.scores) if self.scores else 0
        }
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.stop_interview()
            
            if self.session_thread and self.session_thread.is_alive():
                self.session_thread.join(timeout=5)
            
            self.speech_processor.cleanup()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")