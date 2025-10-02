# app.py (sin SQLAlchemy, usando mysql.connector)
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash

from conexion.conexion import conexion, cerrar_conexion
from forms import ClienteForm, ProductoForm
from modelos.model_login import Usuario

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'   # En producción usa variable de entorno

# --- CSRF global ---
csrf = CSRFProtect(app)

# --- Flask-Login ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # adonde redirigir si no hay sesión

@login_manager.user_loader
def load_user(id_usuario: str):
    # Flask-Login guarda id_usuario como string
    try:
        return Usuario.obtener_por_id(int(id_usuario))
    except Exception:
        return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            print("\n--- DEBUG LOGIN ---")
            print("email:", repr(email))
            print("password_len:", len(password))

            user = Usuario.obtener_por_mail(email)
            if not user:
                print("user: None (no existe ese email en la DB)")
                flash('Credenciales inválidas. Inténtalo de nuevo.', 'danger')
                return render_template('login.html', title='Iniciar Sesión')

            print("user.id:", user.id_usuario if hasattr(user, 'id_usuario') else user.id)
            print("hash_prefix:", user.password_hash.split('$', 1)[0])  # ej: pbkdf2:sha256:600000

            from werkzeug.security import check_password_hash
            ok = check_password_hash(user.password_hash, password)
            print("check_password_hash:", ok)
            print("hash_len:", len(user.password_hash))

            if ok:
                login_user(user)
                flash('Has iniciado sesión correctamente.', 'success')
                return redirect(request.args.get('next') or url_for('index'))
            else:
                flash('Credenciales inválidas. Inténtalo de nuevo.', 'danger')

        except Exception:
            import traceback; traceback.print_exc()
            flash('Error al iniciar sesión (revisa la consola).', 'danger')

    return render_template('login.html', title='Iniciar Sesión')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre','').strip()
        email  = request.form.get('email','').strip().lower()
        password  = request.form.get('password','')
        password2 = request.form.get('password2','')

        print(password)

        if not nombre or not email or not password:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('registro.html', title='Registro', nombre=nombre, email=email)

        if password != password2:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('registro.html', title='Registro', nombre=nombre, email=email)

        if Usuario.obtener_por_mail(email):
            flash('El correo ya está registrado.', 'warning')
            return render_template('registro.html', title='Registro', nombre=nombre, email=email)

        # 👉 crea con PBKDF2:sha256:600000 gracias al modelo
        user = Usuario.crear_usuario(email=email, password_plano=password, nombre=nombre)
        if user:
            flash('Usuario creado. Ahora inicia sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash('No se pudo registrar.', 'danger')

    return render_template('registro.html', title='Registro')



# ========================================================================================================================
#  CONTEXTO / PÁGINAS BASE
# ========================================================================================================================
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

@app.route('/')
def index():
    return render_template('index.html', title='Inicio')

@app.route('/usuario/<nombre>')
@login_required
def usuario(nombre):
    return f'Bienvenido, {nombre}!'

@app.route('/about/')
def about():
    return render_template('about.html', title='Acerca de')

@app.route("/test_db")
def test_db():
    conn = conexion()
    if not conn:
        return "No se pudo conectar a la base de datos."

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE(), USER()")
        db_name, db_user = cursor.fetchone()
        return f"Conexión exitosa a la base de datos: {db_name} (usuario: {db_user})"
    except Exception as e:
        return f"Error ejecutando consulta: {str(e)}"
    finally:
        cerrar_conexion(conn)


# ========================================================================================================================
#  PRODUCTOS (CRUD)
# ========================================================================================================================
# Listar / Buscar
@app.route('/productos')
@login_required
def listar_productos():
    q = request.args.get('q', '').strip()
    conn = conexion()
    cur = conn.cursor(dictionary=True)
    try:
        if q:
            cur.execute(
                "SELECT id_producto, nombre, cantidad, precio FROM productos WHERE nombre LIKE %s",
                (f"%{q}%",)
            )
        else:
            cur.execute("SELECT id_producto, nombre, cantidad, precio FROM productos")
        productos = cur.fetchall()
        return render_template('products/list.html', title='Productos', productos=productos, q=q)
    finally:
        cur.close()
        cerrar_conexion(conn)

# Crear
@app.route('/productos/nuevo', methods=['GET', 'POST'])
@login_required
def crear_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        conn = conexion()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO productos (nombre, cantidad, precio) VALUES (%s, %s, %s)",
                (form.nombre.data.strip(), form.cantidad.data, float(form.precio.data))
            )
            conn.commit()
            flash('Producto agregado correctamente.', 'success')
            return redirect(url_for('listar_productos'))
        except Exception as e:
            conn.rollback()
            form.nombre.errors.append('No se pudo guardar: ' + str(e))
        finally:
            cur.close()
            cerrar_conexion(conn)
    return render_template('products/form.html', title='Nuevo producto', form=form, modo='crear')

# Editar
@app.route('/productos/<int:pid>/editar', methods=['GET', 'POST'])
@login_required
def editar_producto(pid):
    conn = conexion()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id_producto, nombre, cantidad, precio FROM productos WHERE id_producto = %s", (pid,))
        prod = cur.fetchone()
        if not prod:
            flash('Producto no encontrado.', 'warning')
            return redirect(url_for('listar_productos'))

        form = ProductoForm(data={'nombre': prod['nombre'], 'cantidad': prod['cantidad'], 'precio': prod['precio']})

        if form.validate_on_submit():
            nombre = form.nombre.data.strip()
            cantidad = form.cantidad.data
            precio = float(form.precio.data)
            cur2 = conn.cursor()
            try:
                cur2.execute(
                    "UPDATE productos SET nombre=%s, cantidad=%s, precio=%s WHERE id_producto=%s",
                    (nombre, cantidad, precio, pid)
                )
                conn.commit()
                flash('Producto actualizado correctamente.', 'success')
                return redirect(url_for('listar_productos'))
            except Exception as e:
                conn.rollback()
                form.nombre.errors.append('Error al actualizar: ' + str(e))
            finally:
                cur2.close()

        return render_template('products/form.html', title='Editar producto', form=form, modo='editar', pid=pid)
    finally:
        cur.close()
        cerrar_conexion(conn)

# Eliminar
@app.route('/productos/<int:pid>/eliminar', methods=['POST'])
@login_required
def eliminar_producto(pid):
    conn = conexion()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM productos WHERE id_producto = %s", (pid,))
        if cur.rowcount > 0:
            conn.commit()
            flash('Producto eliminado correctamente.', 'success')
        else:
            flash('Producto no encontrado.', 'warning')
        return redirect(url_for('listar_productos'))
    finally:
        cur.close()
        cerrar_conexion(conn)

# ========================================================================================================================
#  CLIENTES (CRUD)
# ========================================================================================================================

# Listar / Buscar
@app.route('/clientes')
@login_required
def listar_clientes():
    q = request.args.get('q', '').strip()
    conn = conexion()
    cur = conn.cursor(dictionary=True)
    try:
        if q:
            cur.execute(
                "SELECT id_cliente, nombre, apellido, email, telefono, direccion, fecha_registro "
                "FROM clientes WHERE nombre LIKE %s OR apellido LIKE %s OR email LIKE %s",
                (f"%{q}%", f"%{q}%", f"%{q}%")
            )
        else:
            cur.execute("SELECT id_cliente, nombre, apellido, email, telefono, direccion, fecha_registro FROM clientes")
        clientes = cur.fetchall()
        return render_template('clientes/list.html', title='Clientes', clientes=clientes, q=q)
    finally:
        cur.close()
        cerrar_conexion(conn)


# Crear
@app.route('/clientes/nuevo', methods=['GET', 'POST'])
@login_required
def crear_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        conn = conexion()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO clientes (nombre, apellido, email, telefono, direccion) VALUES (%s, %s, %s, %s, %s)",
                (form.nombre.data.strip(),
                 form.apellido.data.strip(),
                 form.email.data.strip(),
                 form.telefono.data.strip() if form.telefono.data else None,
                 form.direccion.data.strip() if form.direccion.data else None)
            )
            conn.commit()
            flash('Cliente agregado correctamente.', 'success')
            return redirect(url_for('listar_clientes'))
        except Exception as e:
            conn.rollback()
            form.nombre.errors.append('No se pudo guardar: ' + str(e))
        finally:
            cur.close()
            cerrar_conexion(conn)
    return render_template('clientes/form.html', title='Nuevo cliente', form=form, modo='crear')


# Editar
@app.route('/clientes/<int:cid>/editar', methods=['GET', 'POST'])
@login_required
def editar_cliente(cid):
    conn = conexion()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM clientes WHERE id_cliente = %s", (cid,))
        cli = cur.fetchone()
        if not cli:
            flash('Cliente no encontrado.', 'warning')
            return redirect(url_for('listar_clientes'))

        form = ClienteForm(data={
            'nombre': cli['nombre'],
            'apellido': cli['apellido'],
            'email': cli['email'],
            'telefono': cli['telefono'],
            'direccion': cli['direccion']
        })

        if form.validate_on_submit():
            conn2 = conexion()
            cur2 = conn2.cursor()
            try:
                cur2.execute(
                    "UPDATE clientes SET nombre=%s, apellido=%s, email=%s, telefono=%s, direccion=%s WHERE id_cliente=%s",
                    (form.nombre.data.strip(),
                     form.apellido.data.strip(),
                     form.email.data.strip(),
                     form.telefono.data.strip() if form.telefono.data else None,
                     form.direccion.data.strip() if form.direccion.data else None,
                     cid)
                )
                conn2.commit()
                flash('Cliente actualizado correctamente.', 'success')
                return redirect(url_for('listar_clientes'))
            except Exception as e:
                conn2.rollback()
                form.nombre.errors.append('Error al actualizar: ' + str(e))
            finally:
                cur2.close()
                cerrar_conexion(conn2)

        return render_template('clientes/form.html', title='Editar cliente', form=form, modo='editar', cid=cid)
    finally:
        cur.close()
        cerrar_conexion(conn)


# Eliminar
@app.route('/clientes/<int:cid>/eliminar', methods=['POST'])
@login_required
def eliminar_cliente(cid):
    conn = conexion()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM clientes WHERE id_cliente = %s", (cid,))
        if cur.rowcount > 0:
            conn.commit()
            flash('Cliente eliminado correctamente.', 'success')
        else:
            flash('Cliente no encontrado.', 'warning')
        return redirect(url_for('listar_clientes'))
    finally:
        cur.close()
        cerrar_conexion(conn)

# Listar facturas
@app.route('/facturas')
@login_required
def listar_facturas():
    conn = conexion()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT f.id_factura, f.fecha, f.subtotal, f.iva, f.total, f.estado,
                   c.nombre, c.apellido
            FROM facturas f
            JOIN clientes c ON f.id_cliente = c.id_cliente
            ORDER BY f.fecha DESC
        """)
        facturas = cur.fetchall()
        return render_template('facturas/list.html', facturas=facturas)
    finally:
        cur.close()
        cerrar_conexion(conn)


# Crear factura
@app.route('/facturas/nueva', methods=['GET', 'POST'])
@login_required
def crear_factura():
    conn = conexion()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_cliente = request.form['id_cliente']
        productos = request.form.getlist('productos[]')
        cantidades = request.form.getlist('cantidades[]')

        try:
            # Calcular totales
            subtotal = 0
            detalle = []
            for pid, cant in zip(productos, cantidades):
                cur.execute("SELECT precio FROM productos WHERE id_producto=%s", (pid,))
                prod = cur.fetchone()
                precio = float(prod['precio'])
                cantidad = int(cant)
                st = precio * cantidad
                subtotal += st
                detalle.append((pid, cantidad, precio, st))

            iva = subtotal * 0.12
            total = subtotal + iva

            # Insertar factura
            cur.execute("INSERT INTO facturas (id_cliente, subtotal, iva, total, estado) VALUES (%s,%s,%s,%s,%s)",
                        (id_cliente, subtotal, iva, total, 'PAGADA'))
            id_factura = cur.lastrowid

            # Insertar detalle
            for pid, cantidad, precio, st in detalle:
                cur.execute("""INSERT INTO factura_detalle 
                               (id_factura, id_producto, cantidad, precio_unitario, subtotal)
                               VALUES (%s,%s,%s,%s,%s)""",
                            (id_factura, pid, cantidad, precio, st))
                # Actualizar stock
                cur.execute("UPDATE productos SET cantidad = cantidad - %s WHERE id_producto=%s", (cantidad, pid))

            conn.commit()
            flash('Factura registrada correctamente ✅', 'success')
            return redirect(url_for('listar_facturas'))

        except Exception as e:
            conn.rollback()
            flash(f'Error al registrar la factura: {str(e)}', 'danger')

    # GET: mostrar formulario
    cur.execute("SELECT * FROM clientes ORDER BY nombre")
    clientes = cur.fetchall()
    cur.execute("SELECT * FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    cerrar_conexion(conn)
    return render_template('facturas/form.html', clientes=clientes, productos=productos)

@app.route('/facturas/<int:fid>/eliminar', methods=['POST'])
@login_required
def eliminar_factura(fid):
    conn = conexion()
    cur = conn.cursor()
    try:
        # Primero eliminar detalle
        cur.execute("DELETE FROM factura_detalle WHERE id_factura = %s", (fid,))
        # Luego eliminar la factura
        cur.execute("DELETE FROM facturas WHERE id_factura = %s", (fid,))
        if cur.rowcount > 0:
            conn.commit()
            flash(f'Factura #{fid} eliminada correctamente ✅', 'success')
        else:
            flash('Factura no encontrada ⚠️', 'warning')
    except Exception as e:
        conn.rollback()
        flash(f'Error al eliminar factura: {str(e)}', 'danger')
    finally:
        cur.close()
        cerrar_conexion(conn)

    return redirect(url_for('listar_facturas'))


# Ver detalle de factura
@app.route('/facturas/<int:fid>')
@login_required
def detalle_factura(fid):
    conn = conexion()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT f.*, c.nombre, c.apellido, c.email 
            FROM facturas f
            JOIN clientes c ON f.id_cliente = c.id_cliente
            WHERE f.id_factura=%s
        """, (fid,))
        factura = cur.fetchone()

        cur.execute("""
            SELECT d.*, p.nombre 
            FROM factura_detalle d
            JOIN productos p ON d.id_producto = p.id_producto
            WHERE d.id_factura=%s
        """, (fid,))
        detalle = cur.fetchall()

        return render_template('facturas/detalle.html', factura=factura, detalle=detalle)
    finally:
        cur.close()
        cerrar_conexion(conn)

# ========================
#  MAIN
# ========================
if __name__ == '__main__':
    app.run(debug=True)
