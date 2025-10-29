import os
import uuid
import subprocess
from pathlib import Path
from flask import Flask, request, redirect, url_for, flash, render_template, send_file, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from PIL import Image

# Setup paths
UPLOAD_DIR = Path("/tmp/uploads")
OUTPUT_DIR = Path("/tmp/outputs")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_PDF = {"pdf"}
ALLOWED_DOCX = {"docx"}
ALLOWED_IMAGES = {"png", "jpg", "jpeg", "bmp", "tiff", "webp"}

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://ptwtp.netlify.app/"]}})

# ---------- Utility ----------

def save_upload(file_storage, subdir):
    """Save an uploaded file with a unique name."""
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower()
    out_dir = UPLOAD_DIR / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    saved_path = out_dir / f"{uuid.uuid4().hex}_{filename}"
    file_storage.save(saved_path)
    return saved_path, ext

def make_download_response(filepath: Path, download_name: str, mimetype: str):
    """Force correct file name and type in download response."""
    response = make_response(send_file(filepath, as_attachment=True))
    response.headers["Content-Type"] = mimetype
    response.headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return response

# ---------- Routes ----------

@app.route("/")
def index():
    return render_template("index.html")

# ---- PDF → DOCX ----
@app.route("/convert/pdf-to-docx", methods=["POST"])
def pdf_to_docx():
    file = request.files.get("file")
    if not file:
        flash("No file uploaded")
        return redirect(url_for("index"))
    saved, ext = save_upload(file, "pdf_to_docx")
    if ext not in ALLOWED_PDF:
        flash("Only PDF files allowed")
        return redirect(url_for("index"))

    output = OUTPUT_DIR / f"{Path(file.filename).stem}.docx"
    try:
        cv = Converter(str(saved))
        cv.convert(str(output))
        cv.close()
    except Exception as e:
        flash(f"Conversion failed: {e}")
        return redirect(url_for("index"))

    return make_download_response(
        output,
        download_name=f"{Path(file.filename).stem}.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# ---- DOCX → PDF ----
@app.route("/convert/docx-to-pdf", methods=["POST"])
def docx_to_pdf():
    file = request.files.get("file")
    if not file:
        flash("No file uploaded")
        return redirect(url_for("index"))
    saved, ext = save_upload(file, "docx_to_pdf")
    if ext not in ALLOWED_DOCX:
        flash("Only DOCX files allowed")
        return redirect(url_for("index"))

    out_dir = OUTPUT_DIR / "docx_to_pdf"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(saved)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
    except Exception as e:
        flash(f"Conversion failed: {e}")
        return redirect(url_for("index"))

    output = out_dir / f"{saved.stem}.pdf"
    if not output.exists():
        flash("Conversion failed: no output PDF created")
        return redirect(url_for("index"))

    return make_download_response(
        output,
        download_name=f"{Path(file.filename).stem}.pdf",
        mimetype="application/pdf"
    )

# ---- IMAGES → PDF ----
@app.route("/convert/images-to-pdf", methods=["POST"])
def images_to_pdf():
    files = request.files.getlist("files")
    if not files:
        flash("No images uploaded")
        return redirect(url_for("index"))

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
        flash(f"Images → PDF failed: {e}")
        return redirect(url_for("index"))
    finally:
        for im in images:
            try:
                im.close()
            except Exception:
                pass

    return make_download_response(
        out_pdf,
        download_name="images_converted.pdf",
        mimetype="application/pdf"
    )

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
