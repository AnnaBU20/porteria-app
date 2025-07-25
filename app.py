from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
import io
import base64
import re
import qrcode
import uuid
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import requests
from anadir_info_pdf import generar_protocolo_desde_plantilla
from generar_registro_conductores_pdf import generar_registro_pdf
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import pandas as pd
from flask import send_file
import json
import pytz
from datetime import datetime, timedelta
from models import db, Registro 



app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_segura'

basedir = os.path.abspath(os.path.dirname(__file__))

# Usar PostgreSQL en Render, SQLite en local
if os.environ.get("RENDER") == "true":
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
    db_path = os.path.join(basedir, 'instance', 'porteria.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

ULTRAMSG_INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID")
ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN")

class QRUnico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    usado = db.Column(db.Boolean, default=False, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_uso = db.Column(db.DateTime, nullable=True)

    def marcar_como_usado(self):
        self.usado = True
        self.fecha_uso = datetime.utcnow()
        db.session.commit()

class Usuario(UserMixin):
    id = 1
    username = "porteria"
    password = "porteria123"

class Camionero(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricula_tractora = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), unique=True, nullable=False)
    empresa = db.Column(db.String(100), nullable=False)
    matricula_remolque = db.Column(db.String(20), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    if user_id == "1":
        return Usuario()
    return None

@app.route('/', methods=['GET', 'POST'])
def formulario():
    camionero_data = None  # ← Este debe ir bien alineado

    if 'camionero_id' in session:
        camionero = Camionero.query.get(session['camionero_id'])
        if camionero:
            camionero_data = camionero

    if request.method == 'POST':
        tipo_operacion = request.form['tipo_operacion']
        empresa = request.form['empresa']
        matricula_tractora = request.form['matricula_tractora']
        matricula_remolque = request.form['matricula_remolque']
        nombre = request.form['nombre']
        dni = request.form['dni']
        telefono = request.form['telefono']
        fecha = datetime.strptime(request.form['fecha'], "%Y-%m-%d").date()
        idioma = request.form['idioma']

        acepta = 'acepta' in request.form
        proteccion_datos = 'proteccion_datos' in request.form

        if not acepta or not proteccion_datos:
            flash("Debe aceptar las condiciones de seguridad y la política de protección de datos.")
            return redirect(url_for('formulario'))

        firma_data = request.form['firma_base64']
        match = re.match(r'data:image/png;base64,(.*)', firma_data)
        firma_filename = None
        if match:
            firma_bytes = base64.b64decode(match.group(1))
            firma_filename = f"{nombre}_{dni}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            
            # Crear ruta segura para la firma (Render o local)
            if os.environ.get("RENDER") == "true":
                firma_dir = '/tmp/firmas'  # Render solo permite escritura en /tmp
            else:
                firma_dir = os.path.join("static", "firmas")

            os.makedirs(firma_dir, exist_ok=True)
            firma_path = os.path.join(firma_dir, firma_filename)

            with open(firma_path, "wb") as f:
                f.write(firma_bytes)
        
        zona_horaria = pytz.timezone('Europe/Madrid')
        hora_entrega = datetime.now(zona_horaria)

        nuevo_registro = Registro(
            tipo_operacion=tipo_operacion,
            empresa=empresa,
            matricula_tractora=matricula_tractora,
            matricula_remolque=matricula_remolque,
            nombre=nombre,
            dni=dni,
            telefono=telefono,
            fecha=fecha,
            acepta=acepta,
            proteccion_datos=proteccion_datos,
            idioma=idioma,
            firma_filename=firma_filename,
            hora_entrega=hora_entrega 
        )

        db.session.add(nuevo_registro)
        db.session.commit()

        protocolo_path = generar_protocolo_desde_plantilla(nuevo_registro)
        nuevo_registro.protocolo_filename = os.path.basename(protocolo_path)
        db.session.commit()

        return render_template('confirmacion.html', registro_id=nuevo_registro.id, protocolo_filename=nuevo_registro.protocolo_filename)

    return render_template('formulario.html', camionero_data=camionero_data, datetime=datetime)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == "porteria" and request.form['password'] == "porteria123":
            login_user(Usuario())
            return redirect(url_for('registros'))
        flash("Credenciales incorrectas.")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/registros')
@login_required
def registros():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    query = Registro.query
    if fecha_inicio and fecha_fin:
        query = query.filter(Registro.fecha >= datetime.strptime(fecha_inicio, "%Y-%m-%d").date(),
                             Registro.fecha <= datetime.strptime(fecha_fin, "%Y-%m-%d").date())
    return render_template('registros.html', registros=query.all())

@app.route('/panel-control')
@login_required
def panel_control():
    registros = Registro.query.order_by(Registro.hora_entrega.desc()).all()
    return render_template('panel_control.html', registros=registros)

@app.route('/descargar_protocolo/<int:registro_id>')
def descargar_protocolo(registro_id):
    registro = Registro.query.get_or_404(registro_id)
    if registro.protocolo_filename:
        return send_file(os.path.join("pdfs", registro.protocolo_filename), as_attachment=True)
    flash("Este registro no tiene protocolo generado.")
    return redirect(url_for('registros'))

@app.route('/qr')
def qr():
    return render_template('qr.html')

@app.route('/qr_image')
def qr_image():
    qr = qrcode.make("https://porteria-kr.onrender.com")
    img_io = io.BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/qr_lote')
@login_required
def qr_lote():
    return render_template('qr_lote.html')

@app.route('/generar_qr_lote')
@login_required
def generar_qr_lote():
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Margen de 1cm (10mm)
    margen = 10 * mm
    qr_size = 30 * mm
    texto_offset_x = 5 * mm
    espacio_entre_qr_y_texto = 15 * mm
    espacio_vertical = (height - 2 * margen - 7 * qr_size) / 6  # 7 filas, 6 huecos

    # Columnas
    col1_x_qr = margen
    col1_x_texto = col1_x_qr + qr_size + texto_offset_x - 5 * mm

    col2_x_texto_derecha = width - margen
    col2_x_texto = col2_x_texto_derecha - 60 * mm  # Aproximado
    col2_x_qr = col2_x_texto - espacio_entre_qr_y_texto - qr_size + 15 * mm

    y = height - margen - qr_size

    for fila in range(7):
        for col in range(2):
            codigo = str(uuid.uuid4())
            link = f"https://porteria-kr.onrender.com/registro_unico/{codigo}"

            nuevo_qr = QRUnico(codigo=codigo)
            db.session.add(nuevo_qr)

            qr_img = qrcode.make(link)
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            qr_reader = ImageReader(qr_buffer)

            # Posición en columna
            if col == 0:
                qr_x = col1_x_qr
                text_x = col1_x_texto
            else:
                qr_x = col2_x_qr
                text_x = col2_x_texto

            # Dibujar QR
            c.drawImage(qr_reader, qr_x, y, width=qr_size, height=qr_size)

            # Texto centrado verticalmente respecto al QR
            text_y = y + qr_size / 2 + 4

            c.setFont("Helvetica", 9)
            c.drawString(text_x, text_y, "Escanee este código al llegar a Kronospan")
            c.drawString(text_x, text_y - 12, "para registrarse. Este QR es de un solo uso.")

        y -= qr_size + espacio_vertical

    db.session.commit()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="qr_kronospan.pdf", mimetype='application/pdf')

@app.route('/registro_unico/<codigo>', methods=['GET', 'POST'])
def registro_unico(codigo):
    qr = QRUnico.query.filter_by(codigo=codigo).first()

    if not qr:
        flash("⚠️ Este código QR no es válido.")
        return redirect(url_for('qr'))

    if qr.usado:
        flash("⚠️ Este código QR ya ha sido utilizado.")
        return redirect(url_for('qr'))

    qr.marcar_como_usado()
    return redirect(url_for('formulario'))

@app.route('/actualizar_estado/<int:registro_id>', methods=['POST'])
@login_required
def actualizar_estado(registro_id):
    registro = Registro.query.get_or_404(registro_id)
    registro.estado = request.form.get('nuevo_estado')
    db.session.commit()

    if registro.estado == "dentro" and registro.telefono:
        url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
        payload = {
            "token": ULTRAMSG_TOKEN,
            "to": f"+34{registro.telefono}",
            "body": f"Buenos días {registro.nombre}, ya puede subir a báscula e ingresar a portería. Gracias por su paciencia."
        }
        try:
            response = requests.post(url, data=payload)
            print("WhatsApp enviado:", response.json())
        except Exception as e:
            print("Error al enviar WhatsApp:", e)

    return redirect(url_for('panel_control'))

@app.route('/eliminar_registro/<int:registro_id>', methods=['POST'])
@login_required
def eliminar_registro(registro_id):
    db.session.delete(Registro.query.get_or_404(registro_id))
    db.session.commit()
    flash("Registro eliminado correctamente.")
    return redirect(url_for('panel_control'))

@app.route('/exportar_registros_pdf', methods=['POST'])
@login_required
def exportar_registros_pdf():
    from generar_registro_conductores_pdf import generar_registro_pdf

    registros_filtrados = request.form.get('registros_filtrados')
    if not registros_filtrados:
        flash("No se recibieron registros filtrados.")
        return redirect(url_for('registros'))

    try:
        registros = json.loads(registros_filtrados)
    except Exception as e:
        flash("Error al procesar los registros.")
        return redirect(url_for('registros'))

    for r in registros:
        try:
            fecha_dt = datetime.strptime(r['fecha'], "%d/%m/%Y").date()
        except ValueError:
            fecha_dt = datetime.strptime(r['fecha'], "%Y-%m-%d").date()

        registro_db = Registro.query.filter_by(dni=r['dni'], fecha=fecha_dt).first()
        if registro_db and not r.get('firma_filename'):
            r['firma_filename'] = registro_db.firma_filename

    if registros:
        print("🧾 Ejemplo de registro antes de generar PDF:")
        print(registros[0])

    # Generar el PDF con los registros completos (incluyendo la firma)
    ruta_pdf = generar_registro_pdf(registros)

    return send_file(
        ruta_pdf,
        as_attachment=True,
        download_name='registro_conductores.pdf',
        mimetype='application/pdf'
    )

@app.route('/login-camionero', methods=['GET', 'POST'])
def login_camionero():
    if request.method == 'POST':
        dni = request.form['dni']
        password = request.form['password']

        camionero = Camionero.query.filter_by(dni=dni).first()

        if camionero and camionero.check_password(password):
            # Guardamos su info en la sesión para autorrellenar luego
            session['camionero_id'] = camionero.id
            flash("Has iniciado sesión correctamente.")
            return redirect(url_for('formulario'))
        else:
            flash("Matrícula o contraseña incorrecta.")
            return redirect(url_for('login_camionero'))

    return render_template('login_camionero.html')

@app.route('/registro-camionero', methods=['GET', 'POST'])
def registro_camionero():
    if request.method == 'POST':
        dni = request.form['dni']
        password = request.form['password']
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        empresa = request.form['empresa']
        matricula_tractora = request.form['matricula_tractora']
        matricula_remolque = request.form['matricula_remolque']

        # Verificar si ya existe un camionero con ese DNI o matrícula
        if Camionero.query.filter_by(dni=dni).first():
            flash("Ya existe un usuario con ese DNI.")
            return redirect(url_for('registro_camionero'))
        if Camionero.query.filter_by(matricula_tractora=matricula_tractora).first():
            flash("Ya existe un usuario con esa matrícula tractora.")
            return redirect(url_for('registro_camionero'))

        nuevo = Camionero(
            dni=dni,
            nombre=nombre,
            telefono=telefono,
            empresa=empresa,
            matricula_tractora=matricula_tractora,
            matricula_remolque=matricula_remolque
        )
        nuevo.set_password(password)

        db.session.add(nuevo)
        db.session.commit()
        flash("Registro exitoso. Ahora puedes iniciar sesión.")
        return redirect(url_for('login_camionero'))

    return render_template('registro_camionero.html')

@app.route('/logout-camionero')
def logout_camionero():
    session.pop('camionero_id', None)
    flash("Sesión cerrada correctamente.")
    return redirect(url_for('formulario'))

@app.route('/exportar_registros_excel', methods=['POST'])
@login_required
def exportar_registros_excel():
    registros_filtrados = request.form.get('registros_filtrados')
    if not registros_filtrados:
        flash("No se recibieron registros filtrados.")
        return redirect(url_for('registros'))

    try:
        import json
        registros = json.loads(registros_filtrados)
    except Exception as e:
        flash("Error al procesar los registros.")
        return redirect(url_for('registros'))

    df = pd.DataFrame(registros)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Registros')

    output.seek(0)
    nombre_archivo = f"registros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, as_attachment=True, download_name=nombre_archivo, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def limpiar_registros_antiguos():
    limite = datetime.utcnow() - timedelta(days=30)
    registros_a_borrar = Registro.query.filter(Registro.fecha < limite.date()).all()
    for registro in registros_a_borrar:
        # Eliminar firma si existe
        if registro.firma_filename:
            ruta_firma = os.path.join("static", "firmas", registro.firma_filename)
            if os.path.exists(ruta_firma):
                os.remove(ruta_firma)
        db.session.delete(registro)
    db.session.commit()


@app.before_request
def ejecutar_limpieza():
    ruta_marcador = 'ultima_limpieza.txt'
    hoy = datetime.utcnow().date()

    # Si el archivo no existe, crearlo y ejecutar limpieza
    if not os.path.exists(ruta_marcador):
        with open(ruta_marcador, 'w') as f:
            f.write(hoy.isoformat())
        limpiar_registros_antiguos()
        return

    # Leer la fecha de la última limpieza
    with open(ruta_marcador, 'r') as f:
        ultima_fecha_str = f.read().strip()
        try:
            ultima_fecha = datetime.fromisoformat(ultima_fecha_str).date()
        except ValueError:
            ultima_fecha = hoy - timedelta(days=1)  # Forzar limpieza si el formato falla

    # Si ha pasado un día, limpiar y actualizar el archivo
    if hoy > ultima_fecha:
        limpiar_registros_antiguos()
        with open(ruta_marcador, 'w') as f:
            f.write(hoy.isoformat())

@app.route('/recuperar-contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if request.method == 'POST':
        dni = request.form['dni']
        nueva_contrasena = request.form['nueva_contrasena']

        camionero = Camionero.query.filter_by(dni=dni).first()
        if camionero:
            camionero.set_password(nueva_contrasena)
            db.session.commit()
            flash('Contraseña actualizada correctamente.')
            return redirect(url_for('login_camionero'))
        else:
            flash('No se encontró un usuario con ese DNI.')

    return render_template('recuperar_contrasena.html')

import os

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)