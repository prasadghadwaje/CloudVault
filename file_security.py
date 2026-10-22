
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE_DIR = Path(__file__).resolve().parent
BLOCK_DIR = BASE_DIR / "encrypted_blocks"
KEY_DIR = BASE_DIR / "keys"
KEY_FILE = KEY_DIR / "cloudvault.key"

BLOCK_DIR.mkdir(exist_ok=True)
KEY_DIR.mkdir(exist_ok=True)


def load_or_create_key():
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()

    key = AESGCM.generate_key(bit_length=256)
    KEY_FILE.write_bytes(key)

    # Restrict permissions where supported.
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass

    return key


def split_encrypt_file(file_path, block_size=1024 * 1024):
    """Split a file into 1 MiB blocks and encrypt each block."""

    file_path = Path(file_path)
    key = load_or_create_key()
    aes = AESGCM(key)

    blocks = []
    original_hash = hashlib.sha256()
    index = 0

    with file_path.open("rb") as source:
        while True:
            plaintext = source.read(block_size)
            if not plaintext:
                break

            original_hash.update(plaintext)

            nonce = os.urandom(12)
            ciphertext = aes.encrypt(nonce, plaintext, None)

            block_name = f"{file_path.name}.block{index:04d}.bin"
            block_path = BLOCK_DIR / block_name
            block_path.write_bytes(nonce + ciphertext)

            blocks.append({
                "index": index,
                "filename": block_name,
                "size": len(ciphertext) + len(nonce)
            })
            index += 1

    manifest = {
        "original_filename": file_path.name,
        "original_sha256": original_hash.hexdigest(),
        "block_size": block_size,
        "blocks": blocks
    }

    manifest_path = BLOCK_DIR / f"{file_path.name}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return manifest


def decrypt_reassemble(manifest_path, output_path):
    """Decrypt blocks in order and reconstruct the original file."""

    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())

    key = load_or_create_key()
    aes = AESGCM(key)
    digest = hashlib.sha256()

    output_path = Path(output_path)

    with output_path.open("wb") as output:
        for block in manifest["blocks"]:
            block_path = BLOCK_DIR / block["filename"]
            encrypted = block_path.read_bytes()

            nonce = encrypted[:12]
            ciphertext = encrypted[12:]

            plaintext = aes.decrypt(nonce, ciphertext, None)
            output.write(plaintext)
            digest.update(plaintext)

    if digest.hexdigest() != manifest["original_sha256"]:
        output_path.unlink(missing_ok=True)
        raise ValueError("Integrity check failed: recovered file does not match.")

    return output_path
