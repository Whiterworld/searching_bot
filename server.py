import os
import uuid
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from PIL import Image

UPLOAD_DIR = Path("/tmp/uploads")
OUTPUT_DIR = Path("/tmp/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_PDF = {"pdf"}
ALLOWED_DOCX = {"docx"}
ALLOWED_IMAGES = {"png", "jpg", "jpeg", "bmp", "tiff", "webp"}

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://ptwtp.netlify.app"}})  # Allow all for testing


def save_upload(file_storage, subdir):
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower()
    out_dir = UPLOAD_DIR / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    saved_path = out_dir / f"{uuid.uuid4().hex}_{filename}"
    file_storage.save(saved_path)
    return saved_path, ext


def make_download_response(filepath: Path, download_name: str, mimetype: str):
    response = make_response(send_file(filepath, as_attachment=True, download_name=download_name))
    response.headers["Content-Type"] = mimetype
    response.headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return response


@app.route("/")
def index():
    return {"message": "✅ Flask File Converter Running"}


@app.route("/convert/pdf-to-docx", methods=["POST"])
def pdf_to_docx():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    saved, ext = save_upload(file, "pdf_to_docx")
    if ext not in ALLOWED_PDF:
        return jsonify({"error": "Only PDF files allowed"}), 400

    output = OUTPUT_DIR / f"{Path(file.filename).stem}.docx"
    try:
        cv = Converter(str(saved))
        cv.convert(str(output))
        cv.close()
    except Exception as e:
        return jsonify({"error": f"Conversion failed: {e}"}), 500

    return make_download_response(output, f"{Path(file.filename).stem}.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.route("/convert/docx-to-pdf", methods=["POST"])
def docx_to_pdf():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    saved, ext = save_upload(file, "docx_to_pdf")
    if ext not in ALLOWED_DOCX:
        return jsonify({"error": "Only DOCX files allowed"}), 400

    out_dir = OUTPUT_DIR / "docx_to_pdf"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{saved.stem}.pdf"

    try:
        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(saved)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=True
        )
        print(result.stdout.decode(), result.stderr.decode())
    except subprocess.CalledProcessError as e:
        print("LibreOffice Error:", e.stderr.decode())
        return jsonify({"error": f"Conversion failed. LibreOffice issue: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Conversion failed: {e}"}), 500

    if not output.exists():
        return jsonify({"error": "Conversion failed: no output PDF created"}), 500

    return make_download_response(output, f"{Path(file.filename).stem}.pdf", "application/pdf")


@app.route("/convert/images-to-pdf", methods=["POST"])
def images_to_pdf():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No images uploaded"}), 400

    images = []
    try:
        for f in files:
            saved, ext = save_upload(f, "images_to_pdf")
            if ext not in ALLOWED_IMAGES:
                raise ValueError(f"Unsupported image: {f.filename}")
            img = Image.open(saved).convert("RGB")
            images.append(img)

        out_pdf = OUTPUT_DIR / f"{uuid.uuid4().hex}_images.pdf"
        images[0].save(out_pdf, save_all=True, append_images=images[1:])
    except Exception as e:
        return jsonify({"error": f"Images → PDF failed: {e}"}), 500
    finally:
        for im in images:
            try:
                im.close()
            except Exception:
                pass

    return make_download_response(out_pdf, "images_converted.pdf", "application/pdf")


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
