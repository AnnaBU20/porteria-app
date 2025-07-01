from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
import io
import base64
import re
from anadir_info_pdf import generar_protocolo_desde_plantilla
from pdf_generador import generar_pdf

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
    fecha = db.Column(db.Date, nullable=False)
    hora_entrega = db.Column(db.DateTime, default=datetime.utcnow)
    acepta = db.Column(db.Boolean, nullable=False)
    proteccion_datos = db.Column(db.Boolean, nullable=False)
    idioma = db.Column(db.String(10), nullable=False)
    firma_filename = db.Column(db.String(200), nullable=True)
    protocolo_filename = db.Column(db.String(200), nullable=True)

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
    return render_template(
    'confirmacion.html',
    protocolo_filename=nuevo_registro.protocolo_filename,
    registro_id=nuevo_registro.id
)

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

@app.route('/descargar_protocolo/<int:registro_id>')
def descargar_protocolo(registro_id):
    registro = Registro.query.get_or_404(registro_id)
    if registro.protocolo_filename:
        ruta = os.path.join("pdfs", registro.protocolo_filename)
        return send_file(ruta, as_attachment=True)
    else:
        flash("Este registro no tiene protocolo generado.")
        return redirect(url_for('registros'))

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
    pdf_buffer = generar_pdf(registros_filtrados)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name='registros.pdf',
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)