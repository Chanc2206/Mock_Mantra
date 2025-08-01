import time
import os
import re
import json
import numpy as np
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from cheating_detection import CheatingDetector
import google.generativeai as genai
import whisper
import cv2
from deepface import DeepFace
from gtts import gTTS  # Google Text-to-Speech

app = Flask(__name__)
CORS(app)

# Load API key from environment variable or config file (more secure)
API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyBFRijskHJaJaF4Szle61bgilbYbQQRVmI")
genai.configure(api_key=API_KEY)

# Load models
try:
    whisper_model = whisper.load_model("base")
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    detector = CheatingDetector()
    # Load face detection model
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
except Exception as e:
    print(f"Error loading models: {e}")

def generate_question(role):
    """Generate technical interview questions."""
    try:
        prompt = (
            f"Generate 5 role-specific, technical interview questions for a {role} position. "
            "Ensure each question tests practical knowledge and problem-solving abilities, "
            "suitable for a verbal response. Focus on core skills, frameworks, and industry practices."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating questions: {e}")
        return f"Error generating question: {str(e)}"

def transcribe_audio(audio_path):
    """Transcribe audio file to text."""
    try:
        result = whisper_model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return "Error transcribing audio"

def generate_speech(text, output_path):
    """Generate speech from text and save to file"""
    try:
        # Validate that we have text to speak
        if not text or text.strip() == "":
            print("Warning: Empty text provided to speech generator")
            return False
            
        tts = gTTS(text=text, lang='en')
        tts.save(output_path)
        return True
    except Exception as e:
        print(f"Error generating speech: {e}")
        return False
    
def analyze_facial_emotions_and_detect_cheating(video_path):
    """Analyze facial emotions and detect potential cheating in video."""
    try:
        cap = cv2.VideoCapture(video_path)
        emotions = []
        sample_rate = 10  # Only analyze every 10th frame to improve performance
        frame_count = 0
        
        # For cheating detection
        cheating_frames = []
        total_analyzed_frames = 0
        frames_with_multiple_faces = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            if frame_count % sample_rate != 0:
                continue
            
            total_analyzed_frames += 1
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Check for multiple faces (potential cheating)
            if len(faces) > 1:
                frames_with_multiple_faces += 1
                cheating_frames.append({
                    "frame_number": frame_count,
                    "face_count": len(faces)
                })
                
            # Analyze emotion of primary face (if present)
            if len(faces) > 0:
                try:
                    analysis = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                    emotions.append(analysis[0]['dominant_emotion'])
                except Exception as e:
                    print(f"Error analyzing emotions: {e}")
                    pass

        cap.release()
        
        # Calculate percentage of frames with multiple faces
        cheating_percentage = (frames_with_multiple_faces / total_analyzed_frames * 100) if total_analyzed_frames > 0 else 0
        
        # Determine dominant emotion
        dominant_emotion = "Neutral"
        if emotions:
            dominant_emotion = max(set(emotions), key=emotions.count)
        
        return {
            "dominant_emotion": dominant_emotion,
            "cheating_detected": frames_with_multiple_faces > 0,
            "cheating_percentage": round(cheating_percentage, 2),
            "cheating_frames": cheating_frames,
            "total_analyzed_frames": total_analyzed_frames
        }
    except Exception as e:
        print(f"Error analyzing video: {e}")
        return {
            "dominant_emotion": "Error",
            "cheating_detected": False,
            "cheating_percentage": 0,
            "cheating_frames": [],
            "total_analyzed_frames": 0,
            "error": str(e)
        }

def evaluate_responses(questions, full_transcript):
    """Evaluate interview responses using AI."""
    try:
        # Create a comprehensive evaluation prompt
        prompt = (
            "I'm going to provide you with a transcript of a technical interview and the questions that were asked.\n\n"
            "Questions:\n"
        )
        
        for i, question in enumerate(questions):
            prompt += f"{i+1}. {question}\n"
        
        prompt += f"\nFull transcript of candidate's responses:\n{full_transcript}\n\n"
        prompt += (
            "Please analyze this interview by:\n"
            "1. Identifying which parts of the transcript correspond to answers for each question\n"
            "2. For each question, score the answer from 0-10\n"
            "3. For each question, provide specific feedback on strengths and areas for improvement\n"
            "4. Provide an overall assessment of the candidate with a total score\n\n"
            "Format your response as follows for each question:\n"
            "Question 1: [Question text]\n"
            "Answer: [Extracted answer from transcript]\n"
            "Score: [0-10]\n"
            "Feedback: [Your feedback]\n\n"
            "... [Repeat for all questions] ...\n\n"
            "Overall Assessment:\n"
            "[Your overall assessment of the candidate's performance, technical skills, and communication abilities with they are doing cheating or not]\n"
            "Total Score: [Average of individual scores]/10\n"
            "Cheating Detection:\n"
            "[Tell the time stamp on which tab is switched or multiple face detected]"
        )
        
        response = model.generate_content(prompt)
        parsed_results = parse_evaluation_results(response.text, questions)
        return parsed_results
    except Exception as e:
        print(f"Error evaluating responses: {e}")
        return {"error": f"Error evaluating responses: {str(e)}"}

def parse_evaluation_results(evaluation_text, questions):
    """Parse AI evaluation results into structured format."""
    try:
        results = []
        overall_assessment = ""
        total_score = 0
        cheating_detected = False
        cheating_evidence = ""
        
        # Extract question sections using regex
        question_sections = re.split(r'Question \d+:', evaluation_text)[1:]  # Skip first empty element
        
        # Extract overall assessment section
        overall_match = re.search(r'Overall Assessment:(.*?)Total Score:', evaluation_text, re.DOTALL)
        if overall_match:
            overall_assessment = overall_match.group(1).strip()
        
        # Extract total score
        total_score_match = re.search(r'Total Score:\s*(\d+(\.\d+)?)', evaluation_text)
        if total_score_match:
            total_score = total_score_match.group(1)

        cheating_match = re.search(r'Cheating Detection:(.*?)(?=Question \d+:|Overall Assessment:|Total Score:|$)', 
                                    evaluation_text, re.DOTALL)
        if cheating_match:
            cheating_section = cheating_match.group(1).strip()
            cheating_detected = "detected" in cheating_section.lower() or "positive" in cheating_section.lower()
            cheating_evidence = cheating_section
        
        # Process each question section
        for i, section in enumerate(question_sections):
            if i >= len(questions):
                break
                
            result = {
                "question": questions[i].strip(),
                "answer": "",
                "score": 0,
                "feedback": ""
            }
            
            # Extract answer
            answer_match = re.search(r'Answer:(.*?)Score:', section, re.DOTALL)
            if answer_match:
                result["answer"] = answer_match.group(1).strip()
            
            # Extract score
            score_match = re.search(r'Score:\s*(\d+(\.\d+)?)', section)
            if score_match:
                result["score"] = score_match.group(1)
            
            # Extract feedback
            feedback_match = re.search(r'Feedback:(.*?)(?=Question \d+:|Overall Assessment:|$)', section, re.DOTALL)
            if feedback_match:
                result["feedback"] = feedback_match.group(1).strip()
            
            results.append(result)
        
        return {
            "question_analysis": results,
            "overall_assessment": overall_assessment,
            "total_score": total_score,
            "cheating_detection": {
                "detected": cheating_detected,
                "evidence": cheating_evidence
            }
        }
    except Exception as e:
        print(f"Error parsing evaluation results: {e}")
        return {
            "question_analysis": [],
            "overall_assessment": "Error parsing results",
            "total_score": 0,
            "cheating_detection": {
                "detected": False,
                "evidence": f"Error: {str(e)}"
            }
        }

@app.route('/')
def home():
    """Render homepage."""
    return render_template('i.html')

@app.route("/ensure-upload-dir", methods=["GET"])
def ensure_upload_dir():
    """Ensure upload directories exist."""
    try:
        os.makedirs("uploads", exist_ok=True)
        os.makedirs("uploads/logs", exist_ok=True)
        os.makedirs("uploads/audio", exist_ok=True)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/start-interview", methods=["POST"])
def start_interview():
    """Initialize interview with questions for specified role."""
    try:
        data = request.json
        role = data.get("role")
        candidate_id = data.get("candidate_id", "unknown")
        questions = generate_question(role)
        
        # Parse questions into a list
        question_list = []
        for line in questions.split('\n'):
            line = line.strip()
            if re.match(r'^\d+[\.:\)]', line):
                question_list.append(line)
        
        # If parsing failed, try another approach
        if not question_list:
            question_list = [q.strip() for q in questions.split('\n\n') if q.strip()]
        
        # Generate intro audio
        intro_text = f"Hello! I'll be your interviewer today for the {role} position. When you're ready, click 'Start Interview' to begin."
        intro_audio_path = f"uploads/audio/intro_audio.mp3"
        generate_speech(intro_text, intro_audio_path)
        
        # Generate speech files for each question
        audio_files = []
        for i, question in enumerate(question_list):
            # Clean up question text for speech
            clean_question = re.sub(r'^\d+[\.:\)]', '', question).strip()
            
            # Generate speech file
            audio_path = f"uploads/audio/question_{i+1}.mp3"
            generate_speech(clean_question, audio_path)
            audio_files.append(f"/uploads/audio/question_{i+1}.mp3")  # Path for client
        
        return jsonify({
            "question_list": [q for q in question_list],
            "audio_files": audio_files,
            "intro_audio": "/uploads/audio/intro_audio.mp3"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get-question-audio/<int:question_num>", methods=["GET"])
def get_question_audio(question_num):
    """Get audio file for a specific question."""
    try:
        audio_path = f"uploads/audio/question_{question_num}.mp3"
        if os.path.exists(audio_path):
            return send_file(audio_path, mimetype="audio/mpeg")
        else:
            return jsonify({"error": "Audio not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/speak_question", methods=["POST"])
def speak_question():
    """Generate speech for a question."""
    try:
        data = request.json
        question = data.get("question", "")
        candidate_id = data.get("candidate_id", "unknown")
        
        # Clean the question text
        clean_question = question.strip()
        
        # Generate a unique filename
        timestamp = int(time.time())
        filename = f"{candidate_id}_{timestamp}.mp3"
        audio_path = f"uploads/audio/{filename}"
        
        # Generate the speech file
        success = generate_speech(clean_question, audio_path)
        
        if success:
            # Return the URL to the audio file
            return jsonify({
                "audio_url": f"/uploads/audio/{filename}"
            })
        else:
            return jsonify({"error": "Failed to generate speech"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/analyze-interview", methods=["POST"])
def analyze_interview():
    """Analyze complete interview recording."""
    try:
        # Get questions and video file
        questions = request.form.getlist("question_list[]")
        file = request.files["video"]
        
        # Save the video file
        file_path = f"uploads/full_interview.webm"
        file.save(file_path)
        
        # Extract audio from video
        audio_path = "uploads/full_interview.wav"
        ffmpeg_command = f"ffmpeg -i \"{file_path}\" -q:a 0 -map a \"{audio_path}\""
        os.system(ffmpeg_command)
        
        # Transcribe the full interview
        transcript = transcribe_audio(audio_path)
        
        # Analyze facial emotions and detect cheating
        analysis_results = analyze_facial_emotions_and_detect_cheating(file_path)
        
        # Evaluate responses for all questions
        evaluation = evaluate_responses(questions, transcript)
        
        # Compile and return results
        return jsonify({
            "transcript": transcript,
            "emotion": analysis_results["dominant_emotion"],
            "cheating_detected": analysis_results["cheating_detected"],
            "cheating_details": {
                "percentage": analysis_results["cheating_percentage"],
                "frames_with_multiple_faces": len(analysis_results["cheating_frames"]),
                "total_analyzed_frames": analysis_results["total_analyzed_frames"],
                "suspicious_frames": analysis_results["cheating_frames"][:10]  # Limit to 10 examples
            },
            "evaluation": evaluation
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process_video_frame', methods=['POST'])
def process_video_frame():
    """Process individual video frame for real-time cheating detection."""
    try:
        # Get video frame from request
        if 'frame' not in request.files:
            return jsonify({'error': 'No frame provided'})
            
        file = request.files['frame']
        
        # Convert to OpenCV format
        nparr = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Detect faces
        face_count, marked_frame = detector.detect_multiple_faces(frame)
        
        # Check if multiple faces detected
        cheating_detected = face_count > 1
        if cheating_detected:
            log_entry = detector.log_cheating_attempt('multiple_faces', {'count': face_count})
            
            # Save log to file
            candidate_id = request.form.get('candidate_id', 'unknown')
            log_file_path = f'uploads/logs/{candidate_id}_cheating_logs.json'
            try:
                if os.path.exists(log_file_path):
                    with open(log_file_path, 'r') as f:
                        logs = json.load(f)
                else:
                    logs = []
                    
                logs.append(log_entry)
                
                with open(log_file_path, 'w') as f:
                    json.dump(logs, f)
                    
                # Also save the frame as evidence
                cv2.imwrite(f'uploads/logs/{candidate_id}_{log_entry["timestamp"].replace(":", "-")}.jpg', marked_frame)
                
            except Exception as e:
                print(f"Error saving log: {e}")
        
        # Return result
        return jsonify({
            'face_count': face_count,
            'cheating_detected': cheating_detected
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/log_tab_switch', methods=['POST'])
def log_tab_switch():
    """Log when candidate switches browser tabs."""
    try:
        data = request.get_json()
        candidate_id = data.get('candidate_id', 'unknown')
        
        log_entry = detector.log_cheating_attempt('tab_switch', {
            'timestamp': data.get('timestamp'),
            'details': 'User switched tabs during interview'
        })
        
        # Save log to file
        log_file_path = f'uploads/logs/{candidate_id}_cheating_logs.json'
        
        try:
            if os.path.exists(log_file_path):
                with open(log_file_path, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
                
            logs.append(log_entry)
            
            with open(log_file_path, 'w') as f:
                json.dump(logs, f)
                
        except Exception as e:
            print(f"Error saving log: {e}")
        
        return jsonify({'status': 'logged'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/view_logs/<candidate_id>')
def admin_view_logs(candidate_id):
    """View cheating logs for a candidate."""
    try:
        log_file_path = f'uploads/logs/{candidate_id}_cheating_logs.json'
        
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        return render_template('admin_logs.html', logs=logs, candidate_id=candidate_id)
    except Exception as e:
        return f"Error loading logs: {e}", 500

@app.route('/uploads/audio/<filename>')
def serve_audio(filename):
    """Securely serve audio files."""
    try:
        file_path = f"uploads/audio/{filename}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_file(file_path)
        else:
            return "File not found", 404
    except Exception as e:
        return f"Error serving file: {e}", 500

if __name__ == "__main__":
    # Create necessary directories on startup
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("uploads/logs", exist_ok=True)
    os.makedirs("uploads/audio", exist_ok=True)
    
    app.run(debug=True)