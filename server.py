from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from pdf2docx import Converter
from docx2pdf import convert
import os
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://pdftword.netlify.app"]}})


# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if file and file.filename.endswith('.pdf'):
        try:
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
                    logger.error(f"Error deleting files: {e}")
                return response
            return send_file(docx_path, as_attachment=True)
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return jsonify({'error': f'Conversion failed: {str(e)}'}), 500
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
        try:
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
                    logger.error(f"Error deleting files: {e}")
                return response
            return send_file(pdf_path, as_attachment=True)
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return jsonify({'error': f'Conversion failed: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
