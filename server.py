from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from pdf2docx import Converter
from docx2pdf import convert
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://pdftword.netlify.app"]}})

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        docx_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.pdf', '.docx'))
        file.save(pdf_path)

        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()

        @after_this_request
        def remove_file(response):
            try:
                os.remove(pdf_path)
                os.remove(docx_path)
            except Exception as e:
                print(f"Error deleting files: {e}")
            return response

        return send_file(docx_path, as_attachment=True)
    else:
        return jsonify({'error': 'Invalid file type'}), 400

@app.route('/word-to-pdf', methods=['POST'])
def word_to_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if file and file.filename.endswith('.docx'):
        filename = secure_filename(file.filename)
        docx_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.docx', '.pdf'))
        file.save(docx_path)

        convert(docx_path, pdf_path)

        @after_this_request
        def remove_file(response):
            try:
                os.remove(docx_path)
                os.remove(pdf_path)
            except Exception as e:
                print(f"Error deleting files: {e}")
            return response

        return send_file(pdf_path, as_attachment=True)
    else:
        return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    app.run(debug=True)
