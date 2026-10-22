
import os
import re
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from file_security import split_encrypt_file, decrypt_reassemble
from s3_storage import upload_encrypted_file
from s3_download import download_and_restore

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB limit

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DOWNLOAD_DIR = BASE_DIR / "downloads"

UPLOAD_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")

    if not file or not file.filename:
        return jsonify({"error": "Please select a file."}), 400

    filename = secure_filename(file.filename)

    if not filename:
        return jsonify({"error": "Invalid filename."}), 400

    upload_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{upload_id}_{filename}"

    try:
        file.save(input_path)

        manifest = split_encrypt_file(input_path)
        cloud_manifest = upload_encrypted_file(
            Path("encrypted_blocks") /
            f"{input_path.name}.manifest.json"
        )

        # Return only the identifier and basic status, not internal keys.
        return jsonify({
            "message": "File encrypted and uploaded successfully.",
            "upload_id": cloud_manifest["upload_id"],
            "filename": filename,
            "blocks": len(cloud_manifest["blocks"])
        }), 201

    except Exception:
        app.logger.exception("Upload failed")
        return jsonify({
            "error": "Upload failed. Check the server logs."
        }), 500

    finally:
        input_path.unlink(missing_ok=True)


@app.route("/api/download/<upload_id>", methods=["GET"])
def download_file(upload_id):
    if not re.fullmatch(r"[0-9a-f]{32}", upload_id):
        return jsonify({"error": "Invalid upload ID."}), 400

    try:
        recovered_path = download_and_restore(upload_id)

        # Serve the recovered file as an attachment.
        return send_file(
            recovered_path,
            as_attachment=True,
            download_name=recovered_path.name
        )

    except Exception:
        app.logger.exception("Download failed")
        return jsonify({
            "error": "Download failed. Check the server logs."
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
