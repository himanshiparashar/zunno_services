#!/usr/bin/env python3
"""
Flask application for RFQ Data Extraction Service.
Provides a single endpoint for extracting RFQ data from PDF, DOC, and TXT files.
"""

from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import tempfile
from services.aksum_services import extract_aksum_data_from_RFQ

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'txt'}
# Register both blueprints
# app.register_blueprint(aksum_blueprint, url_prefix="/aksum")
# app.register_blueprint(jd_blueprint, url_prefix="/jd")

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def cleanup_temp_file(file_path):
    """Clean up temporary file."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        app.logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

@app.route('/', methods=['GET'])
def index():
    """Serve the upload form."""
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_rfq():
    """
    Extract RFQ data from uploaded file.
    
    Expected: multipart/form-data with 'file' field
    Returns: JSON with extracted RFQ data
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                "error": "No file provided",
                "message": "Please upload a file using the 'file' field"
            }), 400
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({
                "error": "No file selected",
                "message": "Please select a file to upload"
            }), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({
                "error": "Unsupported file format",
                "message": f"Supported formats: {', '.join(app.config['ALLOWED_EXTENSIONS'])}"
            }), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(temp_path)
            
            # Extract RFQ data
            result = extract_aksum_data_from_RFQ(temp_path)
            
            # Clean up temp file
            cleanup_temp_file(temp_path)
            
            # Return the result
            return jsonify(result)
            
        except Exception as e:
            # Clean up temp file on error
            cleanup_temp_file(temp_path)
            raise e
            
    except Exception as e:
        app.logger.error(f"Error in extract_rfq: {str(e)}")
        return jsonify({
            "error": "Extraction failed",
            "message": str(e),
            "processing_status": "error"
        }), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    return jsonify({
        "error": "File too large",
        "message": f"Maximum file size is {app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)}MB"
    }), 413

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        "error": "Not found",
        "message": "The requested endpoint does not exist"
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

if __name__ == '__main__':
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True
    )
