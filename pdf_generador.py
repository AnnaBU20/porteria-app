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
            c.drawImage(logo_path, width/2 - 80, height - 60, width=160, preserveAspectRatio=True, mask='auto')
        except:
            pass

        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2, height - 95, "Registro de Entrega del Protocolo de Seguridad")

        # Ajustamos tabla más arriba
        y_header = height - 125
        c.setFillColor(colors.HexColor('#163677'))
        c.rect(25, y_header - 15, width - 50, 25, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        headers = ["Fecha", "Hora", "Tipo operación", "Empresa", "Tractora", "Remolque", "Nombre", "DNI", "Idioma"]
        x_positions = [30, 100, 180, 300, 420, 520, 620, 750, 850]
        for i, header in enumerate(headers):
            c.drawString(x_positions[i], y_header, header)

        pie_legal(c, width, fecha_generacion, pagina_num)
        return y_header - 30

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
            alignment=4,  # Justificado total
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
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    x_positions = [30, 100, 180, 300, 420, 520, 620, 750, 850]

    for r in registros:
        datos = [
            str(r.fecha),
            r.hora_entrega.strftime('%H:%M'),
            r.tipo_operacion,
            r.empresa,
            r.matricula_tractora,
            r.matricula_remolque,
            r.nombre,
            r.dni,
            r.idioma
        ]
        for i, dato in enumerate(datos):
            c.drawString(x_positions[i], y, dato)

        c.setStrokeColor(colors.lightgrey)
        c.line(25, y - 3, width - 25, y - 3)

        y -= 20

        if y < 100:
            c.showPage()
            pagina += 1
            y = cabecera(pagina)
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.black)

    c.save()
    buffer.seek(0)
    return buffer