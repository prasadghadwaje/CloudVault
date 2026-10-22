
import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from file_security import decrypt_reassemble

BUCKET_NAME = "cloudvault-prasad-2026-demo-01"
AWS_REGION = "ap-south-1"

s3 = boto3.client("s3", region_name=AWS_REGION)

DOWNLOAD_DIR = Path("downloads")
BLOCK_DIR = Path("encrypted_blocks")


def download_and_restore(upload_id):
    prefix = f"encrypted-uploads/{upload_id}/"
    manifest_key = prefix + "manifest.json"

    DOWNLOAD_DIR.mkdir(exist_ok=True)
    BLOCK_DIR.mkdir(exist_ok=True)

    local_manifest = DOWNLOAD_DIR / f"{upload_id}.manifest.json"

    # Download the manifest from the private S3 bucket.
    s3.download_file(
        BUCKET_NAME,
        manifest_key,
        str(local_manifest)
    )

    manifest = json.loads(local_manifest.read_text(encoding="utf-8"))

    # Download every encrypted block and save it for reconstruction.
    for block in manifest["blocks"]:
        key = block["s3_key"]
        filename = Path(block["filename"]).name
        local_block = BLOCK_DIR / filename

        s3.download_file(
            BUCKET_NAME,
            key,
            str(local_block)
        )

        print(f"Downloaded: {filename}")

    # Create a local manifest in the format expected by file_security.py.
    local_format_manifest = BLOCK_DIR / f"{upload_id}.manifest.json"

    local_manifest_data = {
        "original_filename": manifest["original_filename"],
        "original_sha256": manifest["original_sha256"],
        "block_size": manifest["block_size"],
        "blocks": manifest["blocks"]
    }

    local_format_manifest.write_text(
        json.dumps(local_manifest_data, indent=2),
        encoding="utf-8"
    )

    # Recover the original file. The original key must still be available.
    output_path = DOWNLOAD_DIR / (
        "recovered_" + Path(manifest["original_filename"]).name
    )

    result = decrypt_reassemble(
        local_format_manifest,
        output_path
    )

    print("\nSUCCESS: File restored and integrity verified.")
    print(f"Recovered file: {result.resolve()}")

    return result


if __name__ == "__main__":
    upload_id = input("Enter the S3 Upload ID: ").strip()

    if not upload_id or "/" in upload_id or "\\" in upload_id or ".." in upload_id:
        raise ValueError("Invalid upload ID.")

    try:
        download_and_restore(upload_id)
    except (ClientError, OSError, ValueError, KeyError) as error:
        print(f"Download or restoration failed: {error}")
