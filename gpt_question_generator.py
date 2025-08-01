#!/usr/bin/env python3
"""
GPT-powered question generation and answer analysis
"""

import openai
import json
import re
from typing import Dict, List, Any, Optional
from config import Config

class GPTQuestionGenerator:
    """Generates dynamic interview questions using GPT-4"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.OPENAI_API_KEY
        openai.api_key = self.api_key
        self.question_history = []
        self.fallback_questions = self._load_fallback_questions()
    
    def generate_questions(self, job_role: str, difficulty: str, num_questions: int = 5) -> List[str]:
        """Generate interview questions based on job role and difficulty"""
        
        # Create context-aware prompt
        prompt = self._create_question_prompt(job_role, difficulty, num_questions)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert technical interviewer with 10+ years of experience. Generate challenging, relevant interview questions."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            questions_text = response.choices[0].message.content.strip()
            questions = self._parse_questions(questions_text)
            
            # Store in history to avoid repetition
            self.question_history.extend(questions)
            
            return questions[:num_questions]  # Ensure we return exact number requested
            
        except Exception as e:
            print(f"Error generating questions with GPT: {e}")
            return self._get_fallback_questions(job_role, difficulty, num_questions)
    
    def analyze_answer(self, question: str, answer: str, job_role: str) -> Dict[str, Any]:
        """Analyze user's answer and provide detailed feedback"""
        
        prompt = self._create_analysis_prompt(question, answer, job_role)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert interview evaluator. Provide detailed, constructive feedback on interview answers."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content
            return self._parse_analysis(analysis_text)
            
        except Exception as e:
            print(f"Error analyzing answer with GPT: {e}")
            return self._get_fallback_analysis(answer)
    
    def generate_follow_up(self, question: str, answer: str, job_role: str) -> str:
        """Generate a follow-up question based on the answer"""
        
        prompt = f"""
        Based on this interview exchange, generate ONE relevant follow-up question:
        
        Original Question: {question}
        Candidate's Answer: {answer}
        Job Role: {job_role}
        
        The follow-up should:
        - Dig deeper into their experience
        - Test practical knowledge
        - Be specific to {job_role}
        - Be concise and focused
        
        Return only the follow-up question, nothing else.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.6
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating follow-up: {e}")
            return "Can you provide a specific example of how you've applied this in practice?"
    
    def _create_question_prompt(self, job_role: str, difficulty: str, num_questions: int) -> str:
        """Create a detailed prompt for question generation"""
        
        avoided_questions = "\n".join([f"- {q}" for q in self.question_history[-10:]])  # Last 10 questions
        
        return f"""
        Generate exactly {num_questions} interview questions for a {job_role} position at {difficulty} level.
        
        Requirements:
        - Mix of technical (40%), behavioral (30%), and situational (30%) questions
        - Questions should be specific to {job_role} responsibilities
        - {difficulty} difficulty means: {self._get_difficulty_description(difficulty)}
        - Each question should test different competencies
        - Avoid generic questions
        
        AVOID these recently used questions:
        {avoided_questions if avoided_questions.strip() else "None"}
        
        Format your response as:
        1. [First question]
        2. [Second question]
        ...
        
        Focus on real-world scenarios and practical problem-solving for {job_role}.
        """
    
    def _create_analysis_prompt(self, question: str, answer: str, job_role: str) -> str:
        """Create prompt for answer analysis"""
        
        return f"""
        Evaluate this interview answer for a {job_role} position:
        
        QUESTION: {question}
        ANSWER: {answer}
        
        Provide analysis in this EXACT format:
        
        SCORE: [Integer from 1-10]
        STRENGTHS: [2-3 specific strengths in the answer]
        WEAKNESSES: [1-2 areas that could be improved]
        SUGGESTIONS: [Specific advice for improvement]
        KEYWORDS: [Key technical terms or concepts mentioned]
        COMPLETENESS: [How complete was the answer - Poor/Fair/Good/Excellent]
        
        Evaluation criteria:
        - Technical accuracy and depth
        - Communication clarity
        - Practical experience demonstration
        - Problem-solving approach
        - Relevance to {job_role}
        """
    
    def _parse_questions(self, questions_text: str) -> List[str]:
        """Parse generated questions from GPT response"""
        questions = []
        lines = questions_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Remove numbering (1., 2., etc.)
            if re.match(r'^\d+\.?\s+', line):
                question = re.sub(r'^\d+\.?\s+', '', line)
                questions.append(question.strip())
            elif line.startswith('-') or line.startswith('•'):
                question = line[1:].strip()
                questions.append(question)
            elif len(line) > 20 and '?' in line:  # Likely a question
                questions.append(line)
        
        return questions
    
    def _parse_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse GPT analysis response into structured data"""
        analysis = {
            "score": 5.0,
            "strengths": "Response provided",
            "weaknesses": "Could be more detailed",
            "suggestions": "Provide more specific examples",
            "keywords": [],
            "completeness": "Fair"
        }
        
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                key = parts[0].strip().upper()
                value = parts[1].strip()
                
                if key == 'SCORE':
                    try:
                        score_match = re.search(r'(\d+)', value)
                        if score_match:
                            analysis["score"] = float(score_match.group(1))
                    except:
                        pass
                elif key == 'STRENGTHS':
                    analysis["strengths"] = value
                elif key == 'WEAKNESSES':
                    analysis["weaknesses"] = value
                elif key == 'SUGGESTIONS':
                    analysis["suggestions"] = value
                elif key == 'KEYWORDS':
                    # Parse keywords (might be comma-separated)
                    keywords = [k.strip() for k in value.split(',') if k.strip()]
                    analysis["keywords"] = keywords
                elif key == 'COMPLETENESS':
                    analysis["completeness"] = value
        
        return analysis
    
    def _get_difficulty_description(self, difficulty: str) -> str:
        """Get description for difficulty level"""
        descriptions = {
            "Beginner": "Entry-level questions focusing on fundamentals and basic concepts",
            "Intermediate": "Mid-level questions requiring 2-3 years experience and practical knowledge",
            "Advanced": "Senior-level questions involving complex problem-solving and leadership",
            "Expert": "Principal/Staff level questions requiring deep expertise and system design"
        }
        return descriptions.get(difficulty, descriptions["Intermediate"])
    
    def _load_fallback_questions(self) -> Dict[str, List[str]]:
        """Load fallback questions for when API fails"""
        return {
            "software_engineer": {
                "Beginner": [
                    "Explain the difference between a class and an object in object-oriented programming.",
                    "What is the purpose of version control systems like Git?",
                    "Describe the basic structure of an HTML document.",
                    "What are the main differences between HTTP and HTTPS?",
                    "Explain what a database index is and why it's useful."
                ],
                "Intermediate": [
                    "Design a system to handle user authentication and authorization.",
                    "Explain the differences between SQL and NoSQL databases with examples.",
                    "How would you optimize a slow-performing web application?",
                    "Describe your approach to debugging a production issue.",
                    "What are design patterns and can you explain a few common ones?"
                ],
                "Advanced": [
                    "Design a distributed caching system for a high-traffic application.",
                    "How would you implement a rate limiting system?",
                    "Explain microservices architecture and its trade-offs.",
                    "Design a system to handle real-time notifications to millions of users.",
                    "How would you approach refactoring a legacy monolithic application?"
                ],
                "Expert": [
                    "Design a global content delivery network from scratch.",
                    "How would you build a system to handle financial transactions at scale?",
                    "Design a recommendation engine for a streaming platform.",
                    "Architect a system for real-time fraud detection.",
                    "How would you design a search engine indexing system?"
                ]
            },
            "data_scientist": {
                "Beginner": [
                    "What is the difference between supervised and unsupervised learning?",
                    "Explain what overfitting means in machine learning.",
                    "What are the basic steps in the data science process?",
                    "How do you handle missing values in a dataset?",
                    "What is the purpose of cross-validation?"
                ],
                "Intermediate": [
                    "How would you approach a classification problem with imbalanced data?",
                    "Explain the bias-variance tradeoff in machine learning.",
                    "How do you choose between different machine learning algorithms?",
                    "Describe your approach to feature engineering.",
                    "How would you design an A/B test for a new product feature?"
                ],
                "Advanced": [
                    "Design a recommendation system for an e-commerce platform.",
                    "How would you build a real-time fraud detection model?",
                    "Explain how you would approach time series forecasting for sales data.",
                    "Design an ML pipeline for processing streaming data.",
                    "How would you optimize hyperparameters for a complex model?"
                ],
                "Expert": [
                    "Design a complete ML infrastructure for a large organization.",
                    "How would you build a multi-armed bandit system for content optimization?",
                    "Design a causal inference study to measure marketing campaign effectiveness.",
                    "Build a system for automated model monitoring and retraining.",
                    "How would you architect a real-time ML serving platform?"
                ]
            }
        }
    
    def _get_fallback_questions(self, job_role: str, difficulty: str, num_questions: int) -> List[str]:
        """Get fallback questions when API fails"""
        role_key = job_role.lower().replace(' ', '_')
        
        if role_key in self.fallback_questions and difficulty in self.fallback_questions[role_key]:
            questions = self.fallback_questions[role_key][difficulty]
            return questions[:num_questions]
        
        # Default fallback
        return [
            "Tell me about a challenging project you've worked on recently.",
            "How do you approach problem-solving in your field?",
            "Describe a time when you had to learn a new technology quickly.",
            "What interests you most about this role?",
            "How do you stay updated with industry trends?"
        ][:num_questions]
    
    def _get_fallback_analysis(self, answer: str) -> Dict[str, Any]:
        """Provide fallback analysis when API fails"""
        word_count = len(answer.split()) if answer else 0
        
        if word_count == 0:
            score = 1
            completeness = "Poor"
        elif word_count < 20:
            score = 3
            completeness = "Poor"
        elif word_count < 50:
            score = 5
            completeness = "Fair"
        elif word_count < 100:
            score = 7
            completeness = "Good"
        else:
            score = 8
            completeness = "Excellent"
        
        return {
            "score": score,
            "strengths": "Response provided with reasonable detail" if word_count > 20 else "Response provided",
            "weaknesses": "Could provide more specific examples" if word_count < 50 else "Good response length",
            "suggestions": "Try to include specific examples and technical details",
            "keywords": [],
            "completeness": completeness
        }