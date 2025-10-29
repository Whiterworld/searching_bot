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

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://ptwtp.netlify.app/"]}})  # Allow frontend

# ----------------- MongoDB Setup -----------------
MONGO_URI = "mongodb+srv://admin:admin123@cluster0.uhfubqa.mongodb.net/Whiter"
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Force connection check
except Exception as e:
    print(f"MongoDB connection failed: {e}")
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

        try:
            cv = Converter(input_pdf)
            cv.convert(output_docx, start=0, end=None)
            cv.close()
        except Exception as e:
            return jsonify({'error': f'PDF → Word conversion failed: {str(e)}'}), 500

        with open(output_docx, "rb") as f:
            docx_data = f.read()

    # Log to MongoDB
    try:
        logs.insert_one({
            "type": "pdf_to_word",
            "filename": pdf_file.filename,
            "timestamp": datetime.now(timezone.utc)
        })
    except:
        pass

    return send_file(
        io.BytesIO(docx_data),
        as_attachment=True,
        download_name="converted.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# ----------------- Word → PDF (with images) -----------------
@app.route('/word-to-pdf', methods=['POST'])
def word_to_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    word_file = request.files['file']

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
                if para.text.strip():
                    pdf.multi_cell(0, 10, para.text)

            # Extract images from docx
            for rel in doc.part.rels.values():
                if "image" in rel.target_ref:
                    img_path = os.path.join(tmpdir, "img.png")
                    with open(img_path, "wb") as f:
                        f.write(rel.target_part.blob)
                    pdf.add_page()
                    pdf.image(img_path, w=pdf.epw)

            pdf.output(output_pdf)
        except Exception as e:
            return jsonify({'error': f'Word → PDF conversion failed: {str(e)}'}), 500

        with open(output_pdf, "rb") as f:
            pdf_data = f.read()

    # Log to MongoDB
    try:
        logs.insert_one({
            "type": "word_to_pdf",
            "filename": word_file.filename,
            "timestamp": datetime.now(timezone.utc)
        })
    except:
        pass

    return send_file(
        io.BytesIO(pdf_data),
        as_attachment=True,
        download_name="converted.pdf",
        mimetype="application/pdf"
    )

# ----------------- Images → PDF -----------------
@app.route('/images-to-pdf', methods=['POST'])
def images_to_pdf():
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400

    files = request.files.getlist('files')
    with tempfile.TemporaryDirectory() as tmpdir:
        output_pdf = os.path.join(tmpdir, 'output.pdf')
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        for img_file in files:
            img_path = os.path.join(tmpdir, img_file.filename)
            img_file.save(img_path)
            pdf.add_page()
            pdf.image(img_path, w=pdf.epw)  # Fit width

        pdf.output(output_pdf)
        with open(output_pdf, "rb") as f:
            pdf_data = f.read()

    # Log to MongoDB
    try:
        for img_file in files:
            logs.insert_one({
                "type": "images_to_pdf",
                "filename": img_file.filename,
                "timestamp": datetime.now(timezone.utc)
            })
    except:
        pass

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
