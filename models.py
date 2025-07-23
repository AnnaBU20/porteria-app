from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo_operacion = db.Column(db.String(100), nullable=False)
    empresa = db.Column(db.String(100), nullable=False)
    matricula_tractora = db.Column(db.String(50), nullable=False)
    matricula_remolque = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(50), nullable=False)
    telefono = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    idioma = db.Column(db.String(10), nullable=False)
    protocolo_filename = db.Column(db.String(200))
    firma_filename = db.Column(db.String(200))
    hora_entrega = db.Column(db.Time, default=datetime.utcnow)