#!/usr/bin/env python3
"""
REST API for Voice Sentiment Analysis System
Provides endpoints for integrating the pipeline into other applications
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import tempfile
import uuid
from voice_sentiment import VoiceSentimentAnalyzer
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the analyzer (singleton)
analyzer = None

def get_analyzer():
    """Get or create analyzer instance"""
    global analyzer
    if analyzer is None:
        logger.info("Initializing Voice Sentiment Analyzer...")
        analyzer = VoiceSentimentAnalyzer()
        logger.info("Analyzer ready!")
    return analyzer

# API Documentation HTML Template
API_DOCS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Voice Sentiment Analysis API Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 30px; }
        .endpoint { background: #f9f9f9; padding: 15px; margin: 20px 0; border-left: 4px solid #007cba; }
        .method { background: #007cba; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }
        .method.get { background: #28a745; }
        .method.post { background: #007cba; }
        pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
        code { background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
        .example { margin: 10px 0; }
        h1 { color: #333; }
        h2 { color: #007cba; border-bottom: 2px solid #007cba; padding-bottom: 5px; }
        h3 { color: #555; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Voice Sentiment Analysis API</h1>
        <p><strong>Version:</strong> 1.0.0</p>
        <p><strong>Base URL:</strong> <code>{{ base_url }}</code></p>
        <p>Analyze customer call sentiment using Wav2Vec 2.0 + BERT pipeline</p>
    </div>

    <h2>Authentication</h2>
    <p>No authentication required for this API.</p>

    <h2>Supported Audio Formats</h2>
    <ul>
        <li><strong>WAV</strong> (.wav) - Recommended</li>
        <li><strong>MP3</strong> (.mp3)</li>
        <li><strong>M4A</strong> (.m4a)</li>
    </ul>

    <h2>API Endpoints</h2>

    <div class="endpoint">
        <h3><span class="method get">GET</span> /docs</h3>
        <p><strong>Description:</strong> This documentation page</p>
        <p><strong>Response:</strong> HTML documentation</p>
    </div>

    <div class="endpoint">
        <h3><span class="method get">GET</span> /health</h3>
        <p><strong>Description:</strong> Health check endpoint</p>
        <p><strong>Response:</strong></p>
        <pre><code>{
  "status": "healthy",
  "service": "Voice Sentiment Analysis API",
  "version": "1.0.0"
}</code></pre>
    </div>

    <div class="endpoint">
        <h3><span class="method post">POST</span> /analyze</h3>
        <p><strong>Description:</strong> Analyze a single audio file for sentiment</p>
        <p><strong>Content-Type:</strong> multipart/form-data</p>
        <p><strong>Parameters:</strong></p>
        <ul>
            <li><code>audio</code> (file, required): Audio file to analyze</li>
        </ul>
        
        <div class="example">
            <p><strong>Example Request (cURL):</strong></p>
            <pre><code>curl -X POST \\
  -F "audio=@call1.wav" \\
  {{ base_url }}/analyze</code></pre>
        </div>

        <div class="example">
            <p><strong>Example Response:</strong></p>
            <pre><code>{
  "success": true,
  "data": {
    "filename": "call1.wav",
    "transcription": "Hello I am very satisfied with your service",
    "sentiment": "POSITIVE",
    "confidence_score": 0.89,
    "satisfaction": "Satisfied"
  },
  "processing_id": "uuid-string"
}</code></pre>
        </div>

        <div class="example">
            <p><strong>Error Response:</strong></p>
            <pre><code>{
  "error": "Unsupported file format",
  "message": "Supported formats: .wav, .mp3, .m4a, .flac",
  "received": ".txt"
}</code></pre>
        </div>
    </div>

    <div class="endpoint">
        <h3><span class="method post">POST</span> /analyze/batch</h3>
        <p><strong>Description:</strong> Analyze multiple audio files</p>
        <p><strong>Content-Type:</strong> multipart/form-data</p>
        <p><strong>Parameters:</strong></p>
        <ul>
            <li><code>audio</code> (files, required): Multiple audio files to analyze</li>
        </ul>

        <div class="example">
            <p><strong>Example Request (cURL):</strong></p>
            <pre><code>curl -X POST \\
  -F "audio=@call1.wav" \\
  -F "audio=@call2.mp3" \\
  {{ base_url }}/analyze/batch</code></pre>
        </div>

        <div class="example">
            <p><strong>Example Response:</strong></p>
            <pre><code>{
  "success": true,
  "batch_id": "uuid-string",
  "statistics": {
    "total_files": 2,
    "sentiment_distribution": {
      "POSITIVE": {"count": 1, "percentage": 50.0},
      "NEGATIVE": {"count": 1, "percentage": 50.0}
    },
    "satisfaction_distribution": {
      "Satisfied": {"count": 1, "percentage": 50.0},
      "Dissatisfied": {"count": 1, "percentage": 50.0}
    }
  },
  "results": [
    {
      "filename": "call1.wav",
      "transcription": "Hello I am satisfied",
      "sentiment": "POSITIVE",
      "confidence_score": 0.89,
      "satisfaction": "Satisfied",
      "success": true
    },
    {
      "filename": "call2.mp3",
      "transcription": "This is terrible service",
      "sentiment": "NEGATIVE",
      "confidence_score": 0.92,
      "satisfaction": "Dissatisfied",
      "success": true
    }
  ],
  "processed_files": 2,
  "total_uploaded": 2
}</code></pre>
        </div>
    </div>

    <div class="endpoint">
        <h3><span class="method get">GET</span> /models/info</h3>
        <p><strong>Description:</strong> Get information about loaded models</p>
        <p><strong>Response:</strong></p>
        <pre><code>{
  "speech_recognition": {
    "model": "facebook/wav2vec2-large-960h-lv60-self",
    "type": "Wav2Vec 2.0",
    "language": "English",
    "description": "Large Wav2Vec 2.0 model for English speech recognition"
  },
  "sentiment_analysis": {
    "model": "nlptown/bert-base-multilingual-uncased-sentiment",
    "type": "BERT",
    "language": "Multilingual",
    "description": "Multilingual BERT for sentiment analysis"
  },
  "supported_formats": [".wav", ".mp3", ".m4a", ".flac"],
  "classifications": {
    "sentiments": ["POSITIVE", "NEGATIVE", "NEUTRAL"],
    "satisfaction": ["Satisfied", "Dissatisfied", "Neutral"]
  }
}</code></pre>
    </div>

    <h2>Response Codes</h2>
    <ul>
        <li><strong>200</strong> - Success</li>
        <li><strong>400</strong> - Bad Request (invalid file, missing parameters)</li>
        <li><strong>404</strong> - Endpoint Not Found</li>
        <li><strong>413</strong> - File Too Large (>16MB)</li>
        <li><strong>500</strong> - Internal Server Error</li>
    </ul>

    <h2>Integration Examples</h2>
    
    <h3>Python</h3>
    <pre><code>import requests

# Single file analysis
with open('audio.wav', 'rb') as f:
    response = requests.post(
        '{{ base_url }}/analyze',
        files={'audio': f}
    )
    result = response.json()
    print(f"Sentiment: {result['data']['sentiment']}")

# Batch analysis
files = [
    ('audio', open('call1.wav', 'rb')),
    ('audio', open('call2.mp3', 'rb'))
]
response = requests.post('{{ base_url }}/analyze/batch', files=files)
result = response.json()
print(f"Processed {result['processed_files']} files")</code></pre>

    <h3>JavaScript</h3>
    <pre><code>// Single file upload
const formData = new FormData();
formData.append('audio', fileInput.files[0]);

fetch('{{ base_url }}/analyze', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log('Sentiment:', data.data.sentiment);
});</code></pre>

    <h3>Node.js</h3>
    <pre><code>const fs = require('fs');
const FormData = require('form-data');

const form = new FormData();
form.append('audio', fs.createReadStream('call.wav'));

fetch('{{ base_url }}/analyze', {
    method: 'POST',
    body: form
})
.then(response => response.json())
.then(data => console.log(data));</code></pre>

    <h2>Rate Limits</h2>
    <p>Currently no rate limits are enforced. For production use, consider implementing rate limiting.</p>

    <h2>File Size Limits</h2>
    <ul>
        <li><strong>Maximum file size:</strong> 16MB per file</li>
        <li><strong>Recommended:</strong> Keep files under 5MB for faster processing</li>
        <li><strong>Optimal duration:</strong> 30 seconds to 2 minutes</li>
    </ul>

    <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; color: #666;">
        <p>Voice Sentiment Analysis API - Powered by Wav2Vec 2.0 + BERT</p>
    </footer>
</body>
</html>
"""

@app.route('/docs', methods=['GET'])
@app.route('/documentation', methods=['GET'])
@app.route('/', methods=['GET'])
def api_documentation():
    """API Documentation page"""
    base_url = request.url_root.rstrip('/')
    return render_template_string(API_DOCS_HTML, base_url=base_url)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Voice Sentiment Analysis API",
        "version": "1.0.0"
    })

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    """
    Analyze a single audio file
    
    Expected: multipart/form-data with 'audio' file
    Returns: JSON with analysis results
    """
    try:
        # Check if file is present
        if 'audio' not in request.files:
            return jsonify({
                "error": "No audio file provided",
                "message": "Please upload an audio file using the 'audio' field"
            }), 400
        
        audio_file = request.files['audio']
        
        # Check if file is selected
        if audio_file.filename == '':
            return jsonify({
                "error": "No file selected",
                "message": "Please select an audio file"
            }), 400
        
        # Validate file extension
        allowed_extensions = ['.wav', '.mp3', '.m4a', '.flac']
        file_ext = os.path.splitext(audio_file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({
                "error": "Unsupported file format",
                "message": f"Supported formats: {', '.join(allowed_extensions)}",
                "received": file_ext
            }), 400
        
        # Save file temporarily
        temp_id = str(uuid.uuid4())
        temp_filename = f"temp_audio_{temp_id}{file_ext}"
        temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
        
        audio_file.save(temp_path)
        
        try:
            # Analyze the audio
            analyzer = get_analyzer()
            result = analyzer.analyze_call(temp_path)
            
            # Clean up temporary file
            os.remove(temp_path)
            
            # Return results
            return jsonify({
                "success": True,
                "data": {
                    "filename": audio_file.filename,
                    "transcription": result['transcription'],
                    "sentiment": result['sentiment'],
                    "confidence_score": round(result['score'], 3),
                    "satisfaction": result['satisfaction']
                },
                "processing_id": temp_id
            })
        
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
            
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return jsonify({
            "error": "Processing failed",
            "message": str(e)
        }), 500

@app.route('/analyze/batch', methods=['POST'])
def analyze_batch():
    """
    Analyze multiple audio files
    
    Expected: multipart/form-data with multiple 'audio' files
    Returns: JSON with batch analysis results
    """
    try:
        # Check if files are present
        if 'audio' not in request.files:
            return jsonify({
                "error": "No audio files provided",
                "message": "Please upload audio files using the 'audio' field"
            }), 400
        
        audio_files = request.files.getlist('audio')
        
        if not audio_files or all(f.filename == '' for f in audio_files):
            return jsonify({
                "error": "No files selected",
                "message": "Please select audio files"
            }), 400
        
        results = []
        temp_files = []
        batch_id = str(uuid.uuid4())
        
        try:
            # Process each file
            for i, audio_file in enumerate(audio_files):
                if audio_file.filename == '':
                    continue
                
                # Validate file extension
                allowed_extensions = ['.wav', '.mp3', '.m4a', '.flac']
                file_ext = os.path.splitext(audio_file.filename)[1].lower()
                
                if file_ext not in allowed_extensions:
                    results.append({
                        "filename": audio_file.filename,
                        "error": f"Unsupported format: {file_ext}",
                        "success": False
                    })
                    continue
                
                # Save file temporarily
                temp_filename = f"batch_{batch_id}_{i}{file_ext}"
                temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
                temp_files.append(temp_path)
                
                audio_file.save(temp_path)
                
                # Analyze the audio
                analyzer = get_analyzer()
                result = analyzer.analyze_call(temp_path)
                
                results.append({
                    "filename": audio_file.filename,
                    "transcription": result['transcription'],
                    "sentiment": result['sentiment'],
                    "confidence_score": round(result['score'], 3),
                    "satisfaction": result['satisfaction'],
                    "success": True
                })
            
            # Calculate statistics
            successful_results = [r for r in results if r.get('success', False)]
            total_files = len(successful_results)
            
            if total_files > 0:
                sentiment_counts = {}
                satisfaction_counts = {}
                
                for result in successful_results:
                    sentiment = result['sentiment']
                    satisfaction = result['satisfaction']
                    
                    sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
                    satisfaction_counts[satisfaction] = satisfaction_counts.get(satisfaction, 0) + 1
                
                statistics = {
                    "total_files": total_files,
                    "sentiment_distribution": {
                        k: {"count": v, "percentage": round(v/total_files*100, 1)} 
                        for k, v in sentiment_counts.items()
                    },
                    "satisfaction_distribution": {
                        k: {"count": v, "percentage": round(v/total_files*100, 1)} 
                        for k, v in satisfaction_counts.items()
                    }
                }
            else:
                statistics = {"total_files": 0, "message": "No files processed successfully"}
            
            return jsonify({
                "success": True,
                "batch_id": batch_id,
                "statistics": statistics,
                "results": results,
                "processed_files": len(successful_results),
                "total_uploaded": len([f for f in audio_files if f.filename != ''])
            })
        
        finally:
            # Clean up temporary files
            for temp_path in temp_files:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        return jsonify({
            "error": "Batch processing failed",
            "message": str(e)
        }), 500

@app.route('/models/info', methods=['GET'])
def model_info():
    """Get information about loaded models"""
    return jsonify({
        "speech_recognition": {
            "model": "facebook/wav2vec2-large-960h-lv60-self",
            "type": "Wav2Vec 2.0",
            "language": "English",
            "description": "Large Wav2Vec 2.0 model for English speech recognition"
        },
        "sentiment_analysis": {
            "model": "nlptown/bert-base-multilingual-uncased-sentiment",
            "type": "BERT",
            "language": "Multilingual",
            "description": "Multilingual BERT for sentiment analysis (1-5 stars)"
        },
        "supported_formats": [".wav", ".mp3", ".m4a", ".flac"],
        "classifications": {
            "sentiments": ["POSITIVE", "NEGATIVE", "NEUTRAL"],
            "satisfaction": ["Satisfied", "Dissatisfied", "Neutral"]
        }
    })

@app.errorhandler(413)
def file_too_large(error):
    """Handle file too large error"""
    return jsonify({
        "error": "File too large",
        "message": "Audio file exceeds maximum size limit"
    }), 413

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist",
        "available_endpoints": [
            "GET /health - Health check",
            "POST /analyze - Analyze single audio file",
            "POST /analyze/batch - Analyze multiple audio files",
            "GET /models/info - Get model information"
        ]
    }), 404

if __name__ == '__main__':
    # Configuration
    HOST = os.getenv('API_HOST', '0.0.0.0')
    PORT = int(os.getenv('API_PORT', 8000))
    DEBUG = os.getenv('API_DEBUG', 'False').lower() == 'true'
    
    # Set maximum file size (16MB)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    print(f"Starting Voice Sentiment Analysis API...")
    print(f"Server: http://{HOST}:{PORT}")
    print(f"Health check: http://{HOST}:{PORT}/health")
    print(f"Documentation: See README for API usage examples")
    
    app.run(host=HOST, port=PORT, debug=DEBUG)