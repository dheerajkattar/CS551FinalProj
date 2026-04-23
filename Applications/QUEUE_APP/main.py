from flask import Flask, request, jsonify
from celery import Celery
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

# Celery configuration
app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])
celery.conf.update(app.config)

# Import tasks after celery is initialized
from tasks import process_csv_etl

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('results', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload a CSV file to be processed by ETL pipeline
    Returns a job ID to track progress
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CSV files allowed'}), 400

    # Generate unique job ID
    job_id = str(uuid.uuid4())
    filename = secure_filename(f"{job_id}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Save uploaded file
    file.save(filepath)

    # Queue the ETL task
    task = process_csv_etl.delay(filepath, job_id)

    return jsonify({
        'message': 'File uploaded successfully',
        'job_id': job_id,
        'task_id': task.id,
        'filename': file.filename,
        'timestamp': datetime.now().isoformat()
    }), 202

@app.route('/status/<job_id>', methods=['GET'])
def check_status(job_id):
    """
    Check the status of an ETL job
    """
    result_file = os.path.join('results', f"{job_id}_result.json")

    if os.path.exists(result_file):
        with open(result_file, 'r') as f:
            import json
            result = json.load(f)
            return jsonify({
                'job_id': job_id,
                'status': 'completed',
                'result': result
            }), 200

    # Check if still processing
    error_file = os.path.join('results', f"{job_id}_error.json")
    if os.path.exists(error_file):
        with open(error_file, 'r') as f:
            import json
            error = json.load(f)
            return jsonify({
                'job_id': job_id,
                'status': 'failed',
                'error': error
            }), 400

    return jsonify({
        'job_id': job_id,
        'status': 'processing',
        'message': 'Job is still being processed'
    }), 202

@app.route('/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """
    Download the processed results CSV
    """
    output_file = os.path.join('results', f"{job_id}_output.csv")

    if not os.path.exists(output_file):
        return jsonify({'error': 'Results not found. Job may still be processing.'}), 404

    from flask import send_file
    return send_file(output_file, as_attachment=True, download_name=f"{job_id}_output.csv")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5002)
