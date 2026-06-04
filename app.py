from flask import Flask, request, jsonify, send_file
import os
import uuid
import requests
from datetime import datetime
import base64
import re
import hashlib
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)

# ========== CONFIGURATION ==========
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'ico'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
BASE_URL = os.environ.get('BASE_URL', 'https://your-domain.vercel.app')

# ========== API KEY ==========
REQUIRED_API_KEY = "@satvir123"  # <-- API Key fixed

# ========== OWNER INFO ==========
OWNER = "@notxsatvir"
API_VERSION = "2.0.0"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========== API KEY DECORATOR ==========
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check header first
        api_key = request.headers.get('X-API-Key')
        
        # Then check query parameter
        if not api_key:
            api_key = request.args.get('api_key')
        
        # Then check JSON body
        if not api_key and request.is_json:
            data = request.get_json()
            api_key = data.get('api_key') if data else None
        
        # Validate API Key
        if not api_key or api_key != REQUIRED_API_KEY:
            return jsonify({
                "success": False,
                "error": "Invalid or missing API Key",
                "message": "Please provide valid API key",
                "required_api_key": REQUIRED_API_KEY,
                "owner": OWNER
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

# ========== HELPER FUNCTIONS ==========
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file):
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return filename, filepath

def save_base64_image(base64_string):
    # Remove data URL prefix if present
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    
    image_data = base64.b64decode(base64_string)
    ext = 'png'  # default
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    with open(filepath, 'wb') as f:
        f.write(image_data)
    
    return filename, filepath

# ========== ROUTES ==========
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "api": "Image to URL API",
        "owner": OWNER,
        "version": API_VERSION,
        "status": "running",
        "authentication": {
            "required": True,
            "method": "X-API-Key header or ?api_key= parameter",
            "api_key": REQUIRED_API_KEY
        },
        "endpoints": {
            "GET /": "API Information",
            "GET /health": "Health Check (no auth)",
            "POST /upload": "Upload image and get URL",
            "POST /upload/base64": "Upload base64 image",
            "GET /image/{filename}": "View uploaded image (public)",
            "DELETE /delete/{filename}": "Delete image",
            "GET /stats": "Upload statistics"
        },
        "usage": {
            "curl": f"curl -X POST -H 'X-API-Key: {REQUIRED_API_KEY}' -F 'image=@photo.jpg' https://your-api.vercel.app/upload",
            "python": f"requests.post('https://your-api.vercel.app/upload', headers={{'X-API-Key': '{REQUIRED_API_KEY}'}}, files={{'image': open('photo.jpg', 'rb')}})"
        },
        "limits": {
            "max_size": f"{MAX_FILE_SIZE // 1024 // 1024}MB",
            "allowed_formats": list(ALLOWED_EXTENSIONS)
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "owner": OWNER,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/upload', methods=['POST'])
@require_api_key
def upload_image():
    """Upload image and get URL"""
    
    if 'image' not in request.files:
        return jsonify({
            "success": False,
            "error": "No image file provided",
            "usage": "Send file with key 'image'",
            "owner": OWNER
        }), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({
            "success": False,
            "error": "No file selected",
            "owner": OWNER
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            "owner": OWNER
        }), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_FILE_SIZE:
        return jsonify({
            "success": False,
            "error": f"File too large. Max {MAX_FILE_SIZE // 1024 // 1024}MB",
            "owner": OWNER
        }), 400
    
    try:
        filename, filepath = save_image(file)
        file_size = os.path.getsize(filepath)
        
        # Generate public URL
        image_url = f"{request.host_url.rstrip('/')}/image/{filename}"
        
        return jsonify({
            "success": True,
            "owner": OWNER,
            "filename": filename,
            "url": image_url,
            "size": f"{file_size / 1024:.2f} KB",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "owner": OWNER
        }), 500

@app.route('/upload/base64', methods=['POST'])
@require_api_key
def upload_base64():
    """Upload base64 encoded image"""
    
    data = request.get_json()
    
    if not data or 'image' not in data:
        return jsonify({
            "success": False,
            "error": "No base64 image provided",
            "usage": {"image": "base64_string"},
            "owner": OWNER
        }), 400
    
    base64_string = data['image']
    
    try:
        filename, filepath = save_base64_image(base64_string)
        file_size = os.path.getsize(filepath)
        
        image_url = f"{request.host_url.rstrip('/')}/image/{filename}"
        
        return jsonify({
            "success": True,
            "owner": OWNER,
            "filename": filename,
            "url": image_url,
            "size": f"{file_size / 1024:.2f} KB",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Invalid base64 image: {str(e)}",
            "owner": OWNER
        }), 400

@app.route('/image/<filename>', methods=['GET'])
def get_image(filename):
    """Get uploaded image (public - no auth needed)"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({
            "success": False,
            "error": "Image not found",
            "owner": OWNER
        }), 404
    
    return send_file(filepath, mimetype='image/png')

@app.route('/delete/<filename>', methods=['DELETE'])
@require_api_key
def delete_image(filename):
    """Delete uploaded image"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({
            "success": False,
            "error": "Image not found",
            "owner": OWNER
        }), 404
    
    os.remove(filepath)
    
    return jsonify({
        "success": True,
        "message": f"Image {filename} deleted successfully",
        "owner": OWNER,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Get upload statistics"""
    files = os.listdir(UPLOAD_FOLDER)
    total_size = sum(os.path.getsize(os.path.join(UPLOAD_FOLDER, f)) for f in files)
    
    return jsonify({
        "success": True,
        "owner": OWNER,
        "stats": {
            "total_files": len(files),
            "total_size_mb": f"{total_size / 1024 / 1024:.2f} MB",
            "allowed_formats": list(ALLOWED_EXTENSIONS),
            "max_file_size_mb": MAX_FILE_SIZE // 1024 // 1024
        },
        "timestamp": datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/health", "/upload", "/upload/base64", "/image/{filename}", "/delete/{filename}", "/stats"],
        "owner": OWNER
    }), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
