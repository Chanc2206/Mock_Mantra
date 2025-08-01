let mediaRecorder;
let recordedChunks = [];
let currentQuestionIndex = 0;
let questions = [];
let audioFiles = [];
let recording = false;
let stream;
let tabFocusInterval;
let isSpeaking = false;
let audioElement = new Audio();
let cheatingDetectionTimer;
let expressionCanvas;
let animationFrame;
let analyzingData = false;
let downloadingPdf = false;
let analysisRetryCount = 0;
const MAX_RETRY_ATTEMPTS = 3;
let candidateId = 'candidate_' + new Date().getTime(); // Generate a unique ID for the candidate
let interviewData;
let allQuestions = [];

// Initialize page
$(document).ready(function() {
    // First ensure upload directories exist
    $.get('/ensure-upload-dir')
        .done(function() {
            console.log("Upload directory confirmed");
        })
        .fail(function(error) {
            showMessage("Warning: Could not verify upload directory. Some features may not work correctly.", "error");
            console.error("Upload directory error:", error);
        });
    
    // Setup listeners
    $('#startSetupBtn').click(startSetup);
    $('#startBtn').click(startInterview);
    $('#nextBtn').click(nextQuestion);
    $('#stopBtn').click(stopInterview);
    
    // Load the interviewer image
    const avatarImage = document.getElementById('avatarImage');
    
    // You'd replace this with the actual path to your image
    // For now using a placeholder - in production you would use your actual image URL
    avatarImage.src = "/static/images/preview.webp"; // Replace with actual path
    
    // Set up audio ended event to stop speaking animation
    audioElement.addEventListener('ended', function() {
        stopSpeaking();
    });

    // Set up event listeners for avatar image load
    avatarImage.onload = function() {
        // Initialize facial expressions once image is loaded
        expressionCanvas = setupAvatarAnimations();
    };
    
    // Error handler for avatar image
    avatarImage.onerror = function() {
        console.warn("Avatar image failed to load, using placeholder");
        avatarImage.src = "/api/placeholder/400/400";
        // Still initialize animations even with placeholder
        expressionCanvas = setupAvatarAnimations();
    };
    
    // Tab visibility detection for cheating prevention
    document.addEventListener("visibilitychange", function() {
        if (document.hidden && recording) {
            // Log tab switch as potential cheating
            $.ajax({
                url: '/log_tab_switch',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    candidate_id: candidateId,
                    timestamp: new Date().toISOString()
                }),
                error: function(error) {
                    console.error("Failed to log tab switch:", error);
                }
            });
        }
    });
});

// Helper function to show status messages
function showMessage(message, type = "info") {
    const statusDiv = document.getElementById('statusMessages');
    const messageDiv = document.createElement('div');
    messageDiv.textContent = message;
    messageDiv.className = type === "error" ? "error-message" : 
                           type === "success" ? "success-message" : "";
    
    statusDiv.appendChild(messageDiv);
    
    // Auto-remove after 5 seconds for non-error messages
    if (type !== "error") {
        setTimeout(() => {
            if (statusDiv.contains(messageDiv)) {
                statusDiv.removeChild(messageDiv);
            }
        }, 5000);
    }
}

// Avatar animation functions
function setupAvatarAnimations() {
    // Remove the simple div mouth if it exists
    const mouthContainer = document.getElementById('mouthAnimation');
    if (mouthContainer) mouthContainer.remove();
    
    // Remove any existing canvas first to avoid duplicates
    const existingCanvas = document.getElementById('expressionCanvas');
    if (existingCanvas) existingCanvas.remove();
    
    // Create an overlay canvas for facial expressions
    const avatarContainer = document.getElementById('avatarContainer');
    const expressionCanvas = document.createElement('canvas');
    expressionCanvas.id = 'expressionCanvas';
    expressionCanvas.style.position = 'absolute';
    expressionCanvas.style.top = '0';
    expressionCanvas.style.left = '0';
    expressionCanvas.style.width = '100%';
    expressionCanvas.style.height = '100%';
    expressionCanvas.style.pointerEvents = 'none';
    avatarContainer.appendChild(expressionCanvas);
    
    // Set dimensions based on container
    const setCanvasDimensions = () => {
        const containerRect = avatarContainer.getBoundingClientRect();
        expressionCanvas.width = containerRect.width;
        expressionCanvas.height = containerRect.height;
    };
    
    // Initial sizing and resize handler
    setCanvasDimensions();
    window.addEventListener('resize', setCanvasDimensions);
    
    return expressionCanvas;
}

// Create more varied mouth animations with correct positioning
function animateSpeech(canvas, intensity = 0.5) {
    if (!canvas) return null; // Return null instead of undefined
    
    const ctx = canvas.getContext('2d');
    const avatarImage = document.getElementById('avatarImage');
    const containerRect = canvas.getBoundingClientRect();
    
    // Position relative to the face in the image - these values should be adjusted
    // based on the actual avatar image you're using
    const mouthX = containerRect.width * 0.5;  // Center horizontally
    const mouthY = containerRect.height * 0.67; // Lower third of the face
    const mouthWidth = containerRect.width * 0.25; // 25% of container width
    const mouthBaseHeight = containerRect.height * 0.04; // 4% of container height
    
    let frameCount = 0;
    
    function drawMouth() {
        // Clear previous drawing
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (!isSpeaking) return;
        
        // Calculate dynamic mouth height based on audio intensity and animation frame
        const openAmount = Math.sin(frameCount * 0.3) * intensity + intensity;
        const mouthHeight = mouthBaseHeight + (mouthBaseHeight * 3 * openAmount);
        
        // Drawing with better styling
        // Add a subtle shadow for depth
        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctx.shadowBlur = 5;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 2;
        
        // Lips outline with more natural color
        ctx.fillStyle = 'rgba(180, 90, 90, 0.85)';
        ctx.beginPath();
        
        // More natural mouth shape with curves
        ctx.moveTo(mouthX - mouthWidth/2, mouthY);
        ctx.bezierCurveTo(
            mouthX - mouthWidth/4, mouthY - mouthHeight/2,
            mouthX + mouthWidth/4, mouthY - mouthHeight/2,
            mouthX + mouthWidth/2, mouthY
        );
        ctx.bezierCurveTo(
            mouthX + mouthWidth/4, mouthY + mouthHeight/2,
            mouthX - mouthWidth/4, mouthY + mouthHeight/2,
            mouthX - mouthWidth/2, mouthY
        );
        
        ctx.fill();
        
        // Inner mouth - darker for contrast
        ctx.shadowBlur = 0; // Reset shadow for inner mouth
        ctx.fillStyle = 'rgba(100, 40, 40, 0.8)';
        const innerWidth = mouthWidth * 0.7;
        const innerHeight = mouthHeight * 0.7;
        
        ctx.beginPath();
        ctx.ellipse(
            mouthX, mouthY, 
            innerWidth/2, innerHeight/2, 
            0, 0, Math.PI * 2
        );
        ctx.fill();
        
        frameCount++;
        animationFrame = requestAnimationFrame(drawMouth);
    }
    
    return drawMouth;
}

// Update speaking animation functions
function startSpeaking() {
    isSpeaking = true;
    $('#avatarContainer').addClass('avatar-speaking');
    
    // Initialize canvas if not done yet
    if (!expressionCanvas) {
        expressionCanvas = setupAvatarAnimations();
    }
    
    // Start mouth animation with higher intensity for better visibility
    const drawMouth = animateSpeech(expressionCanvas, 0.8);
    if (drawMouth) drawMouth(); // Check if drawMouth is defined
    
    // Random eye blinks every 3-7 seconds
    const blinkInterval = setInterval(() => {
        if (isSpeaking) {
            // Simple blink animation could be added here
        } else {
            clearInterval(blinkInterval);
        }
    }, Math.random() * 4000 + 3000);
}

function stopSpeaking() {
    isSpeaking = false;
    $('#avatarContainer').removeClass('avatar-speaking');
    
    // Clear canvas
    if (expressionCanvas) {
        const ctx = expressionCanvas.getContext('2d');
        ctx.clearRect(0, 0, expressionCanvas.width, expressionCanvas.height);
    }
    
    // Cancel animation frame if active
    if (animationFrame) {
        cancelAnimationFrame(animationFrame);
        animationFrame = null;
    }
}

function startSetup() {
    const role = $('#roleSelect').val();
    if (!role) {
        showMessage("Please select a role", "error");
        return;
    }
    
    // Show loading status
    showMessage("Setting up interview for " + role + " role...");
    
    // Request camera permission
    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then(function(mediaStream) {
            stream = mediaStream;
            const video = document.getElementById('videoPreview');
            video.srcObject = mediaStream;
            video.play(); // Add play() to ensure video starts
            
            // Generate questions based on selected role
            $.ajax({
                url: '/start-interview',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ 
                    role: role
                }),
                success: function(response) {
                    // Store the full response for later use
                    interviewData = response;
                    
                    // Parse questions from the response
                    const questionsText = response.questions;
                    allQuestions = response.question_list || [];
                    
                    // If question_list is empty, try to parse from text
                    if (allQuestions.length === 0) {
                        const questionLines = questionsText.split('\n').filter(line => line.trim() !== '');
                        
                        // Extract numbered questions
                        let currentQuestion = '';
                        
                        for (const line of questionLines) {
                            if (/^\d+[\.\):]/.test(line)) {
                                if (currentQuestion) {
                                    allQuestions.push(currentQuestion.trim());
                                }
                                currentQuestion = line;
                            } else {
                                currentQuestion += ' ' + line;
                            }
                        }
                        
                        if (currentQuestion) {
                            allQuestions.push(currentQuestion.trim());
                        }
                        
                        if (allQuestions.length === 0) {
                            allQuestions = questionsText.split('\n\n').filter(q => q.trim() !== '');
                        }
                    }
                    
                    // Display questions
                    displayQuestions();
                    
                    // Move to questions step
                    $('#setup-step').addClass('hidden');
                    $('#questions-step').removeClass('hidden');
                    
                    // Update step indicator
                    $('.step').removeClass('active');
                    $('#step-1').addClass('completed');
                    $('#step-2').addClass('active');
                },
                error: function(error) {
                    console.error("Setup error:", error);
                    showMessage("Error setting up interview. Please try again.", "error");
                }
            });
        })
        .catch(function(err) {
            console.error("Media error:", err);
            showMessage("Error accessing camera or microphone. Please ensure you have granted permissions.", "error");
        });
}

function startInterview() {
    if (currentQuestionIndex >= questions.length) {
        showMessage("No more questions available", "error");
        return;
    }
    
    // Setup recording
    setupRecording();
    
    // Update UI
    $('#startBtn').prop('disabled', true);
    $('#nextBtn').prop('disabled', false);
    $('#stopBtn').prop('disabled', false);
    
    // Start recording
    startRecording();
    
    // Speak the current question
    speakQuestion(questions[currentQuestionIndex].question);
}

function speakQuestion(questionText) {
    $('#speechBubble').text(questionText);
    startSpeaking();
    
    // Request TTS for the question
    $.ajax({
        url: '/speak_question',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ 
            question: questionText,
            candidate_id: candidateId
        }),
        success: function(data) {
            if (data.audio_url) {
                audioElement.src = data.audio_url;
                audioElement.play().catch(err => {
                    console.error("Audio playback error:", err);
                    stopSpeaking();
                });
            } else {
                stopSpeaking();
                showMessage("Error: No audio URL received", "error");
            }
        },
        error: function(error) {
            console.error("TTS error:", error);
            stopSpeaking();
            showMessage("Error generating speech. Continuing with text only.", "error");
        }
    });
}

function setupRecording() {
    if (!stream) {
        showMessage("No media stream available. Please refresh and try again.", "error");
        return;
    }
    
    try {
        mediaRecorder = new MediaRecorder(stream, {mimeType: 'video/webm;codecs=vp8,opus'});
        recordedChunks = [];
        
        mediaRecorder.ondataavailable = function(e) {
            if (e.data.size > 0) {
                recordedChunks.push(e.data);
            }
        };
        
        mediaRecorder.onstop = function() {
            saveRecording();
        };
    } catch (e) {
        console.error("MediaRecorder error:", e);
        showMessage("Error setting up recording. Your browser may not support this feature.", "error");
    }
}

function startRecording() {
    if (!mediaRecorder) {
        showMessage("Recording not set up", "error");
        return;
    }
    
    recordedChunks = [];
    try {
        mediaRecorder.start();
        recording = true;
        
        // Update UI
        $('#recordingStatus').text('Recording').addClass('status-recording');
        
        // Start cheat detection
        startCheatingDetection();
    } catch (e) {
        console.error("Recording start error:", e);
        showMessage("Error starting recording", "error");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        try {
            mediaRecorder.stop();
            recording = false;
            
            // Update UI
            $('#recordingStatus').text('').removeClass('status-recording');
            
            // Stop cheat detection
            stopCheatingDetection();
        } catch (e) {
            console.error("Recording stop error:", e);
            showMessage("Error stopping recording", "error");
        }
    }
}

function saveRecording() {
    if (recordedChunks.length === 0) {
        showMessage("No recording data available", "error");
        return;
    }
    
    try {
        const blob = new Blob(recordedChunks, { type: 'video/webm' });
        const formData = new FormData();
        formData.append('video', blob);
        formData.append('question_index', currentQuestionIndex);
        formData.append('candidate_id', candidateId);
        
        // Show progress bar
        $('#progressContainer').removeClass('hidden');
        $('#progressBar').width('0%').text('0%');
        
        // Upload recording
        $.ajax({
            url: '/upload_recording',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhr: function() {
                const xhr = new XMLHttpRequest();
                xhr.upload.addEventListener('progress', function(e) {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        $('#progressBar').width(percent + '%');
                        $('#progressBar').text(percent + '%');
                    }
                });
                return xhr;
            },
            success: function(data) {
                showMessage("Recording saved successfully", "success");
                $('#progressContainer').addClass('hidden');
            },
            error: function(error) {
                console.error("Upload error:", error);
                showMessage("Error saving recording. Please try again.", "error");
                $('#progressContainer').addClass('hidden');
            }
        });
    } catch (e) {
        console.error("Save recording error:", e);
        showMessage("Error processing recording", "error");
    }
}

function nextQuestion() {
    // First stop current recording
    stopRecording();
    
    // Move to next question
    currentQuestionIndex++;
    
    if (currentQuestionIndex >= questions.length) {
        // No more questions, end interview
        stopInterview();
        return;
    }
    
    // Update UI with next question
    $('#currentQuestion').text(questions[currentQuestionIndex].question);
    
    // Start new recording and speak question
    setTimeout(() => {
        setupRecording();
        startRecording();
        speakQuestion(questions[currentQuestionIndex].question);
    }, 1000);
}

function stopInterview() {
    // Stop any ongoing recording
    stopRecording();
    
    // Disable interview controls
    $('#startBtn').prop('disabled', true);
    $('#nextBtn').prop('disabled', true);
    $('#stopBtn').prop('disabled', true);
    
    // Show analyzing state
    showMessage("Analyzing interview responses...");
    $('#progressContainer').removeClass('hidden');
    $('#progressBar').width('0%');
    $('#progressBar').text('Analyzing...');
    
    // Stop any ongoing audio
    audioElement.pause();
    stopSpeaking();
    
    // Flag for tracking analysis state
    analyzingData = true;
    analysisRetryCount = 0; // Reset retry count
    
    // Animation for progress bar during analysis
    let progress = 0;
    const analysisInterval = setInterval(() => {
        if (progress < 95 && analyzingData) {
            progress += Math.random() * 3;
            if (progress > 95) progress = 95;
            $('#progressBar').width(progress + '%');
            $('#progressBar').text('Analyzing: ' + Math.round(progress) + '%');
        } else {
            clearInterval(analysisInterval);
        }
    }, 300);
    
    // Submit for analysis
    analyzeInterviewResponses();
}

function analyzeInterviewResponses() {
    $.ajax({
        url: '/analyze_interview',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            candidate_id: candidateId,
            question_count: questions.length
        }),
        success: function(data) {
            // Analysis complete
            analyzingData = false;
            
            // Update UI
            $('#progressBar').width('100%');
            $('#progressBar').text('Complete!');
            setTimeout(() => {
                $('#progressContainer').addClass('hidden');
            }, 1000);
            
            // Show results
            displayResults(data);
        },
        error: function(error) {
            console.error("Analysis error:", error);
            
            // Retry logic
            if (analysisRetryCount < MAX_RETRY_ATTEMPTS) {
                analysisRetryCount++;
                showMessage(`Analysis failed. Retrying (${analysisRetryCount}/${MAX_RETRY_ATTEMPTS})...`, "error");
                setTimeout(() => analyzeInterviewResponses(), 5000);
            } else {
                analyzingData = false;
                showMessage("Failed to analyze interview after multiple attempts. Please try again later.", "error");
                $('#progressContainer').addClass('hidden');
            }
        }
    });
}

function displayResults(data) {
    // Check if data is valid
    if (!data || !data.overall_assessment || !data.question_assessments) {
        showMessage("Error: Invalid result data received", "error");
        return;
    }
    
    // Hide interview container
    $('#interviewContainer').addClass('hidden');
    
    // Show results container
    $('#resultsContainer').removeClass('hidden');
    
    // Build results HTML
    let resultsHTML = `
        <div class="result-summary">
            <h3>Overall Assessment</h3>
            <p>${data.overall_assessment}</p>
            <h4>Score: ${data.overall_score}/10</h4>
        </div>
    `;
    
    // Add individual question assessments
    resultsHTML += `<h3>Question Breakdown</h3>`;
    
    data.question_assessments.forEach((assessment, index) => {
        resultsHTML += `
            <div class="question-evaluation">
                <h4>Q${index + 1}: ${assessment.question}</h4>
                <p><strong>Assessment:</strong> ${assessment.assessment}</p>
                <p><strong>Score:</strong> ${assessment.score}/10</p>
            </div>
        `;
    });
    
    // Add feedback and recommendations
    resultsHTML += `
        <div class="result-section">
            <h3>Strengths</h3>
            <ul>
                ${data.strengths.map(strength => `<li>${strength}</li>`).join('')}
            </ul>
        </div>
        
        <div class="result-section">
            <h3>Areas for Improvement</h3>
            <ul>
                ${data.areas_for_improvement.map(area => `<li>${area}</li>`).join('')}
            </ul>
        </div>
        
        <div class="result-section">
            <h3>Recommended Resources</h3>
            <ul>
                ${data.recommended_resources.map(resource => `<li>${resource}</li>`).join('')}
            </ul>
        </div>
    `;
    
    // Add PDF download button
    resultsHTML += `
        <button id="downloadPdfBtn" class="download-btn">Download Results as PDF</button>
        <div id="pdfDownloadStatus"></div>
    `;
    
    // Display results
    $('#resultsContent').html(resultsHTML);
    
    // Setup PDF download button
    $('#downloadPdfBtn').click(function() {
        downloadPdf();
    });
}

function displayQuestions() {
    let questionsHtml = '<ol>';
    allQuestions.forEach(question => {
        questionsHtml += '<li class="question-item">' + question + '</li>';
    });
    questionsHtml += '</ol>';
    
    $('#questions-container').html(questionsHtml);
}

function displayAllQuestions() {
    let questionsHtml = '<h3>Answer all these questions:</h3><ol>';
    allQuestions.forEach(question => {
        questionsHtml += '<li class="question-item">' + question + '</li>';
    });
    questionsHtml += '</ol>';
    
    $('#all-questions-container').html(questionsHtml);
}

function downloadPdf() {
    if (downloadingPdf) return;
    downloadingPdf = true;
    
    // Show download status
    $('#pdfDownloadStatus').html('<div>Generating PDF... <div class="loader"></div></div>');
    
    $.ajax({
        url: '/generate_pdf',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            candidate_id: candidateId
        }),
        success: function(response) {
            if (response.pdf_url) {
                // Create a download link
                const link = document.createElement('a');
                link.href = response.pdf_url;
                link.download = 'Interview_Results.pdf';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                // Update status
                $('#pdfDownloadStatus').html('<div class="success-message">PDF downloaded successfully!</div>');
                downloadingPdf = false;
            } else {
                $('#pdfDownloadStatus').html('<div class="error-message">Error: No PDF URL received</div>');
                downloadingPdf = false;
            }
        },
        error: function(error) {
            console.error("PDF generation error:", error);
            $('#pdfDownloadStatus').html('<div class="error-message">Error generating PDF. Please try again.</div>');
            downloadingPdf = false;
        }
    });
}

// Cheating detection functions
function startCheatingDetection() {
    // Tab focus check every second
    tabFocusInterval = setInterval(() => {
        if (!document.hasFocus() && recording) {
            // Log potential cheating event
            $.ajax({
                url: '/log_cheating',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    candidate_id: candidateId,
                    type: 'tab_switch',
                    timestamp: new Date().toISOString(),
                    question_index: currentQuestionIndex
                }),
                error: function(error) {
                    console.error("Failed to log cheating event:", error);
                }
            });
        }
    }, 1000);
}

function stopCheatingDetection() {
    if (tabFocusInterval) {
        clearInterval(tabFocusInterval);
        tabFocusInterval = null;
    }
}

// Cleanup function for when the window is closed
window.addEventListener('beforeunload', function() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
    
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    
    stopCheatingDetection();
});