from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pdf2docx import Converter
from docx2pdf import convert
from pymongo import MongoClient
from PIL import Image
import tempfile
import os
import io
from datetime import datetime, timezone
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://ptwtp.netlify.app"]}})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Setup (use environment variables in production!)
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://admin:admin123@cluster0.uhfubqa.mongodb.net/Whiter")
client = MongoClient(MONGO_URI)
db = client["pdf_converter"]
logs = db["conversion_logs"]

@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    pdf_file = request.files['file']
    if not pdf_file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        input_pdf = os.path.join(tmpdir, 'input.pdf')
        output_docx = os.path.join(tmpdir, 'output.docx')
        pdf_file.save(input_pdf)
        try:
            cv = Converter(input_pdf)
            cv.convert(output_docx, start=0, end=None)
            cv.close()
            with open(output_docx, "rb") as f:
                docx_data = f.read()
            logs.insert_one({
                "type": "pdf_to_word",
                "filename": pdf_file.filename,
                "timestamp": datetime.now(timezone.utc)
            })
            return send_file(
                io.BytesIO(docx_data),
                as_attachment=True,
                download_name="converted.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            logger.error(f"PDF to Word conversion failed: {str(e)}")
            return jsonify({'error': f'PDF to Word conversion failed: {str(e)}'}), 500

@app.route('/word-to-pdf', methods=['POST'])
def word_to_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    word_file = request.files['file']
    if not word_file.filename.endswith(('.docx', '.doc')):
        return jsonify({'error': 'Only Word files are allowed'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        input_docx = os.path.join(tmpdir, 'input.docx')
        output_pdf = os.path.join(tmpdir, 'output.pdf')
        word_file.save(input_docx)
        try:
            convert(input_docx, output_pdf)
            with open(output_pdf, "rb") as f:
                pdf_data = f.read()
            logs.insert_one({
                "type": "word_to_pdf",
                "filename": word_file.filename,
                "timestamp": datetime.now(timezone.utc)
            })
            return send_file(
                io.BytesIO(pdf_data),
                as_attachment=True,
                download_name="converted.pdf",
                mimetype="application/pdf"
            )
        except Exception as e:
            logger.error(f"Word to PDF conversion failed: {str(e)}")
            return jsonify({'error': f'Word to PDF conversion failed: {str(e)}'}), 500

@app.route('/image-to-pdf', methods=['POST'])
def image_to_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    img_file = request.files['file']
    if not img_file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        return jsonify({'error': 'Only PNG, JPG, or JPEG images are allowed'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        input_img = os.path.join(tmpdir, 'input_image')
        output_pdf = os.path.join(tmpdir, 'output.pdf')
        img_file.save(input_img)
        try:
            img = Image.open(input_img)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(output_pdf, "PDF")
            with open(output_pdf, "rb") as f:
                pdf_data = f.read()
            logs.insert_one({
                "type": "image_to_pdf",
                "filename": img_file.filename,
                "timestamp": datetime.now(timezone.utc)
            })
            return send_file(
                io.BytesIO(pdf_data),
                as_attachment=True,
                download_name="converted.pdf",
                mimetype="application/pdf"
            )
        except Exception as e:
            logger.error(f"Image to PDF conversion failed: {str(e)}")
            return jsonify({'error': f'Image to PDF conversion failed: {str(e)}'}), 500

@app.route('/')
def home():
    return jsonify({"message": "Flask API is running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
