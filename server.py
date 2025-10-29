from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pdf2docx import Converter
from docx import Document
from fpdf import FPDF
from pymongo import MongoClient
import tempfile
import os
import io
from datetime import datetime, timezone

app = Flask(_name_)
CORS(app)  # Allow cross-origin requests (React frontend)

# ----------------- MongoDB Setup -----------------
MONGO_URI = "mongodb+srv://admin:admin123@cluster0.uhfubqa.mongodb.net/Whiter"
client = MongoClient(MONGO_URI)
db = client["pdf_converter"]
logs = db["conversion_logs"]

# ----------------- PDF → Word -----------------
@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    pdf_file = request.files['file']

    with tempfile.TemporaryDirectory() as tmpdir:
        input_pdf = os.path.join(tmpdir, 'input.pdf')
        output_docx = os.path.join(tmpdir, 'output.docx')
        pdf_file.save(input_pdf)

        # Convert PDF to Word
        cv = Converter(input_pdf)
        cv.convert(output_docx)
        cv.close()

        # ✅ Read into memory BEFORE temp folder closes
        with open(output_docx, "rb") as f:
            docx_data = f.read()

    # Log to MongoDB
    logs.insert_one({
        "type": "pdf_to_word",
        "filename": pdf_file.filename,
        "timestamp": datetime.now(timezone.utc)
    })

    # ✅ Return file safely from memory
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

    with tempfile.TemporaryDirectory() as tmpdir:
        input_docx = os.path.join(tmpdir, 'input.docx')
        output_pdf = os.path.join(tmpdir, 'output.pdf')
        word_file.save(input_docx)

        # Convert Word to PDF (basic text only)
        doc = Document(input_docx)
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for para in doc.paragraphs:
            pdf.multi_cell(0, 10, para.text)
        pdf.output(output_pdf)

        # ✅ Read into memory before deleting temp dir
        with open(output_pdf, "rb") as f:
            pdf_data = f.read()

    # Log to MongoDB
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


# ----------------- Health Check -----------------
@app.route('/')
def home():
    return jsonify({"message": "Flask API is running"})


# ----------------- Run Server -----------------
if _name_ == '_main_':
    app.run(host='0.0.0.0', port=8000)
