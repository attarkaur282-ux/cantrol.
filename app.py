from flask import Flask, request, jsonify, send_file
import os
import uuid
import io
from datetime import datetime

app = Flask(__name__)

# ========== CONFIG ==========
REQUIRED_API_KEY = "@satvir123"
OWNER = "@notxsatvir"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

# Vercel serverless mein /tmp use karo (writeable)
UPLOAD_FOLDER = '/tmp/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return jsonify({
        "api": "Image to URL API",
        "owner": OWNER,
        "version": "1.0.0",
        "status": "running",
        "auth": {
            "required": True,
            "api_key": REQUIRED_API_KEY,
            "method": "X-API-Key header or ?api_key=query"
        },
        "endpoints": {
            "POST /upload": "Upload image (multipart/form-data)",
            "GET /image/{filename}": "View uploaded image",
            "GET /health": "Health check"
        },
        "example_curl": f"curl -X POST -H 'X-API-Key: {REQUIRED_API_KEY}' -F 'image=@photo.jpg' https://control-seven.vercel.app/upload"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "owner": OWNER,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        # Get API Key
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key or api_key != REQUIRED_API_KEY:
            return jsonify({
                "success": False,
                "error": "Invalid or missing API Key",
                "required": REQUIRED_API_KEY
            }), 401
        
        # Check if file exists
        if 'image' not in request.files:
            return jsonify({
                "success": False,
                "error": "No image file provided. Use key 'image'"
            }), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save file
        file.save(filepath)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Generate URL
        base_url = request.host_url.rstrip('/')
        image_url = f"{base_url}/image/{filename}"
        
        return jsonify({
            "success": True,
            "owner": OWNER,
            "filename": filename,
            "url": image_url,
            "size_kb": round(file_size / 1024, 2),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "owner": OWNER
        }), 500

@app.route('/image/<filename>')
def get_image(filename):
    try:
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                "success": False,
                "error": "Image not found"
            }), 404
        
        return send_file(filepath)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/health", "/upload", "/image/{filename}"]
    }), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
