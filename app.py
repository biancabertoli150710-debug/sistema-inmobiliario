from flask import Flask, render_template, request, redirect, session, flash
import os
import sqlite3
import urllib.request
import json
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'clave_secreta_inmobiliaria_2024'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'inmobiliaria.db')
API_KEY = os.getenv('OPENROUTER_API_KEY')


# ----------------- BASE DE DATOS -----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            telefono TEXT,
            rol TEXT DEFAULT 'cliente'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS propiedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            ciudad TEXT NOT NULL,
            direccion TEXT NOT NULL,
            tipo TEXT NOT NULL,
            operacion TEXT NOT NULL,
            habitaciones INTEGER NOT NULL,
            precio TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            imagen TEXT NOT NULL,
            latitud REAL,
            longitud REAL,
            estado TEXT DEFAULT 'Disponible',
            vistas INTEGER DEFAULT 0,
            usuario_id INTEGER,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS imagenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            propiedad_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            FOREIGN KEY (propiedad_id) REFERENCES propiedades(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            tipo_busca TEXT,
            presupuesto TEXT,
            notas TEXT,
            asesor_id INTEGER,
            FOREIGN KEY (asesor_id) REFERENCES usuarios(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            propiedad_id INTEGER NOT NULL,
            cliente_id INTEGER NOT NULL,
            asesor_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            notas TEXT,
            estado TEXT DEFAULT 'Pendiente',
            FOREIGN KEY (propiedad_id) REFERENCES propiedades(id),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (asesor_id) REFERENCES usuarios(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favoritos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            propiedad_id INTEGER NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (propiedad_id) REFERENCES propiedades(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            propiedad_id INTEGER NOT NULL,
            cliente_id INTEGER NOT NULL,
            pregunta TEXT NOT NULL,
            respuesta TEXT,
            fecha TEXT NOT NULL,
            FOREIGN KEY (propiedad_id) REFERENCES propiedades(id),
            FOREIGN KEY (cliente_id) REFERENCES usuarios(id)
        )
    ''')

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn.commit()
    conn.close()


# ----------------- HELPERS -----------------

def usuario_logueado():
    return 'usuario' in session

def es_asesor():
    return session.get('rol') == 'asesor'

def es_cliente():
    return session.get('rol') == 'cliente'


# ----------------- RUTAS PRINCIPALES -----------------

@app.route('/')
def inicio():
    conn = get_db()
    total_propiedades = conn.execute("SELECT COUNT(*) FROM propiedades").fetchone()[0]
    total_usuarios = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    total_venta = conn.execute("SELECT COUNT(*) FROM propiedades WHERE operacion='Venta'").fetchone()[0]
    total_alquiler = conn.execute("SELECT COUNT(*) FROM propiedades WHERE operacion='Alquiler'").fetchone()[0]
    conn.close()
    return render_template("index.html",
        total_propiedades=total_propiedades,
        total_usuarios=total_usuarios,
        total_venta=total_venta,
        total_alquiler=total_alquiler
    )


@app.route('/propiedades')
def ver_propiedades():
    query = request.args.get('q', '')
    tipo = request.args.get('tipo', '')
    operacion = request.args.get('operacion', '')
    orden = request.args.get('orden', '')

    sql = "SELECT * FROM propiedades WHERE 1=1"
    params = []

    if query:
        sql += " AND (LOWER(nombre) LIKE ? OR LOWER(ciudad) LIKE ?)"
        params.extend([f'%{query.lower()}%', f'%{query.lower()}%'])

    if tipo:
        sql += " AND tipo = ?"
        params.append(tipo)

    if operacion:
        sql += " AND operacion = ?"
        params.append(operacion)

    if orden == 'asc':
        sql += " ORDER BY CAST(REPLACE(REPLACE(precio, ',', ''), '.', '') AS INTEGER) ASC"
    elif orden == 'desc':
        sql += " ORDER BY CAST(REPLACE(REPLACE(precio, ',', ''), '.', '') AS INTEGER) DESC"

    conn = get_db()
    propiedades = conn.execute(sql, params).fetchall()

    favoritos_ids = []
    if usuario_logueado():
        usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
        favs = conn.execute("SELECT propiedad_id FROM favoritos WHERE usuario_id = ?", (usuario['id'],)).fetchall()
        favoritos_ids = [f['propiedad_id'] for f in favs]

    conn.close()
    return render_template("propiedades.html", propiedades=propiedades, favoritos_ids=favoritos_ids)


@app.route('/propiedad/<int:id>')
def detalle(id):
    conn = get_db()
    prop = conn.execute("SELECT * FROM propiedades WHERE id = ?", (id,)).fetchone()
    vendedor = None
    es_favorito = False
    imagenes = []
    consultas = []
    if prop:
        conn.execute("UPDATE propiedades SET vistas = vistas + 1 WHERE id = ?", (id,))
        conn.commit()
        vendedor = conn.execute("SELECT nombre, telefono FROM usuarios WHERE id = ?", (prop['usuario_id'],)).fetchone()
        imagenes = conn.execute("SELECT nombre FROM imagenes WHERE propiedad_id = ?", (id,)).fetchall()
        if usuario_logueado():
            usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
            fav = conn.execute("SELECT id FROM favoritos WHERE usuario_id = ? AND propiedad_id = ?", (usuario['id'], id)).fetchone()
            es_favorito = fav is not None
            consultas = conn.execute(
                "SELECT * FROM consultas WHERE propiedad_id = ? AND cliente_id = ? ORDER BY id DESC",
                (id, usuario['id'])
            ).fetchall()
        prop = conn.execute("SELECT * FROM propiedades WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not prop:
        flash('Propiedad no encontrada.', 'error')
        return redirect('/propiedades')
    return render_template("detalle.html", prop=prop, vendedor=vendedor, es_favorito=es_favorito, imagenes=imagenes, consultas=consultas)


@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if not usuario_logueado():
        flash('Debes iniciar sesión para agregar propiedades.', 'warning')
        return redirect('/login')

    if not es_asesor():
        flash('Solo los asesores pueden agregar propiedades.', 'error')
        return redirect('/propiedades')

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        ciudad = request.form.get('ciudad')
        direccion = request.form.get('direccion')
        tipo = request.form.get('tipo')
        operacion = request.form.get('operacion')
        habitaciones = request.form.get('habitaciones')
        precio = request.form.get('precio')
        descripcion = request.form.get('descripcion')
        latitud = request.form.get('latitud') or None
        longitud = request.form.get('longitud') or None

        imagenes = request.files.getlist('imagenes')
        nombre_imagen_principal = None

        conn = get_db()
        usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()

        for i, imagen in enumerate(imagenes):
            if imagen and imagen.filename:
                nombre_imagen = secure_filename(imagen.filename)
                imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_imagen))
                if i == 0:
                    nombre_imagen_principal = nombre_imagen

        if not nombre_imagen_principal:
            flash('Debes subir al menos una imagen.', 'error')
            return render_template("agregar_propiedad.html")

        conn.execute(
            "INSERT INTO propiedades (nombre, ciudad, direccion, tipo, operacion, habitaciones, precio, descripcion, imagen, latitud, longitud, estado, usuario_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nombre, ciudad, direccion, tipo, operacion, habitaciones, precio, descripcion, nombre_imagen_principal, latitud, longitud, 'Disponible', usuario['id'])
        )
        propiedad_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for imagen in imagenes:
            if imagen and imagen.filename:
                nombre_imagen = secure_filename(imagen.filename)
                conn.execute("INSERT INTO imagenes (propiedad_id, nombre) VALUES (?, ?)", (propiedad_id, nombre_imagen))

        conn.commit()
        conn.close()

        flash('Propiedad agregada exitosamente.', 'success')
        return redirect('/propiedades')

    return render_template("agregar_propiedad.html")


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if not usuario_logueado():
        flash('Debes iniciar sesión para editar propiedades.', 'warning')
        return redirect('/login')

    if not es_asesor():
        flash('Solo los asesores pueden editar propiedades.', 'error')
        return redirect('/propiedades')

    conn = get_db()
    prop = conn.execute("SELECT * FROM propiedades WHERE id = ?", (id,)).fetchone()

    if not prop:
        flash('Propiedad no encontrada.', 'error')
        return redirect('/propiedades')

    usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
    if prop['usuario_id'] != usuario['id']:
        flash('No tienes permiso para editar esta propiedad.', 'error')
        return redirect('/propiedades')

    imagenes = conn.execute("SELECT * FROM imagenes WHERE propiedad_id = ?", (id,)).fetchall()

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        ciudad = request.form.get('ciudad')
        direccion = request.form.get('direccion')
        tipo = request.form.get('tipo')
        operacion = request.form.get('operacion')
        habitaciones = request.form.get('habitaciones')
        precio = request.form.get('precio')
        descripcion = request.form.get('descripcion')
        latitud = request.form.get('latitud') or None
        longitud = request.form.get('longitud') or None
        estado = request.form.get('estado', 'Disponible')

        nuevas_imagenes = request.files.getlist('imagenes')
        for imagen in nuevas_imagenes:
            if imagen and imagen.filename:
                nombre_imagen = secure_filename(imagen.filename)
                imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_imagen))
                conn.execute("INSERT INTO imagenes (propiedad_id, nombre) VALUES (?, ?)", (id, nombre_imagen))
                conn.execute("UPDATE propiedades SET imagen = ? WHERE id = ?", (nombre_imagen, id))

        conn.execute(
            "UPDATE propiedades SET nombre=?, ciudad=?, direccion=?, tipo=?, operacion=?, habitaciones=?, precio=?, descripcion=?, latitud=?, longitud=?, estado=? WHERE id=?",
            (nombre, ciudad, direccion, tipo, operacion, habitaciones, precio, descripcion, latitud, longitud, estado, id)
        )
        conn.commit()
        conn.close()

        flash('Propiedad actualizada exitosamente.', 'success')
        return redirect(f'/propiedad/{id}')

    conn.close()
    return render_template("editar_propiedad.html", prop=prop, imagenes=imagenes)


@app.route('/eliminar-imagen/<int:id>', methods=['POST'])
def eliminar_imagen(id):
    if not usuario_logueado() or not es_asesor():
        return redirect('/propiedades')

    conn = get_db()
    imagen = conn.execute("SELECT * FROM imagenes WHERE id = ?", (id,)).fetchone()
    if imagen:
        propiedad_id = imagen['propiedad_id']
        conn.execute("DELETE FROM imagenes WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        flash('Imagen eliminada.', 'success')
        return redirect(f'/editar/{propiedad_id}')

    conn.close()
    return redirect('/propiedades')


@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    if not usuario_logueado() or not es_asesor():
        return redirect('/propiedades')

    conn = get_db()
    prop = conn.execute("SELECT * FROM propiedades WHERE id = ?", (id,)).fetchone()
    usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()

    if prop and prop['usuario_id'] == usuario['id']:
        conn.execute("DELETE FROM imagenes WHERE propiedad_id = ?", (id,))
        conn.execute("DELETE FROM propiedades WHERE id = ?", (id,))
        conn.commit()
        flash('Propiedad eliminada.', 'success')
    else:
        flash('No tienes permiso para eliminar esta propiedad.', 'error')

    conn.close()
    return redirect('/propiedades')


@app.route('/perfil')
def perfil():
    if not usuario_logueado():
        flash('Debes iniciar sesión para ver tu perfil.', 'warning')
        return redirect('/login')

    conn = get_db()
    usuario = conn.execute("SELECT * FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
    propiedades = conn.execute("SELECT * FROM propiedades WHERE usuario_id = ?", (usuario['id'],)).fetchall()
    favoritos = conn.execute(
        "SELECT p.* FROM propiedades p JOIN favoritos f ON p.id = f.propiedad_id WHERE f.usuario_id = ?",
        (usuario['id'],)
    ).fetchall()
    conn.close()
    return render_template("perfil.html", usuario=usuario, propiedades=propiedades, favoritos=favoritos)


@app.route('/estadisticas')
def estadisticas():
    if not usuario_logueado() or not es_asesor():
        flash('Solo los asesores pueden ver las estadísticas.', 'error')
        return redirect('/')

    conn = get_db()
    tipos = conn.execute("SELECT tipo, COUNT(*) as total FROM propiedades GROUP BY tipo").fetchall()
    estados = conn.execute("SELECT estado, COUNT(*) as total FROM propiedades GROUP BY estado").fetchall()
    operaciones = conn.execute("SELECT operacion, COUNT(*) as total FROM propiedades GROUP BY operacion").fetchall()
    ciudades = conn.execute("SELECT ciudad, COUNT(*) as total FROM propiedades GROUP BY ciudad ORDER BY total DESC LIMIT 6").fetchall()
    conn.close()
    return render_template("estadisticas.html",
        tipos=tipos,
        estados=estados,
        operaciones=operaciones,
        ciudades=ciudades
    )


@app.route('/clientes')
def clientes():
    if not usuario_logueado() or not es_asesor():
        flash('Solo los asesores pueden ver los clientes.', 'error')
        return redirect('/')

    conn = get_db()
    usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
    lista_clientes = conn.execute(
        "SELECT * FROM clientes WHERE asesor_id = ? ORDER BY id DESC", (usuario['id'],)
    ).fetchall()
    conn.close()
    return render_template("clientes.html", clientes=lista_clientes)


@app.route('/clientes/agregar', methods=['GET', 'POST'])
def agregar_cliente():
    if not usuario_logueado() or not es_asesor():
        return redirect('/')

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        telefono = request.form.get('telefono', '').strip()
        tipo_busca = request.form.get('tipo_busca', '')
        presupuesto = request.form.get('presupuesto', '').strip()
        notas = request.form.get('notas', '').strip()

        conn = get_db()
        usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
        conn.execute(
            "INSERT INTO clientes (nombre, telefono, tipo_busca, presupuesto, notas, asesor_id) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, telefono, tipo_busca, presupuesto, notas, usuario['id'])
        )
        conn.commit()
        conn.close()

        flash('Cliente registrado exitosamente.', 'success')
        return redirect('/clientes')

    return render_template("agregar_cliente.html")


@app.route('/clientes/eliminar/<int:id>', methods=['POST'])
def eliminar_cliente(id):
    if not usuario_logueado() or not es_asesor():
        return redirect('/')

    conn = get_db()
    usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
    conn.execute("DELETE FROM clientes WHERE id = ? AND asesor_id = ?", (id, usuario['id']))
    conn.commit()
    conn.close()

    flash('Cliente eliminado.', 'success')
    return redirect('/clientes')


@app.route('/visitas')
def visitas():
    if not usuario_logueado() or not es_asesor():
        flash('Solo los asesores pueden ver las visitas.', 'error')
        return redirect('/')

    conn = get_db()
    usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
    lista_visitas = conn.execute(
        "SELECT v.*, p.nombre as prop_nombre, c.nombre as cliente_nombre FROM visitas v JOIN propiedades p ON v.propiedad_id = p.id JOIN clientes c ON v.cliente_id = c.id WHERE v.asesor_id = ? ORDER BY v.fecha ASC, v.hora ASC",
        (usuario['id'],)
    ).fetchall()
    conn.close()
    return render_template("visitas.html", visitas=lista_visitas)


@app.route('/visitas/agregar', methods=['GET', 'POST'])
def agregar_visita():
    if not usuario_logueado() or not es_asesor():
        return redirect('/')

    conn = get_db()
    usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
    propiedades = conn.execute("SELECT id, nombre, ciudad FROM propiedades WHERE usuario_id = ?", (usuario['id'],)).fetchall()
    clientes = conn.execute("SELECT id, nombre FROM clientes WHERE asesor_id = ?", (usuario['id'],)).fetchall()

    if request.method == 'POST':
        propiedad_id = request.form.get('propiedad_id')
        cliente_id = request.form.get('cliente_id')
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        notas = request.form.get('notas', '').strip()

        conn.execute(
            "INSERT INTO visitas (propiedad_id, cliente_id, asesor_id, fecha, hora, notas, estado) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (propiedad_id, cliente_id, usuario['id'], fecha, hora, notas, 'Pendiente')
        )
        conn.commit()
        conn.close()

        flash('Visita agendada exitosamente.', 'success')
        return redirect('/visitas')

    conn.close()
    return render_template("agregar_visita.html", propiedades=propiedades, clientes=clientes)


@app.route('/visitas/estado/<int:id>/<estado>', methods=['POST'])
def cambiar_estado_visita(id, estado):
    if not usuario_logueado() or not es_asesor():
        return redirect('/')

    conn = get_db()
    conn.execute("UPDATE visitas SET estado = ? WHERE id = ?", (estado, id))
    conn.commit()
    conn.close()

    flash(f'Visita marcada como {estado}.', 'success')
    return redirect('/visitas')


@app.route('/visitas/eliminar/<int:id>', methods=['POST'])
def eliminar_visita(id):
    if not usuario_logueado() or not es_asesor():
        return redirect('/')

    conn = get_db()
    conn.execute("DELETE FROM visitas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash('Visita eliminada.', 'success')
    return redirect('/visitas')


@app.route('/calculadora')
def calculadora():
    if not usuario_logueado() or not es_asesor():
        flash('Solo los asesores pueden usar la calculadora.', 'error')
        return redirect('/')
    return render_template("calculadora.html")


@app.route('/generar-descripcion', methods=['POST'])
def generar_descripcion():
    print('>>> FUNCIÓN LLAMADA')
    if not usuario_logueado() or not es_asesor():
        return {'error': 'No autorizado'}, 401

    datos = request.get_json()
    nombre = datos.get('nombre', '')
    tipo = datos.get('tipo', '')
    operacion = datos.get('operacion', '')
    ciudad = datos.get('ciudad', '')
    direccion = datos.get('direccion', '')
    habitaciones = datos.get('habitaciones', '')
    precio = datos.get('precio', '')

    prompt = f"""Eres un experto en bienes raíces. Escribe una descripción profesional y atractiva para esta propiedad inmobiliaria en español. La descripción debe ser persuasiva, destacar los puntos clave y tener entre 80 y 120 palabras. Solo devuelve la descripción, sin títulos ni explicaciones.

Datos de la propiedad:
- Nombre: {nombre}
- Tipo: {tipo}
- Operación: {operacion}
- Ciudad: {ciudad}
- Dirección: {direccion or 'No especificada'}
- Habitaciones: {habitaciones or 'No especificado'}
- Precio: USD {precio or 'A consultar'}"""

    payload = json.dumps({
        "model": "google/gemma-4-26b-a4b-it:free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }
    )

    import time
    for intento in range(4):
        try:
            with urllib.request.urlopen(req) as response:
                resultado = json.loads(response.read())
                descripcion = resultado['choices'][0]['message']['content']
                return {'descripcion': descripcion}
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento < 3:
                time.sleep(7)
                req = urllib.request.Request(
                    'https://openrouter.ai/api/v1/chat/completions',
                    data=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {API_KEY}'
                    }
                )
            else:
                print(f'ERROR HTTP {e.code}: {e.read().decode()}')
                return {'error': f'Error HTTP {e.code}'}, 500
        except Exception as e:
            print(f'ERROR: {e}')
            return {'error': str(e)}, 500
    return {'error': 'Demasiadas solicitudes, intenta de nuevo en unos segundos.'}, 429

@app.route('/sugerir-precio', methods=['POST'])
def sugerir_precio():
    if not usuario_logueado() or not es_asesor():
        return {'error': 'No autorizado'}, 401

    datos = request.get_json()
    ciudad = datos.get('ciudad', '')
    tipo = datos.get('tipo', '')
    operacion = datos.get('operacion', '')
    habitaciones = datos.get('habitaciones', '')

    prompt = f"""Eres un experto en el mercado inmobiliario de Paraguay. Basándote en los precios actuales del mercado paraguayo, sugiere un rango de precio estimado en USD para la siguiente propiedad. Responde SOLO con el rango en este formato exacto: "USD X.000 - USD Y.000" seguido de una línea de explicación breve (máximo 20 palabras). Sin títulos ni texto adicional.

Propiedad:
- Ciudad: {ciudad}
- Tipo: {tipo}
- Operación: {operacion}
- Habitaciones: {habitaciones or 'No especificado'}"""

    payload = json.dumps({
        "model": "google/gemma-4-26b-a4b-it:free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100
    }).encode('utf-8')

    import time
    for intento in range(4):
        try:
            req = urllib.request.Request(
                'https://openrouter.ai/api/v1/chat/completions',
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {API_KEY}'
                }
            )
            with urllib.request.urlopen(req) as response:
                resultado = json.loads(response.read())
                sugerencia = resultado['choices'][0]['message']['content']
                return {'sugerencia': sugerencia}
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento < 3:
                time.sleep(7)
            else:
                return {'error': f'Error HTTP {e.code}'}, 500
        except Exception as e:
            return {'error': str(e)}, 500
    return {'error': 'Demasiadas solicitudes, intenta de nuevo.'}, 429


@app.route('/consultar/<int:propiedad_id>', methods=['POST'])
def consultar(propiedad_id):
    if not usuario_logueado():
        flash('Debes iniciar sesión para enviar una consulta.', 'warning')
        return redirect('/login')

    pregunta = request.form.get('pregunta', '').strip()
    if not pregunta:
        flash('Escribe tu pregunta antes de enviar.', 'error')
        return redirect(f'/propiedad/{propiedad_id}')

    from datetime import datetime
    conn = get_db()
    usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
    conn.execute(
        "INSERT INTO consultas (propiedad_id, cliente_id, pregunta, fecha) VALUES (?, ?, ?, ?)",
        (propiedad_id, usuario['id'], pregunta, datetime.now().strftime('%d/%m/%Y %H:%M'))
    )
    conn.commit()
    conn.close()

    flash('Consulta enviada exitosamente. El asesor te responderá pronto.', 'success')
    return redirect(f'/propiedad/{propiedad_id}')


@app.route('/consultas')
def ver_consultas():
    if not usuario_logueado() or not es_asesor():
        flash('Solo los asesores pueden ver las consultas.', 'error')
        return redirect('/')

    conn = get_db()
    usuario = conn.execute("SELECT id FROM usuarios WHERE email = ?", (session['usuario'],)).fetchone()
    consultas = conn.execute('''
        SELECT c.*, p.nombre as prop_nombre, u.nombre as cliente_nombre, u.email as cliente_email
        FROM consultas c
        JOIN propiedades p ON c.propiedad_id = p.id
        JOIN usuarios u ON c.cliente_id = u.id
        WHERE p.usuario_id = ?
        ORDER BY c.id DESC
    ''', (usuario['id'],)).fetchall()
    conn.close()
    return render_template("consultas.html", consultas=consultas)


@app.route('/consultas/responder/<int:id>', methods=['POST'])
def responder_consulta(id):
    if not usuario_logueado() or not es_asesor():
        return redirect('/')

    respuesta = request.form.get('respuesta', '').strip()
    if respuesta:
        conn = get_db()
        conn.execute("UPDATE consultas SET respuesta = ? WHERE id = ?", (respuesta, id))
        conn.commit()
        conn.close()
        flash('Respuesta enviada exitosamente.', 'success')

    return redirect('/consultas')

# ----------------- AUTENTICACIÓN -----------------

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if usuario_logueado():
        return redirect('/')

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefono = request.form.get('telefono', '').strip()
        rol = request.form.get('rol', 'cliente')
        password = request.form.get('password', '')
        confirmar = request.form.get('confirmar', '')

        if not nombre or not email or not password:
            flash('Completa todos los campos.', 'error')
            return render_template('registro.html')

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return render_template('registro.html')

        if password != confirmar:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('registro.html')

        conn = get_db()
        existe = conn.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone()

        if existe:
            flash('Ya existe una cuenta con ese correo.', 'error')
            conn.close()
            return render_template('registro.html')

        conn.execute(
            "INSERT INTO usuarios (nombre, email, password, telefono, rol) VALUES (?, ?, ?, ?, ?)",
            (nombre, email, generate_password_hash(password), telefono, rol)
        )
        conn.commit()
        conn.close()

        flash('¡Cuenta creada exitosamente! Ya puedes iniciar sesión.', 'success')
        return redirect('/login')

    return render_template('registro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if usuario_logueado():
        return redirect('/')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db()
        usuario = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario['password'], password):
            session['usuario'] = usuario['email']
            session['nombre'] = usuario['nombre']
            session['rol'] = usuario['rol']
            flash(f'¡Bienvenido, {usuario["nombre"]}!', 'success')
            return redirect('/')
        else:
            flash('Correo o contraseña incorrectos.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect('/')


# ----------------- EJECUTAR SERVIDOR -----------------

init_db()

if __name__ == "__main__":
    app.run(debug=True, port=8080)