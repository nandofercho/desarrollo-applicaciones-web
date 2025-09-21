from flask import Flask, render_template, redirect, url_for, flash, request
from datetime import datetime
from models import db, Producto, Usuario
from forms import ProductoForm, UsuarioForm
from inventory import Inventario
from conexion.conexion import conexion, cerrar_conexion

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:password@127.0.0.1:3306/inventario?charset=utf8mb4"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev-secret-key"

db.init_app(app)

# Para usar {{ now().year }} en templates
@app.context_processor
def inject_now():
    return {"now": datetime.utcnow}

# ------- Inicialización al arrancar la app -------
inventario = None 

with app.app_context():
    db.create_all()
    inventario = Inventario.cargar_desde_bd()

def get_inventario():
    global inventario
    if inventario is None:
        with app.app_context():
            db.create_all()
            inventario = Inventario.cargar_desde_bd()
    return inventario

# --------------------------------------------------
@app.route("/test_db")
def test_db():
    conn = conexion()
    if not conn:
        return "❌ No se pudo conectar a la base de datos."

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE(), USER()")
        db_name, db_user = cursor.fetchone()
        return f"✅ Conexión exitosa a la base de datos: {db_name} (usuario: {db_user})"
    except Exception as e:
        return f"❌ Error ejecutando consulta: {str(e)}"
    finally:
        cerrar_conexion(conn)

@app.route("/")
def index():
    return render_template("index.html", title="Inicio")

@app.route("/usuario/<nombre>")
def usuario(nombre):
    return f"Bienvenido, {nombre}!"

@app.route("/about/")
def about():
    return render_template("about.html", title="Acerca de")

# -------------------------------- RUTAS PRODUCTOS --------------------------------
@app.route("/productos")
def listar_productos():
    q = request.args.get("q", "").strip()
    inv = get_inventario()
    productos = inv.buscar_por_nombre_producto(q) if q else inv.listar_producto()
    return render_template("products/list.html", title="Productos", productos=productos, q=q)

@app.route("/productos/nuevo", methods=["GET", "POST"])
def crear_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        try:
            get_inventario().agregar_producto(
                nombre=form.nombre.data,
                cantidad=form.cantidad.data,
                precio=form.precio.data,
            )
            flash("Producto agregado correctamente.", "success")
            return redirect(url_for("listar_productos"))
        except ValueError as e:
            form.nombre.errors.append(str(e))
    return render_template("products/form.html", title="Nuevo producto", form=form, modo="crear")

@app.route("/productos/<int:id>/editar", methods=["GET", "POST"])
def editar_producto(id):
    prod = Producto.query.get_or_404(id)
    form = ProductoForm(obj=prod)
    if form.validate_on_submit():
        try:
            get_inventario().actualizar_producto(
                id_producto=id,
                nombre=form.nombre.data,
                cantidad=form.cantidad.data,
                precio=form.precio.data,
            )
            flash("Producto actualizado.", "success")
            return redirect(url_for("listar_productos"))
        except ValueError as e:
            form.nombre.errors.append(str(e))
    return render_template("products/form.html", title="Editar producto", form=form, modo="editar")

@app.route("/productos/<int:id>/eliminar", methods=["POST"])
def eliminar_producto(id):
    ok = get_inventario().eliminar_producto(id)
    flash("Producto eliminado." if ok else "Producto no encontrado.", "info" if ok else "warning")
    return redirect(url_for("listar_productos"))


# -------------------------------- RUTAS USUARIOS --------------------------------
@app.route("/usuarios")
def listar_usuarios():
    q = request.args.get("q", "").strip()
    inv = get_inventario()
    usuarios = inv.buscar_por_nombre_usuario(q) if q else inv.listar_usuario()
    return render_template("users/list.html", title="Usuarios", usuarios=usuarios, q=q)

@app.route("/usuarios/nuevo", methods=["GET", "POST"])
def crear_usuario():
    form = UsuarioForm()
    if form.validate_on_submit():
        try:
            get_inventario().agregar_usuario(
                nombre=form.nombre.data,
                email=form.email.data,
            )
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("listar_usuarios"))
        except ValueError as e:
            # choque por email único u otra validación
            form.email.errors.append(str(e))
    return render_template("users/form.html", title="Nuevo usuario", form=form, modo="crear")

@app.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
def editar_usuario(id):
    u = Usuario.query.get_or_404(id)
    form = UsuarioForm(obj=u)
    if form.validate_on_submit():
        try:
            get_inventario().actualizar_usuario(
                id_usuario=id,
                nombre=form.nombre.data,
                email=form.email.data,
            )
            flash("Usuario actualizado.", "success")
            return redirect(url_for("listar_usuarios"))
        except ValueError as e:
            form.email.errors.append(str(e))
    return render_template("users/form.html", title="Editar usuario", form=form, modo="editar")

@app.route("/usuarios/<int:id>/eliminar", methods=["POST"])
def eliminar_usuario(id):
    ok = get_inventario().eliminar_usuario(id)
    flash("Usuario eliminado." if ok else "Usuario no encontrado.", "info" if ok else "warning")
    return redirect(url_for("listar_usuarios"))

if __name__ == "__main__":
    app.run(debug=True)
