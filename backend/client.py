# client.py
import requests
import os
import hashlib
from backend.utils import get_file_tag, get_file_blocks, prg

SERVER_URL = "http://127.0.0.1:5000"

def generate_user_proof(filepath, seed):
    """
    Implements the user-side proof generation (User_RespGen from Algorithm 2).
    """
    blocks = list(get_file_blocks(filepath))
    if len(blocks) < 2:
        raise ValueError("File is too small for this proof scheme (must have at least two blocks).")

    # Lines 6-7 of Algorithm 2: Initialize parameters with the first two blocks
    para1 = hashlib.sha256(blocks[0] + prg(seed, 1)).digest()
    para2 = hashlib.sha256(blocks[1] + prg(seed, 2)).digest()
    
    # Line 8 of Algorithm 2: Compute the first intermediate hash
    resp = hashlib.sha256(para1 + para2).digest()
    
    # Lines 11-16 of Algorithm 2: Iterate through the remaining blocks to create a hash chain
    for i in range(2, len(blocks)):
        # Calculate the hash of the current block combined with the PRG output
        block_hash = hashlib.sha256(blocks[i] + prg(seed, i + 1)).digest()
        # Chain it with the previous response
        resp = hashlib.sha256(resp + block_hash).digest()
        
    return resp.hex()

def attempt_upload(filepath, user_name="User"):
    """Simulates a complete upload attempt for a given file."""
    if not os.path.exists(filepath):
        print(f"[{user_name}] ❌ Error: File '{filepath}' not found.")
        return

    print(f"[{user_name}] 🚀 Starting upload process for '{os.path.basename(filepath)}'...")
    
    # Step 1: Calculate the file tag (FTag) locally.
    file_tag = get_file_tag(filepath)
    print(f"[{user_name}] 1. Calculated File Tag: {file_tag[:10]}...")

    # Step 2: Contact the server to check if the tag exists.
    try:
        response = requests.post(f"{SERVER_URL}/upload", data={'tag': file_tag})
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"[{user_name}] ❌ Error connecting to server: {e}")
        return

    # Step 3: Handle the server's response.
    if data['status'] == 'new':
        print(f"[{user_name}] 2. Server says file is new. Uploading full file...")
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f)}
            upload_response = requests.post(
                f"{SERVER_URL}/upload-file",
                files=files,
                data={'tag': file_tag}
            )
        print(f"[{user_name}] 3. ✅ Upload complete: {upload_response.json()}")

    elif data['status'] == 'exists':
        print(f"[{user_name}] 2. Server says file exists. Starting Proof of Ownership...")
        seed = data['seed']
        print(f"[{user_name}]    - Received challenge seed: {seed}")
        
        # Generate the proof using the file and the server's seed.
        proof = generate_user_proof(filepath, seed)
        print(f"[{user_name}] 3. Generated Proof: {proof[:10]}...")

        # Send the proof back for verification.
        verify_response = requests.post(
            f"{SERVER_URL}/verify",
            json={'tag': file_tag, 'proof': proof}
        )
        result = verify_response.json()
        if result['status'] == 'verified':
            print(f"[{user_name}] 4. ✅ Ownership successfully verified!")
        else:
            print(f"[{user_name}] 4. ❌ Ownership verification failed!")
            
if __name__ == '__main__':
    # --- SIMULATION SETUP ---
    TEST_FILE = "my_large_test_file.txt"
    print("Setting up simulation file...")
    # Create a reasonably large dummy file to test with multiple blocks
    with open(TEST_FILE, "w") as f:
        f.write("This is the content of the test file that will be used for the deduplication simulation. " * 5000)
    print(f"'{TEST_FILE}' created.\n")
    
    # --- SIMULATION RUN ---
    # Scenario 1: The first user uploads the file.
    print("--- SCENARIO 1: Alice uploads the file for the first time ---")
    attempt_upload(TEST_FILE, user_name="Alice")
    
    print("\n" + "="*70 + "\n")
    
    # Scenario 2: A second user tries to upload the exact same file.
    print("--- SCENARIO 2: Bob uploads the same file (should trigger POW) ---")
    attempt_upload(TEST_FILE, user_name="Bob")