# Scan2Score - AI Subjective Answer Evaluation System

An intelligent system for evaluating handwritten and scanned answer sheets using advanced AI technologies including Claude 3, PaddleOCR, and comprehensive plagiarism detection via GPTZero and CopyLeaks APIs.

## 🌟 Features

### Core Capabilities
- **📄 OCR Processing**: Advanced text extraction from handwritten and scanned documents using PaddleOCR
- **🧠 AI Evaluation**: Intelligent subjective answer grading using Claude 3 with Chain-of-Thought reasoning
- **🔍 Plagiarism Detection**: Multi-layered plagiarism detection combining GPTZero and CopyLeaks APIs
- **📋 Rubric Management**: Flexible grading rubrics with AI-assisted generation
- **📊 Performance Analytics**: Comprehensive student performance insights and trends
- **🌐 Modern UI**: Responsive web interface with real-time updates

### Technical Features
- **🔐 Secure Authentication**: JWT-based user authentication with role-based access
- **💾 MongoDB Integration**: Scalable NoSQL database for data management
- **📈 Real-time Analytics**: Interactive charts and performance metrics
- **🎯 Chain-of-Thought Reasoning**: Detailed evaluation process with step-by-step analysis
- **⚡ Async Processing**: Efficient handling of multiple evaluation requests
- **🔄 Contextual Feedback**: Constructive feedback generation for student improvement

## 🏗️ Architecture

```
scan2score/
├── backend/
│   ├── api/               # API route handlers
│   ├── database/          # MongoDB connection and models
│   ├── services/          # Core business logic services
│   │   ├── ocr_service.py          # PaddleOCR integration
│   │   ├── ai_evaluator.py         # Claude 3 evaluation engine
│   │   └── plagiarism_detector.py  # Multi-API plagiarism detection
│   └── config/            # Configuration management
├── frontend/
│   ├── templates/         # HTML templates
│   ├── static/
│   │   ├── css/          # Styling
│   │   └── js/           # JavaScript application logic
├── models/               # Data models and schemas
├── utils/                # Utility functions
├── tests/                # Test suites
├── uploads/              # File upload storage
└── temp/                 # Temporary processing files
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **MongoDB 4.4+**
- **API Keys**:
  - Anthropic API key (for Claude 3)
  - OpenAI API key (optional fallback)
  - GPTZero API key (for AI detection)
  - CopyLeaks API credentials (for plagiarism detection)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd scan2score
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Start MongoDB**:
   ```bash
   # Using Docker
   docker run -d -p 27017:27017 --name mongodb mongo:latest
   
   # Or use local MongoDB installation
   mongod --dbpath /path/to/your/db
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure the following:

```env
# Required API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key-optional
GPTZERO_API_KEY=your-gptzero-api-key
COPYLEAKS_EMAIL=your-copyleaks-email
COPYLEAKS_API_KEY=your-copyleaks-api-key

# Database
MONGODB_URI=mongodb://localhost:27017/scan2score

# Security
SECRET_KEY=your-secure-secret-key
JWT_EXPIRATION_HOURS=24
```

### Database Setup

The application will automatically create necessary collections and indexes on first run. No manual database setup is required.

## 📖 Usage Guide

### For Teachers

1. **Create Account**: Register as a teacher to access rubric creation features
2. **Create Rubrics**: Design custom grading rubrics or use AI-generated templates
3. **Upload Documents**: Upload student answer sheets (PDF, images, DOCX)
4. **Review Evaluations**: Monitor AI evaluations and provide manual overrides
5. **Analyze Performance**: View class-wide analytics and individual student progress

### For Students

1. **Submit Answers**: Upload handwritten or typed answer sheets
2. **View Feedback**: Access detailed evaluation results with constructive feedback
3. **Track Progress**: Monitor performance trends and improvement areas
4. **Review Plagiarism**: Understand plagiarism detection results

## 🔍 API Documentation

### Authentication

All API endpoints (except registration and login) require JWT authentication:

```javascript
Authorization: Bearer <your-jwt-token>
```


#### File Upload and OCR
```http
POST /api/upload
Content-Type: multipart/form-data

Parameters:
- file: Document file (PDF, PNG, JPG, DOCX)
- question: Question text (optional)
- assignment_id: Assignment identifier (optional)
```


## 🧠 AI Evaluation Process

### Chain-of-Thought Reasoning

The AI evaluator follows a structured approach:

1. **Content Analysis**: Examines key concepts, facts, and arguments
2. **Structure Assessment**: Evaluates logical flow and organization
3. **Critical Thinking**: Analyzes reasoning depth and evidence use
4. **Rubric Application**: Systematic application of grading criteria
5. **Feedback Generation**: Constructive feedback for improvement

### Plagiarism Detection Pipeline

1. **AI Content Detection**: GPTZero analysis for AI-generated content
2. **Traditional Plagiarism**: CopyLeaks comparison against web sources
3. **Pattern Analysis**: Custom algorithms for suspicious patterns
4. **Confidence Scoring**: Weighted confidence based on multiple signals

## 📊 Performance Analytics

### Student Metrics
- Score trends over time
- Subject-wise performance breakdown
- Improvement areas identification
- Plagiarism incident tracking

### Class Analytics
- Average performance statistics
- Score distribution analysis
- Common weakness identification
- Comparative performance metrics




### Production Considerations

1. **Environment**: Set `FLASK_ENV=production`
2. **Database**: Use MongoDB Atlas or dedicated MongoDB server
3. **Security**: Generate strong `SECRET_KEY`
4. **SSL**: Enable HTTPS in production
5. **Monitoring**: Implement logging and monitoring
6. **Scaling**: Consider load balancing for high traffic


## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Use meaningful commit messages
- Add type hints for new functions

## 🙏 Acknowledgments

- **Anthropic** for Claude 3 API
- **OpenAI** for GPT models
- **PaddlePaddle** for OCR capabilities
- **GPTZero** for AI detection
- **CopyLeaks** for plagiarism detection
- **MongoDB** for database technology
- **Flask** for web framework

## 📞 Support

For support, please:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
4. Contact the development team


