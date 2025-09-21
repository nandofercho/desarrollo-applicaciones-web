# inventory.py
from sqlalchemy.exc import IntegrityError
from models import db, Producto, Usuario

class Inventario:
    """
    - Cache en memoria:
        productos: dict[int, Producto]
        usuarios:  dict[int, Usuario]
    - Validaciones rápidas:
        nombres_productos: set[str] (lower)
        emails_usuarios:   set[str] (lower)
    """
    def __init__(self, productos_dict=None, usuarios_dict=None):
        # Productos
        self.productos = productos_dict or {}  # dict[int, Producto]
        self.nombres_productos = set(p.nombre.lower() for p in self.productos.values())

        # Usuarios
        self.usuarios = usuarios_dict or {}   # dict[int, Usuario]
        self.emails_usuarios = set(u.email.lower() for u in self.usuarios.values())

    @classmethod
    def cargar_desde_bd(cls):
        # Productos
        productos = Producto.query.all()
        productos_dict = {p.id_producto: p for p in productos}

        # Usuarios
        usuarios = Usuario.query.all()
        usuarios_dict = {u.id_usuario: u for u in usuarios}

        return cls(productos_dict=productos_dict, usuarios_dict=usuarios_dict)

    # ========================================================================================================
    # CRUD PRODUCTO
    # ========================================================================================================
    def agregar_producto(self, nombre: str, cantidad: int, precio: float) -> Producto:
        nombre_l = nombre.strip().lower()
        if nombre_l in self.nombres_productos:
            raise ValueError('Ya existe un producto con ese nombre.')
        p = Producto(nombre=nombre.strip(), cantidad=int(cantidad), precio=float(precio))
        try:
            db.session.add(p)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # por si el unique del modelo salta
            raise ValueError('Ya existe un producto con ese nombre (DB).')

        self.productos[p.id_producto] = p
        self.nombres_productos.add(nombre_l)
        return p

    def eliminar_producto(self, id_producto: int) -> bool:
        p = self.productos.get(id_producto) or Producto.query.get(id_producto)
        if not p:
            return False
        nombre_l = p.nombre.lower()
        try:
            db.session.delete(p)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('No se pudo eliminar el producto (restricción de integridad).')

        self.productos.pop(id_producto, None)
        self.nombres_productos.discard(nombre_l)
        return True

    def actualizar_producto(self, id_producto: int, nombre=None, cantidad=None, precio=None) -> Producto | None:
        p = self.productos.get(id_producto) or Producto.query.get(id_producto)
        if not p:
            return None

        old_nombre_l = p.nombre.lower()

        if nombre is not None:
            nuevo = nombre.strip()
            nuevo_l = nuevo.lower()
            if nuevo_l != old_nombre_l and nuevo_l in self.nombres_productos:
                raise ValueError('Ya existe otro producto con ese nombre.')
            p.nombre = nuevo

        if cantidad is not None:
            p.cantidad = int(cantidad)

        if precio is not None:
            p.precio = float(precio)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('No se pudo actualizar el producto (único/DB).')

        # Actualizar cache/sets
        self.productos[p.id_producto] = p
        if nombre is not None:
            self.nombres_productos.discard(old_nombre_l)
            self.nombres_productos.add(p.nombre.lower())
        return p

    # Consultas PRODUCTO (cache)
    def buscar_por_nombre_producto(self, q: str):
        q = q.lower()
        return sorted(
            [p for p in self.productos.values() if q in p.nombre.lower()],
            key=lambda x: x.nombre
        )

    def listar_producto(self):
        return sorted(self.productos.values(), key=lambda x: x.nombre)

    # ========================================================================================================
    # CRUD USUARIO
    # ========================================================================================================
    def agregar_usuario(self, nombre: str, email: str) -> Usuario:
        email_l = email.strip().lower()
        if email_l in self.emails_usuarios:
            raise ValueError('Ya existe un usuario con ese email.')
        u = Usuario(nombre=nombre.strip(), email=email.strip())
        try:
            db.session.add(u)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # por si el unique del modelo salta
            raise ValueError('Ya existe un usuario con ese email (DB).')

        self.usuarios[u.id_usuario] = u
        self.emails_usuarios.add(email_l)
        return u

    def eliminar_usuario(self, id_usuario: int) -> bool:
        u = self.usuarios.get(id_usuario) or Usuario.query.get(id_usuario)
        if not u:
            return False
        email_l = u.email.lower()
        try:
            db.session.delete(u)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('No se pudo eliminar el usuario (restricción de integridad).')

        self.usuarios.pop(id_usuario, None)
        self.emails_usuarios.discard(email_l)
        return True

    def actualizar_usuario(self, id_usuario: int, nombre: str | None = None, email: str | None = None) -> Usuario | None:
        u = self.usuarios.get(id_usuario) or Usuario.query.get(id_usuario)
        if not u:
            return None

        old_email_l = u.email.lower()

        if nombre is not None:
            u.nombre = nombre.strip()

        if email is not None:
            nuevo_email = email.strip()
            nuevo_email_l = nuevo_email.lower()
            if nuevo_email_l != old_email_l and nuevo_email_l in self.emails_usuarios:
                raise ValueError('Ya existe otro usuario con ese email.')
            u.email = nuevo_email

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('No se pudo actualizar el usuario (único/DB).')

        # Actualizar cache/sets
        self.usuarios[u.id_usuario] = u
        if email is not None:
            self.emails_usuarios.discard(old_email_l)
            self.emails_usuarios.add(u.email.lower())
        return u

    # Consultas USUARIO (cache)
    def buscar_por_nombre_usuario(self, q: str):
        q = q.lower()
        return sorted(
            [u for u in self.usuarios.values() if q in u.nombre.lower()],
            key=lambda x: x.nombre
        )

    def listar_usuario(self):
        return sorted(self.usuarios.values(), key=lambda x: x.nombre)
