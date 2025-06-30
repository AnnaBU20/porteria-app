from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os
from datetime import datetime
from googletrans import Translator

def generar_protocolo(registro):
    os.makedirs("pdfs", exist_ok=True)
    filename = f"protocolo_{registro.id}.pdf"
    ruta_pdf = os.path.join("pdfs", filename)

    c = canvas.Canvas(ruta_pdf, pagesize=landscape(A4))
    width, height = landscape(A4)

    margen_superior = height - 40
    margen_lateral = 50

    # TÍTULO
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, margen_superior, "PROTOCOLO DE SEGURIDAD")

    # DATOS DEL CAMIONERO
    c.setFont("Helvetica", 10)
    datos_linea1 = (
        f"Fecha: {registro.fecha}    Hora: {registro.hora_entrega.strftime('%H:%M')}    "
        f"Tipo operación: {registro.tipo_operacion}    Empresa: {registro.empresa}"
    )
    datos_linea2 = (
        f"Tractora: {registro.matricula_tractora}    Remolque: {registro.matricula_remolque}    "
        f"Nombre: {registro.nombre}    DNI: {registro.dni}    Idioma: {registro.idioma}"
    )
    c.drawCentredString(width / 2, margen_superior - 20, datos_linea1)
    c.drawCentredString(width / 2, margen_superior - 35, datos_linea2)

    # TEXTO ORIGINAL EN ESPAÑOL (COMPLETO)
    texto_es = """
(ES) RESPONSABILIDAD DE LOS CONDUCTORES
1. Acceso y operaciones en KRONOSPAN
El conductor debe:
a) Llevar ropa reflectante de ALTA VISIBILIDAD, CALZADO DE SEGURIDAD y CASCO DE SEGURIDAD durante las operaciones de carga y descarga.
b) Permanecer en el interior del vehículo, salvo que se requiera su presencia, en cuyo caso, mantenerse fuera del radio de acción de la carga y las máquinas.
c) Circular por los pasillos peatonales habilitados para ello.
d) Respetar el mapa de circulación, el limite de velocidad de 10-20 Km/h, la señalizacion vial y los pasos de peatones. Llevar las luces encendidas.
e) Usar el Arnes de Seguridad y la línea de vida dispuesta para ello, cuando necesite subirse al camión.
2. Seguridad de las personas
a) Apagar el motor. NO fumar.
b) NO pasar por los puertas automáticas para vehículos. Usar las puertas peatonales.
c) NO utilizar sistemas de elevación de KRONOSPAN.
d) NO permanezca en el radio de accion de maquinaria, bajo cargas suspendidas o junto a los paquetes de tablero.
e) NO abandone materiales junto a zonas de transito de personas o vehículos.
t) NO se suba a los paquetes de tablero. Utilice medios auxiliares adecuados.
3. Seguridad de la carga y de los materiales transportados
El conductor es la única persona con responsabilidad directa, para la carga y el transporte de materiales, y por lo tanto debe:
a) Supervisar personalmente la correcta carga de todos los materiales en su vehículo.
b) Fijar, atar y asegurar personalmente todos los materiales cargados en su vehículo para evitar cualquier movimiento de la carga o perdida de materiales, tanto durante las operaciones de carga en KRONOSPAN y sobre todo durante el siguiente transporte por carretera.
c) Cubrir adecuadamente los materiales, tanto para una mayor seguridad durante su transporte, como para evitar daños a los materiales.
4. Declaración de responsabilidad del conductor
Con la firma de este documento, el conductor declara :
a) Asumir personalmente cualquier responsabilidad directa e indirecta, tanto civiles como penales para los accidentes, lesiones o daños a personas, a la propiedad de KRONOSPAN o de terceros derivadas de la no observación o del incumplimiento de las normas de seguridad que figuran en los puntos 1, 2 y 3 de este documento.
b) Asumir personalmente cualquier responsabilidad directa e indirecta, tanto civiles como penales para los accidentes, lesiones o daños a personas, a la propiedad de KRONOSPAN o de terceros causados durente la carga del camión y el transporte por carretera de la mercancia hasta destino final.

(ES) NORMAS DE ACTUACIÓN MEDIOAMBIENTAL
1. Residuos autorizados a despositar en las instalaciones
a) Sólo se podrán depositar en las instalaciones de Kronospan residuos domésticos (envases, basura orgánica y latas) y residuos de madera recogidos al barrer el fondo de la caja.
b) Estos residuos se depositarán en los contenedores correspondientes (ver figura 1).
Basura orgánica: contenedor marrón / Envases: contenedor amarillo / Latas: contenedor negro / Barreduras: contenedor verde
2. Operaciones de mantenimiento de los vehículos
a) Está prohibida cualquier operación de mantenimiento de sus vehículos, como pueden ser la limpieza o sustitución de filtros, cambios de aceite, limpieza exterior del vehículo...
b) Sólo está autorizada la limpieza del interior de la caja para retirar restos de madera cuando se realiza la descarga de material en el parque de madera. En las zonas de carga de tablero, la limpieza del interior de la caja está permitida siempre que se recojan los residuos y se depositen en el contenedor habilitado para ello.
3. Vertido accidental
a) En caso de vertido accidental, se debe utilizar el absorbente que hay a disposición y, si hay una arqueta cercana, se debe proteger con las mangas absorbentes (ver figura 2).
b) Avisar inmediatamente a personal de Kronospan.
4. Incumplimiento de las normas
a) El incumplimiento de las presentes normas tendrá como consecuencia la imposición de una multa de 150 € por infracción, que será descontada por Kronospan en el siguiente pago, todo ello sin perjuicio de que el transportista y/o su empresa se haga cargo, como responsable, de todos los daños y perjuicios ocasionados por el incumplimiento.
"""

    # ESPAÑOL a la izquierda
    c.setFont("Helvetica", 7)
    text_es = c.beginText(margen_lateral, margen_superior - 65)
    text_es.setLeading(9)
    for linea in texto_es.split('\n'):
        text_es.textLine(linea.strip())
    c.drawText(text_es)

    # TRADUCCIÓN AUTOMÁTICA a la derecha
    translator = Translator()
    try:
        if registro.idioma.upper() != "ES":
            traduccion = translator.translate(texto_es, dest=registro.idioma.lower())
            texto_traducido = traduccion.text
        else:
            texto_traducido = "(Mismo texto en español)"
    except Exception:
        texto_traducido = "(Traducción automática no disponible)"

    c.setFont("Helvetica", 7)
    text_otro = c.beginText(width/2 + 50, margen_superior - 65)
    text_otro.setLeading(9)
    for linea in texto_traducido.split('\n'):
        text_otro.textLine(linea.strip())
    c.drawText(text_otro)

    # PIE DE PÁGINA
    c.setFont("Helvetica-Oblique", 6)
    pie1 = "ES: Sus datos serán tratados con el fin de controlar el acceso a las instalaciones de Kronospan en condiciones de seguridad."
    pie2 = "Puede ejercitar sus derechos de acceso, rectificación o supresión, limitación del tratamiento, Castañares S/N, Burgos, 09199 (España)"
    pie3 = "EN: Your data will be processed in order to control access to the Kronospan facilities under safe conditions."
    pie4 = "Email: privacy@kronospan.es — Spanish Data Protection Agency (www.aepd.es)"

    base_y = 25
    c.drawCentredString(width / 2, base_y, pie1)
    c.drawCentredString(width / 2, base_y - 8, pie2)
    c.drawCentredString(width / 2, base_y - 16, pie3)
    c.drawCentredString(width / 2, base_y - 24, pie4)

    # FECHA GENERACIÓN
    fecha_gen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.setFont("Helvetica-Oblique", 8)
    c.drawRightString(width - 30, height - 20, f"Generado: {fecha_gen}")

    c.save()
    return ruta_pdf