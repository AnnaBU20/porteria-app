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

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///porteria.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

ULTRAMSG_INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID")
ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN")

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
            firma_path = os.path.join("static", "firmas", firma_filename)
            os.makedirs(os.path.dirname(firma_path), exist_ok=True)
            with open(firma_path, "wb") as f:
                f.write(firma_bytes)

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
        nuevo_registro.protocolo_filename = os.path.basename(protocolo_path)
        db.session.commit()

        return render_template('confirmacion.html', registro_id=nuevo_registro.id, protocolo_filename=nuevo_registro.protocolo_filename)

    return render_template('formulario.html')

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
    espacio_total = height - 2 * margen
    espacio_entre = espacio_total / 7

    qr_size = 25 * mm
    texto_x_offset = 30 * mm
    interlineado = 4

    for i in range(7):
        y = height - margen - (i * espacio_entre) - qr_size
        for columna in [0, 1]:
            codigo = str(uuid.uuid4())
            enlace = f"https://porteria-kr.onrender.com/registro_unico/{codigo}"
            db.session.add(QRUnico(codigo=codigo))

            qr_img = qrcode.make(enlace)
            qr_io = io.BytesIO()
            qr_img.save(qr_io, format='PNG')
            qr_io.seek(0)

            if columna == 0:
                x_qr = margen
                x_text = x_qr + qr_size + 5
            else:
                x_text = width - margen - 70 * mm
                x_qr = x_text + 50 * mm

            c.drawImage(ImageReader(qr_io), x_qr, y, width=qr_size, height=qr_size)
            c.setFont("Helvetica", 9)
            c.drawString(x_text, y + qr_size/2 + interlineado, "Escanee este código al llegar a Kronospan")
            c.drawString(x_text, y + qr_size/2 - interlineado, "para registrarse. Este QR es de un solo uso.")

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

@app.route('/exportar_registros_pdf')
@login_required
def exportar_registros_pdf():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    query = Registro.query
    if fecha_inicio and fecha_fin:
        query = query.filter(
            Registro.fecha >= datetime.strptime(fecha_inicio, "%Y-%m-%d").date(),
            Registro.fecha <= datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        )
    registros = query.all()
    pdf_buffer = generar_registro_pdf(registros)
    return send_file(pdf_buffer, as_attachment=True, download_name='registro_conductores.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)