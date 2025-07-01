from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
import os
from datetime import datetime

def generar_pdf(registros):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    fecha_generacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def cabecera(pagina_num):
        logo_path = os.path.join(os.getcwd(), "static", "logo.jpeg")
        try:
            c.drawImage(logo_path, 30, height - 60, width=100, preserveAspectRatio=True, mask='auto')
        except:
            pass

        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 40, "HOJA DE REGISTRO DE ENTREGA DE INFORMACIÓN A LOS CONDUCTORES")

        c.setFont("Helvetica", 8)
        c.drawRightString(width - 30, height - 30, f"Generado: {fecha_generacion}")

        # Encabezados de tabla personalizados
        y = height - 80
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)

        # Rectángulos grandes para secciones
        c.rect(25, y - 40, width - 50, 30, stroke=1, fill=0)  # Cabecera superior
        c.setFont("Helvetica-Bold", 9)
        c.drawString(30, y - 25, "Empresa")
        c.drawString(160, y - 25, "Información del Vehículo")
        c.drawString(360, y - 35, "Matrícula Tractora")
        c.drawString(500, y - 35, "Matrícula Remolque")
        c.drawString(640, y - 25, "Información del Conductor")
        c.drawString(760, y - 35, "Nombre")
        c.drawString(880, y - 35, "DNI")
        c.drawString(1000, y - 25, "Fecha")
        c.drawString(1080, y - 25, "Firma")

        pie_legal(c, width, fecha_generacion, pagina_num)
        return y - 50

    def pie_legal(c, width, fecha_generacion, pagina_num):
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.gray)

        texto_es = ("Sus datos serán tratados con el fin de controlar el acceso a las instalaciones de Kronospan en condiciones de seguridad. Puede ejercitar sus derechos de acceso, rectificación o supresión, limitación del tratamiento, portabilidad u oposición mediante el envio de un correo postal a Barrio Castañares S/N, Burgos, 09199 (España), o por medio de un correo electrónico dirigido a: privacy@kronospan.es Ello sin perjuicio de su derecho de presentar reclamación ante la Agencia Española de Protección de Datos (www.aepd.es) en caso de considerar vulnerados sus derechos en este ámbito.")
        texto_en = ("Your data will be processed in order to control access to the Kronospan facilities under safe conditions. You may exercise your rights of access, rectification or elimination, limitation of treatment, portability or opposition by sending a postal mail to Barrio Castañares S/N, Burgos 09199 (Spain), or by email addressed to: privacy@kronospan.es This without prejudice to your right to file a claim with the Spanish Agency for Data Protection (www.aepd.es) in case you consider your rights violated in this area.")

        texto_total = f"{texto_es}\n\n{texto_en}"

        styles = getSampleStyleSheet()
        justified = ParagraphStyle(
            name='Justificado',
            parent=styles['Normal'],
            alignment=4,
            fontName="Helvetica",
            fontSize=6,
            leading=8,
            textColor=colors.gray,
        )

        p = Paragraph(texto_total, justified)
        frame = Frame(30, 30, width - 60, 60, showBoundary=0)
        frame.addFromList([p], c)

        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(colors.gray)
        c.drawRightString(width - 30, 15, f"Generado: {fecha_generacion}  -  Página {pagina_num}")

    pagina = 1
    y = cabecera(pagina)
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)

    for r in registros:
        if y < 100:
            c.showPage()
            pagina += 1
            y = cabecera(pagina)
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.black)

        c.drawString(30, y, r.empresa)
        c.drawString(360, y, r.matricula_tractora)
        c.drawString(500, y, r.matricula_remolque)
        c.drawString(760, y, r.nombre)
        c.drawString(880, y, r.dni)
        c.drawString(1000, y, r.fecha.strftime('%Y-%m-%d'))

        firma_path = os.path.join("static", "firmas", r.firma_filename) if r.firma_filename else None
        if firma_path and os.path.exists(firma_path):
            try:
                c.drawImage(firma_path, 1080, y - 5, width=50, height=20, preserveAspectRatio=True, mask='auto')
            except:
                pass

        y -= 25

    c.save()
    buffer.seek(0)
    return buffer