# backend/server.py
import os
import secrets
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
from utils import get_file_blocks, prg

# --- Server Setup ---
app = Flask(__name__)
# Enable CORS for all routes, allowing requests from our React frontend
CORS(app) 
SERVER_STORAGE_PATH = "server_storage/"

# This dictionary still acts as our simple database
file_db = {} 

if not os.path.exists(SERVER_STORAGE_PATH):
    os.makedirs(SERVER_STORAGE_PATH)

# --- The core logic functions remain the same as before ---
def generate_server_proof(filepath, seed):
    blocks = list(get_file_blocks(filepath))
    if len(blocks) < 2: return None
    para1 = hashlib.sha256(blocks[0] + prg(seed, 1)).digest()
    para2 = hashlib.sha256(blocks[1] + prg(seed, 2)).digest()
    resp = hashlib.sha256(para1 + para2).digest()
    for i in range(2, len(blocks)):
        block_hash = hashlib.sha256(blocks[i] + prg(seed, i + 1)).digest()
        resp = hashlib.sha256(resp + block_hash).digest()
    return resp.hex()

# --- API Endpoints ---
@app.route('/check-file', methods=['POST'])
def handle_upload_check():
    """Endpoint for the initial deduplication check."""
    data = request.json
    file_tag = data.get('tag')
    
    if not file_tag:
        return jsonify({"status": "error", "message": "File tag missing."}), 400

    if file_tag in file_db:
        seed = secrets.token_hex(16)
        file_db[file_tag + '_seed'] = seed 
        print(f"File exists. Sending seed: {seed}")
        return jsonify({"status": "exists", "seed": seed})
    else:
        print("File is new. Requesting upload.")
        return jsonify({"status": "new"})

@app.route('/upload-file', methods=['POST'])
def upload_full_file():
    """Endpoint to receive a new file for storage."""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part."}), 400
        
    file = request.files['file']
    tag = request.form.get('tag')
    
    if file.filename == '' or not tag:
        return jsonify({"status": "error", "message": "Invalid request."}), 400

    filepath = os.path.join(SERVER_STORAGE_PATH, file.filename)
    file.save(filepath)
    file_db[tag] = filepath
    print(f"✅ File '{file.filename}' saved. DB updated.")
    return jsonify({"status": "uploaded", "filename": file.filename})

@app.route('/verify', methods=['POST'])
def verify_ownership():
    """Endpoint to verify the user's generated proof."""
    data = request.json
    tag = data.get('tag')
    user_proof = data.get('proof')
    
    filepath = file_db.get(tag)
    seed = file_db.get(tag + '_seed')
    
    if not filepath or not seed:
        return jsonify({"status": "error", "message": "Verification failed."}), 404

    server_proof = generate_server_proof(filepath, seed)
    del file_db[tag + '_seed']

    if user_proof == server_proof:
        print(f"✅ Ownership VERIFIED for tag: {tag[:10]}...")
        return jsonify({"status": "verified"})
    else:
        print(f"❌ Ownership FAILED for tag: {tag[:10]}...")
        return jsonify({"status": "failed"}), 403

if __name__ == '__main__':
    app.run(port=5000, debug=True)