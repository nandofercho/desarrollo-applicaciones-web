from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Producto(db.Model):
    __tablename__ = 'productos'
    id_producto = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=0)
    precio = db.Column(db.Float, nullable=False, default=0.0)

    def __repr__(self):
        return f'<Producto {self.id_producto} {self.nombre}>'

    def to_tuple(self):
        # ejemplo de tupla: (id_producto, nombre, cantidad, precio)
        return (self.id_producto, self.nombre, self.cantidad, self.precio)

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<Usuario {self.id_usuario} {self.nombre}>'

    def to_tuple(self):
        # ejemplo de tupla: (id_usuario, nombre, email)
        return (self.id_usuario, self.nombre, self.email)
