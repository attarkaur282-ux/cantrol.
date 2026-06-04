from flask import Flask, request, jsonify, send_file
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
REQUIRED_API_KEY = "@satvir123"
OWNER = "@notxsatvir"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return jsonify({
        "api": "Image to URL API",
        "owner": OWNER,
        "status": "running",
        "api_key_required": REQUIRED_API_KEY
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "owner": OWNER})

@app.route('/upload', methods=['POST'])
def upload_image():
    # Check API Key
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    
    if not api_key or api_key != REQUIRED_API_KEY:
        return jsonify({"error": "Invalid API Key", "required": REQUIRED_API_KEY}), 401
    
    if 'image' not in request.files:
        return jsonify({"error": "No image file"}), 400
    
    file = request.files['image']
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400
    
    filename = f"{uuid.uuid4().hex}.{file.filename.rsplit('.', 1)[1].lower()}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    image_url = f"{request.host_url.rstrip('/')}/image/{filename}"
    
    return jsonify({
        "success": True,
        "owner": OWNER,
        "filename": filename,
        "url": image_url,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/image/<filename>')
def get_image(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Not found"}), 404
    return send_file(filepath)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
