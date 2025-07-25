from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from PyPDF2 import PdfReader, PdfWriter
import os
import io
from datetime import datetime
from reportlab.lib.utils import ImageReader

def generar_registro_pdf(registros):
    plantilla_path = os.path.join("plantillas", "registro_conductores.pdf")
    if not os.path.exists(plantilla_path):
        raise FileNotFoundError(f"No se encuentra la plantilla base: {plantilla_path}")

    output_path = os.path.join("pdfs", "registro_conductores_generado.pdf")
    os.makedirs("pdfs", exist_ok=True)

    filas_por_pagina = 16
    paginas = [registros[i:i+filas_por_pagina] for i in range(0, len(registros), filas_por_pagina)]

    writer = PdfWriter()
    for registros_pagina in paginas:
        reader = PdfReader(plantilla_path)
        template_page = reader.pages[0]
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=landscape(A4))

        coordenadas = [
            (62.64, 428.64), (198, 428.64), (294.24, 428.64), (388.56, 428.64), (523.2, 428.64), (614.88, 428.64), (686.64, 428.64),
            (62.64, 406.32), (198, 406.08), (294.24, 406.32), (388.56, 406.32), (523.2, 406.32), (614.88, 406.32), (686.64, 406.32),
            (62.64, 382.8), (197.76, 382.8), (294.24, 382.8), (388.56, 382.8), (523.2, 382.8), (614.88, 382.8), (686.64, 382.8),
            (62.64, 360.24), (198, 360.24), (294.24, 360.24), (388.56, 360.24), (523.2, 360.24), (614.88, 360.24), (686.64, 360.24),
            (62.64, 337.44), (198, 337.44), (294.24, 337.44), (388.56, 337.44), (523.2, 337.44), (614.88, 337.44), (686.64, 337.44),
            (62.64, 314.88), (198, 314.88), (294.24, 314.88), (388.56, 314.88), (523.2, 314.88), (614.88, 314.88), (686.64, 314.88),
            (62.64, 292.08), (198, 291.84), (294.24, 291.84), (388.56, 292.08), (523.44, 291.84), (614.88, 292.08), (686.64, 292.08),
            (62.64, 270), (197.76, 270), (294.24, 270), (388.56, 270), (523.2, 270), (614.88, 270), (686.64, 270),
            (62.64, 247.44), (198, 247.44), (294.24, 247.44), (388.56, 247.44), (523.44, 247.44), (614.88, 247.44), (686.64, 247.44),
            (62.64, 224.16), (198, 224.16), (294.24, 224.16), (388.56, 224.16), (523.2, 224.16), (614.88, 224.16), (686.64, 224.16),
            (62.64, 201.12), (197.76, 201.12), (294.24, 201.12), (388.56, 201.12), (523.2, 201.12), (614.88, 201.12), (686.64, 201.12),
            (62.64, 178.8), (198, 178.56), (294.24, 178.56), (388.56, 178.8), (523.44, 178.56), (614.88, 178.8), (686.64, 178.8),
            (62.64, 155.76), (197.76, 155.76), (294.24, 155.76), (388.56, 155.76), (523.2, 155.76), (614.88, 155.76), (686.64, 155.76),
            (62.64, 133.2), (198, 133.2), (294.24, 133.2), (388.56, 133.2), (523.2, 133.2), (614.88, 133.2), (686.64, 133.2),
            (62.64, 111.36), (198, 111.36), (294.24, 111.36), (388.56, 111.36), (523.2, 111.36), (614.88, 111.36), (686.64, 111.36),
            (62.64, 88.32), (198, 88.32), (294.24, 88.32), (388.56, 88.32), (523.2, 88.32), (614.88, 88.32), (686.64, 88.32),
        ]

        for i, registro in enumerate(registros_pagina):
            base_idx = i * 7
            can.setFont("Helvetica", 8)
            can.drawString(coordenadas[base_idx + 0][0], coordenadas[base_idx + 0][1], registro['empresa'])
            can.drawString(coordenadas[base_idx + 1][0], coordenadas[base_idx + 1][1], registro['matricula_tractora'])
            can.drawString(coordenadas[base_idx + 2][0], coordenadas[base_idx + 2][1], registro['matricula_remolque'])
            can.drawString(coordenadas[base_idx + 3][0], coordenadas[base_idx + 3][1], registro['nombre'])
            can.drawString(coordenadas[base_idx + 4][0], coordenadas[base_idx + 4][1], registro['dni'])
            can.drawString(coordenadas[base_idx + 5][0], coordenadas[base_idx + 5][1], registro['fecha'])
            # Insertar firma si existe
            if registro.get('firma_filename'):
                firma_path = os.path.join("static", "firmas", registro['firma_filename'])
                if os.path.exists(firma_path):
                    try:
                        firma = ImageReader(firma_path)
                        x_firma, y_firma = coordenadas[base_idx + 6]
                        can.drawImage(firma, x_firma, y_firma - 10, width=60, height=20, preserveAspectRatio=True, mask='auto')
                    except Exception as e:
                        print(f"Error al insertar firma: {e}")
                        can.drawString(coordenadas[base_idx + 6][0], coordenadas[base_idx + 6][1], "Firma no disponible")
    can.save()
    packet.seek(0)
    overlay_pdf = PdfReader(packet)        
    overlay_page = overlay_pdf.pages[0]
    template_page.merge_page(overlay_page)
    writer.add_page(template_page)

        
    # Añadir pie de página legal

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path