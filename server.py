from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pdf2docx import Converter
from docx import Document
from fpdf import FPDF
from pymongo import MongoClient
from PIL import Image
import tempfile
import os
import io
from datetime import datetime, timezone
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://ptwtp.netlify.app/"]}})

# ----------------- Configuration -----------------
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# ----------------- MongoDB Setup -----------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://admin:admin123@cluster0.uhfubqa.mongodb.net/Whiter")
client = MongoClient(MONGO_URI)
db = client["pdf_converter"]
logs = db["conversion_logs"]

# ----------------- PDF → Word -----------------
@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    pdf_file = request.files['file']
    if pdf_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        input_pdf = os.path.join(tmpdir, 'input.pdf')
        output_docx = os.path.join(tmpdir, 'output.docx')
        pdf_file.save(input_pdf)

        try:
            cv = Converter(input_pdf)
            cv.convert(output_docx)
            cv.close()
        except Exception as e:
            return jsonify({'error': f'PDF → Word conversion failed: {str(e)}'}), 500

        with open(output_docx, "rb") as f:
            docx_data = f.read()

        try:
            logs.insert_one({
                "type": "pdf_to_word",
                "filename": pdf_file.filename,
                "timestamp": datetime.now(timezone.utc)
            })
        except Exception as e:
            print(f"Failed to log: {e}")

        return send_file(
            io.BytesIO(docx_data),
            as_attachment=True,
            download_name="converted.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# ----------------- Word → PDF -----------------
@app.route('/word-to-pdf', methods=['POST'])
def word_to_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    word_file = request.files['file']
    if word_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        input_docx = os.path.join(tmpdir, 'input.docx')
        output_pdf = os.path.join(tmpdir, 'output.pdf')
        word_file.save(input_docx)

        try:
            doc = Document(input_docx)
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for para in doc.paragraphs:
                pdf.multi_cell(0, 10, para.text)
            pdf.output(output_pdf)
        except Exception as e:
            return jsonify({'error': f'Word → PDF conversion failed: {str(e)}'}), 500

        with open(output_pdf, "rb") as f:
            pdf_data = f.read()

        try:
            logs.insert_one({
                "type": "word_to_pdf",
                "filename": word_file.filename,
                "timestamp": datetime.now(timezone.utc)
            })
        except Exception as e:
            print(f"Failed to log: {e}")

        return send_file(
            io.BytesIO(pdf_data),
            as_attachment=True,
            download_name="converted.pdf",
            mimetype="application/pdf"
        )

# ----------------- Image → PDF -----------------
@app.route('/image-to-pdf', methods=['POST'])
def image_to_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    img_file = request.files['file']
    if img_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        ext = os.path.splitext(img_file.filename)[1]
        input_img = os.path.join(tmpdir, f'input_image{ext}')
        output_pdf = os.path.join(tmpdir, 'output.pdf')
        img_file.save(input_img)

        try:
            with Image.open(input_img) as img:
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                img.save(output_pdf, "PDF", resolution=100.0)
        except Exception as e:
            return jsonify({'error': f'Image → PDF conversion failed: {str(e)}'}), 500

        with open(output_pdf, "rb") as f:
            pdf_data = f.read()

        try:
            logs.insert_one({
                "type": "image_to_pdf",
                "filename": img_file.filename,
                "timestamp": datetime.now(timezone.utc)
            })
        except Exception as e:
            print(f"Failed to log: {e}")

        return send_file(
            io.BytesIO(pdf_data),
            as_attachment=True,
            download_name="converted.pdf",
            mimetype="application/pdf"
        )

# ----------------- Health Check -----------------
@app.route('/')
def home():
    return jsonify({"message": "Flask API is running"})

# ----------------- Run Server -----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
