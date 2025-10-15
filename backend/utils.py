# utils.py
import hashlib

# Defines the size of each block to read from a file (e.g., 4KB)
BLOCK_SIZE = 4096 

def get_file_blocks(filepath):
    """
    Reads a file and yields its content in sequential blocks of BLOCK_SIZE.
    This is memory-efficient as it doesn't load the whole file at once.
    """
    with open(filepath, 'rb') as f:
        while True:
            block = f.read(BLOCK_SIZE)
            if not block:
                break
            yield block

def get_file_tag(filepath):
    """
    Calculates the SHA-256 hash of an entire file to create its unique tag (FTag).
    This corresponds to line 2 of Algorithm 1 in the paper.
    """
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(BLOCK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def prg(seed, index):
    """
    A simple but secure Pseudorandom Generator (PRG) using SHA-256.
    It combines the server's unique 'seed' with an 'index' to generate a
    deterministic but unpredictable value for each file block.
    """
    prg_hasher = hashlib.sha256()
    prg_hasher.update(seed.encode())
    prg_hasher.update(str(index).encode())
    return prg_hasher.digest()