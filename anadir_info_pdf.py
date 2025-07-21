from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from PyPDF2 import PdfReader, PdfWriter
import os
import io

def generar_protocolo_desde_plantilla(registro):
    idioma = registro.idioma.upper()
    plantilla_filename = f"{idioma} - ES.pdf"  # <-- CORREGIDO AQUÍ
    plantilla_path = os.path.join("plantillas", plantilla_filename)

    if not os.path.exists(plantilla_path):
        raise FileNotFoundError(f"No se encuentra la plantilla: {plantilla_path}")

    output_path = os.path.join("pdfs", f"protocolo_{registro.id}.pdf")
    os.makedirs("pdfs", exist_ok=True)

    reader = PdfReader(plantilla_path)
    writer = PdfWriter()

    for pagina in reader.pages:
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=landscape(A4))

        # Información del camionero
        info = (
            f"Empresa: {registro.empresa}    Tractora: {registro.matricula_tractora}    "
            f"Remolque: {registro.matricula_remolque}    Nombre: {registro.nombre}    "
            f"DNI: {registro.dni}    Fecha: {registro.fecha.strftime('%Y-%m-%d')}    Idioma: {registro.idioma}"
        )

        # Añadir información a 3 cm desde el borde superior (1 cm debajo del título)
        can.setFont("Helvetica", 9)
        width, height = landscape(A4)
        can.drawCentredString(width / 2, height - 3 * 28.35, info)
        # Añadir imagen de la firma si existe
        if registro.firma_filename:
            firma_path = os.path.join("static", "firmas", registro.firma_filename)
            if os.path.exists(firma_path):
                firma_width = 100  # ancho de la imagen
                firma_height = 40  # alto de la imagen
                x_firma = width - firma_width - 28.35  # 28.35 puntos desde el borde derecho
                y_firma = height - firma_height - 28.35  # 28.35 puntos desde el borde superior
                can.drawImage(firma_path, x_firma, y_firma, width=firma_width, height=firma_height, preserveAspectRatio=True, mask='auto')
        can.save()

        packet.seek(0)
        overlay_pdf = PdfReader(packet)
        overlay_page = overlay_pdf.pages[0]

        pagina.mediabox.upper_right = (width, height)
        pagina.merge_page(overlay_page)
        writer.add_page(pagina)

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path