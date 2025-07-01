from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io
import os

def generar_registro_pdf(registros):
    plantilla_path = os.path.join("plantillas", "registro_conductores.pdf")
    if not os.path.exists(plantilla_path):
        raise FileNotFoundError(f"No se encuentra la plantilla: {plantilla_path}")

    output_pdf = PdfWriter()

    # Ajusta estas posiciones según tu plantilla
    posiciones = [
        380, 360, 340, 320, 300, 280, 260, 240,
        220, 200, 180, 160, 140, 120, 100, 80
    ]

    pagina = 0
    for i, registro in enumerate(registros):
        if i % 16 == 0:
            if i > 0:
                output_pdf.add_page(pagina_completa)

            reader = PdfReader(plantilla_path)
            pagina_base = reader.pages[0]

            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=A4)

            pagina_completa = pagina_base
            packet.seek(0)
            pagina += 1

        idx = i % 16
        y = posiciones[idx]

        can.setFont("Helvetica", 8)
        can.drawString(55, y, str(registro.empresa))
        can.drawString(180, y, str(registro.matricula_tractora))
        can.drawString(260, y, str(registro.matricula_remolque))
        can.drawString(340, y, str(registro.nombre))
        can.drawString(420, y, str(registro.dni))
        can.drawString(500, y, registro.fecha.strftime('%Y-%m-%d'))

        if registro.firma_filename:
            firma_path = os.path.join("static", "firmas", registro.firma_filename)
            if os.path.exists(firma_path):
                can.drawImage(firma_path, 570, y - 5, width=50, height=20, preserveAspectRatio=True, mask='auto')

        if idx == 15 or i == len(registros) - 1:
            can.save()
            packet.seek(0)
            overlay = PdfReader(packet).pages[0]
            pagina_base.merge_page(overlay)
            output_pdf.add_page(pagina_base)

    buffer = io.BytesIO()
    output_pdf.write(buffer)
    buffer.seek(0)
    return buffer