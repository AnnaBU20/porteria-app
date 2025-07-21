from flask import Flask, render_template, request, redirect, url_for, flash, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
import io
import base64
import re
import qrcode
import uuid
import pywhatkit as kit
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from anadir_info_pdf import generar_protocolo_desde_plantilla
from generar_registro_conductores_pdf import generar_registro_pdf
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///porteria.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo_operacion = db.Column(db.String(50), nullable=False)
    empresa = db.Column(db.String(100), nullable=False)
    matricula_tractora = db.Column(db.String(20), nullable=False)
    matricula_remolque = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    fecha = db.Column(db.Date, nullable=False)
    hora_entrega = db.Column(db.DateTime, default=datetime.utcnow)
    acepta = db.Column(db.Boolean, nullable=False)
    proteccion_datos = db.Column(db.Boolean, nullable=False)
    idioma = db.Column(db.String(10), nullable=False)
    firma_filename = db.Column(db.String(200), nullable=True)
    protocolo_filename = db.Column(db.String(200), nullable=True)
    estado = db.Column(db.String(20), nullable=False, default="esperando")

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

@login_manager.user_loader
def load_user(user_id):
    if user_id == "1":
        return Usuario()
    return None

@app.route('/', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        tipo_operacion = request.form['tipo_operacion']
        empresa = request.form['empresa']
        matricula_tractora = request.form['matricula_tractora']
        matricula_remolque = request.form['matricula_remolque']
        nombre = request.form['nombre']
        dni = request.form['dni']
        telefono = request.form['telefono']
        fecha_str = request.form['fecha']
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        idioma = request.form['idioma']

        acepta = 'acepta' in request.form
        proteccion_datos = 'proteccion_datos' in request.form

        if not acepta or not proteccion_datos:
            flash("Debe aceptar las condiciones de seguridad y la política de protección de datos.")
            return redirect(url_for('formulario'))

        firma_data = request.form['firma_base64']
        match = re.match(r'data:image/png;base64,(.*)', firma_data)
        if match:
            firma_bytes = base64.b64decode(match.group(1))
            firma_filename = f"{nombre}_{dni}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            firma_path = os.path.join("static", "firmas", firma_filename)
            os.makedirs(os.path.dirname(firma_path), exist_ok=True)
            with open(firma_path, "wb") as f:
                f.write(firma_bytes)
        else:
            firma_filename = None

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
            firma_filename=firma_filename
        )

        db.session.add(nuevo_registro)
        db.session.commit()

        protocolo_path = generar_protocolo_desde_plantilla(nuevo_registro)
        print("PDF generado en:", protocolo_path)

        nuevo_registro.protocolo_filename = os.path.basename(protocolo_path)
        db.session.commit()

        return render_template(
            'confirmacion.html',
            registro_id=nuevo_registro.id,
            protocolo_filename=nuevo_registro.protocolo_filename
        )

    return render_template('formulario.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == "porteria" and password == "porteria123":
            user = Usuario()
            login_user(user)
            return redirect(url_for('registros'))
        else:
            flash("Credenciales incorrectas.")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/registros', methods=['GET'])
@login_required
def registros():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    query = Registro.query
    if fecha_inicio and fecha_fin:
        fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        query = query.filter(Registro.fecha >= fecha_inicio_obj, Registro.fecha <= fecha_fin_obj)

    registros = query.all()
    return render_template('registros.html', registros=registros)

@app.route('/panel-control')
@login_required
def panel_control():
    registros = Registro.query.order_by(Registro.hora_entrega.desc()).all()
    return render_template('panel_control.html', registros=registros)

@app.route('/descargar_protocolo/<int:registro_id>')
def descargar_protocolo(registro_id):
    registro = Registro.query.get_or_404(registro_id)
    if registro.protocolo_filename:
        ruta = os.path.join("pdfs", registro.protocolo_filename)
        return send_file(ruta, as_attachment=True)
    else:
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

@app.route('/exportar_registros_pdf')
@login_required
def exportar_registros_pdf():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    query = Registro.query
    if fecha_inicio and fecha_fin:
        fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        query = query.filter(Registro.fecha >= fecha_inicio_obj, Registro.fecha <= fecha_fin_obj)

    registros_filtrados = query.all()
    pdf_buffer = generar_registro_pdf(registros_filtrados)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name='registro_conductores.pdf',
        mimetype='application/pdf'
    )

@app.route('/actualizar_estado/<int:registro_id>', methods=['POST'])
@login_required
def actualizar_estado(registro_id):
    nuevo_estado = request.form.get('nuevo_estado')
    registro = Registro.query.get_or_404(registro_id)
    registro.estado = nuevo_estado
    db.session.commit()

    if nuevo_estado == "dentro" and registro.telefono:
        mensaje = f"Buenos días {registro.nombre}, ya puede subir a báscula e ingresar a portería. Gracias por su paciencia."
        hora = datetime.now().hour
        minuto = datetime.now().minute + 1
        try:
            kit.sendwhatmsg(f"+34{registro.telefono}", mensaje, hora, minuto, wait_time=10, tab_close=True)
        except Exception as e:
            print("Error al enviar WhatsApp:", e)

    return redirect(url_for('panel_control'))

@app.route('/eliminar_registro/<int:registro_id>', methods=['POST'])
@login_required
def eliminar_registro(registro_id):
    registro = Registro.query.get_or_404(registro_id)
    db.session.delete(registro)
    db.session.commit()
    flash("Registro eliminado correctamente.")
    return redirect(url_for('panel_control'))

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
            link = f"http://127.0.0.1:5000/registro_unico/{codigo_unico}""

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

@app.route('/qr_lote')
@login_required
def qr_lote():
    return render_template('qr_lote.html')

@app.route('/registro_unico/<codigo>', methods=['GET'])
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

if __name__ == '__main__':
    app.run(debug=True)