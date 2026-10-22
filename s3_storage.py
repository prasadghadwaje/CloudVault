
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = "cloudvault-prasad-2026-demo-01"
AWS_REGION = "ap-south-1"

s3 = boto3.client("s3", region_name=AWS_REGION)


def upload_encrypted_file(manifest_path):
    """Upload encrypted blocks and their manifest to private S3 storage."""

    manifest_path = Path(manifest_path).resolve()
    block_dir = manifest_path.parent

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    # A unique prefix prevents overwriting files from previous uploads.
    import uuid
    upload_id = uuid.uuid4().hex
    prefix = f"encrypted-uploads/{upload_id}/"

    import json
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    uploaded_keys = []

    try:
        for block in manifest["blocks"]:
            filename = Path(block["filename"]).name
            block_path = (block_dir / filename).resolve()

            # Only allow block files located directly beside the manifest.
            if block_path.parent != block_dir or not block_path.is_file():
                raise ValueError(f"Invalid or missing block: {filename}")

            key = prefix + filename

            s3.upload_file(
                str(block_path),
                BUCKET_NAME,
                key,
                ExtraArgs={"ContentType": "application/octet-stream"}
            )
            uploaded_keys.append(key)
            print(f"Uploaded encrypted block: {key}")

        # Store a cloud manifest containing the uploaded block locations.
        cloud_manifest = dict(manifest)
        cloud_manifest["upload_id"] = upload_id
        cloud_manifest["s3_prefix"] = prefix

        cloud_manifest["blocks"] = [
            {
                **block,
                "s3_key": prefix + Path(block["filename"]).name
            }
            for block in manifest["blocks"]
        ]

        local_cloud_manifest = manifest_path.with_name(
            f"{manifest_path.stem}.cloud.json"
        )
        local_cloud_manifest.write_text(
            json.dumps(cloud_manifest, indent=2),
            encoding="utf-8"
        )

        manifest_key = prefix + "manifest.json"
        s3.upload_file(
            str(local_cloud_manifest),
            BUCKET_NAME,
            manifest_key,
            ExtraArgs={"ContentType": "application/json"}
        )
        uploaded_keys.append(manifest_key)

        print("\nUpload successful!")
        print(f"Upload ID: {upload_id}")
        print(f"Manifest: s3://{BUCKET_NAME}/{manifest_key}")

        return cloud_manifest

    except (ClientError, OSError, ValueError, KeyError):
        # Remove only objects created by this attempt.
        for key in uploaded_keys:
            try:
                s3.delete_object(Bucket=BUCKET_NAME, Key=key)
            except ClientError:
                print(f"Cleanup failed for: {key}")
        raise


if __name__ == "__main__":
    manifest_file = Path(
        "encrypted_blocks/sample.txt.manifest.json"
    )

    try:
        upload_encrypted_file(manifest_file)
    except Exception as error:
        print(f"Upload failed: {error}")
