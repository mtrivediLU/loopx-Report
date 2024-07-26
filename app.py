from flask import Flask, request, render_template, redirect, url_for, send_file
import google.generativeai as genai
import base64
import os
import tempfile
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.utils import simpleSplit

app = Flask(__name__)
genai.configure(api_key='AIzaSyBTVVFF8RVfAcEU1rvHJsFWUkud9IahSbQ')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_images():
    if 'files[]' not in request.files:
        return redirect(url_for('index'))
    
    files = request.files.getlist('files[]')
    details_list = []
    image_paths = []

    for file in files:
        if file.filename == '':
            continue
        if file:
            os.makedirs('static', exist_ok=True)
            
            file_path = os.path.join('static', file.filename)
            file.save(file_path)
            
            with open(file_path, 'rb') as img_file:
                img_data = img_file.read()
            encoded_image = base64.b64encode(img_data).decode('utf-8')

            details = {
                "speed": ask_gemini_for_detail(encoded_image, "What is the speed of the vehicle in the image?"),
                "time": ask_gemini_for_detail(encoded_image, "What is the time shown in the image?"),
                "num_people": ask_gemini_for_detail(encoded_image, "How many people are in the image?"),
                "degree": ask_gemini_for_detail(encoded_image, "What is the degree of the vehicle in the image?"),
                "incident": ask_gemini_for_detail(encoded_image, "Describe the incident shown in the image."),
                "full_description": ask_gemini_for_detail(encoded_image, "Describe the content of the image in detail.")
            }

            details_list.append(details)
            image_paths.append(file.filename)

    return render_template('result.html', details_list=details_list, image_paths=image_paths, zip=zip)

def ask_gemini_for_detail(encoded_image, question):
    request_payload = [
        {
            "role": "user",
            "parts": [
                {"text": question},
                {"inline_data": {"mime_type": "image/png", "data": encoded_image}}
            ]
        }
    ]

    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    response = model.generate_content(contents=request_payload)
    return response.candidates[0].content.parts[0].text.strip()

@app.route('/download_report', methods=['POST'])
def download_report():
    details_list = request.form.getlist('details_list')
    details_list = [json.loads(details) for details in details_list]
    image_paths = request.form.getlist('image_paths')

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as pdf_file:
        generate_pdf(pdf_file.name, details_list, image_paths)
        return send_file(pdf_file.name, as_attachment=True, download_name='incident_report.pdf')

def generate_pdf(file_path, details_list, image_paths):
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    title = "Incident Report"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))

    for i, (details, image_path) in enumerate(zip(details_list, image_paths)):
        img = Image(os.path.join('static', image_path))
        img.drawHeight = 2 * inch
        img.drawWidth = 2 * inch
        img.hAlign = 'CENTER'

        data = [
            ['Degree:', wrap_text(details['degree'], 4 * inch)],
            ['Incident:', wrap_text(details['incident'], 4 * inch)],
            ['Number of People:', wrap_text(details['num_people'], 4 * inch)],
            ['Speed:', wrap_text(details['speed'], 4 * inch)],
            ['Time:', wrap_text(details['time'], 4 * inch)],
            ['Full Description:', wrap_text(details['full_description'], 4 * inch)]
        ]

        table = Table(data, colWidths=[2 * inch, 4 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        elements.append(Paragraph(f"Image {i+1}", styles['Heading2']))
        elements.append(img)
        elements.append(Spacer(1, 12))
        elements.append(table)
        elements.append(Spacer(1, 12))

    doc.build(elements)

def wrap_text(text, width):
    wrapped_text = "<br/>".join(simpleSplit(text, 'Helvetica', 12, width))
    return Paragraph(wrapped_text, getSampleStyleSheet()['BodyText'])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
