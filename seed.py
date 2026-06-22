"""
Script para poblar la base de datos con datos de ejemplo.
Ejecutar con: python seed.py
"""

import sqlite3
import os
import urllib.request
from werkzeug.security import generate_password_hash
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'inmobiliaria.db')
UPLOADS = os.path.join(BASE_DIR, 'static', 'uploads')

# Imágenes placeholder por tipo de propiedad (Unsplash - libres de uso)
IMAGENES = {
    'casa':        'https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800&q=80',
    'casa2':       'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&q=80',
    'apartamento': 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&q=80',
    'apartamento2':'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&q=80',
    'terreno':     'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80',
    'local':       'https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&q=80',
}

def descargar_imagen(nombre_archivo, url):
    ruta = os.path.join(UPLOADS, nombre_archivo)
    if not os.path.exists(ruta):
        print(f'  Descargando {nombre_archivo}...')
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as r:
                with open(ruta, 'wb') as f:
                    f.write(r.read())
        except Exception as e:
            print(f'  Error descargando {nombre_archivo}: {e}')
            # Usar imagen vacía como fallback
            open(ruta, 'wb').close()
    return nombre_archivo

def seed():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ── Limpiar datos previos de ejemplo ──────────────────────────────────────
    print('Limpiando datos anteriores...')
    for tabla in ['consultas', 'favoritos', 'visitas', 'imagenes', 'propiedades', 'clientes', 'usuarios']:
        c.execute(f'DELETE FROM {tabla}')

    # ── Descargar imágenes ────────────────────────────────────────────────────
    print('Descargando imágenes...')
    os.makedirs(UPLOADS, exist_ok=True)
    imgs = {k: descargar_imagen(f'placeholder_{k}.jpg', v) for k, v in IMAGENES.items()}

    # ── Usuarios ──────────────────────────────────────────────────────────────
    print('Creando usuarios...')
    asesores = [
        ('Carlos Méndez',    'carlos@estatesystem.com',  '123456', '0981-111-001', 'asesor'),
        ('Laura Giménez',    'laura@estatesystem.com',   '123456', '0982-222-002', 'asesor'),
        ('Diego Rodríguez',  'diego@estatesystem.com',   '123456', '0983-333-003', 'asesor'),
    ]
    clientes_data = [
        ('Ana Torres',   'ana@gmail.com',    '123456', '0984-444-004', 'cliente'),
        ('Pedro López',  'pedro@gmail.com',  '123456', '0985-555-005', 'cliente'),
    ]

    ids_asesores = []
    for nombre, email, pw, tel, rol in asesores:
        c.execute(
            'INSERT INTO usuarios (nombre, email, password, telefono, rol) VALUES (?,?,?,?,?)',
            (nombre, email, generate_password_hash(pw), tel, rol)
        )
        ids_asesores.append(c.lastrowid)

    ids_clientes = []
    for nombre, email, pw, tel, rol in clientes_data:
        c.execute(
            'INSERT INTO usuarios (nombre, email, password, telefono, rol) VALUES (?,?,?,?,?)',
            (nombre, email, generate_password_hash(pw), tel, rol)
        )
        ids_clientes.append(c.lastrowid)

    a1, a2, a3 = ids_asesores
    cl1, cl2 = ids_clientes

    # ── Propiedades ───────────────────────────────────────────────────────────
    print('Creando propiedades...')
    propiedades = [
        # (nombre, ciudad, direccion, tipo, operacion, hab, precio, descripcion, imagen, lat, lng, estado, usuario_id)

        # --- Asunción ---
        ('Residencia en Villa Morra',
         'Asunción', 'Av. Mcal. López 2450, Villa Morra',
         'Casa', 'Venta', 4, '185.000',
         'Amplia residencia en una de las zonas más exclusivas de Asunción. Cuenta con jardín privado, garage para 2 vehículos, cocina americana y living comedor integrado con acabados modernos.',
         imgs['casa'], -25.2867, -57.5759, 'Disponible', a1),

        ('Apartamento en Carmelitas',
         'Asunción', 'Calle Eligio Ayala 987, Carmelitas',
         'Apartamento', 'Alquiler', 2, '650',
         'Moderno apartamento en el centro de Asunción, a pasos de shoppings, restaurantes y bancos. Piso 8 con vista panorámica, balcón, seguridad 24h y estacionamiento incluido.',
         imgs['apartamento'], -25.2820, -57.6358, 'Disponible', a1),

        ('Casa Familiar en San Lorenzo',
         'Asunción', 'Ruta 2 km 12, San Lorenzo',
         'Casa', 'Venta', 3, '95.000',
         'Casa familiar en barrio tranquilo de San Lorenzo, ideal para familia. Tres dormitorios, dos baños, patio con árboles frutales y cochera techada. A 10 min del centro.',
         imgs['casa2'], -25.3390, -57.5085, 'Disponible', a2),

        ('Local Comercial Centro',
         'Asunción', 'Calle Palma 650, Centro Histórico',
         'Local comercial', 'Alquiler', 0, '1.200',
         'Local comercial de 120m² sobre la peatonal Palma, la arteria comercial más importante de Asunción. Apto para cualquier tipo de negocio, con excelente flujo de personas.',
         imgs['local'], -25.2868, -57.6390, 'Disponible', a2),

        # --- Encarnación ---
        ('Casa con Piscina en Encarnación',
         'Encarnación', 'Av. Costanera 1200, Encarnación',
         'Casa', 'Venta', 4, '220.000',
         'Espectacular casa a 200 metros de la Costanera de Encarnación. Piscina propia, quincho con parrilla, 4 dormitorios en suite, doble garage y jardín paisajístico.',
         imgs['casa'], -27.3319, -55.8658, 'Disponible', a1),

        ('Apartamento Costanera',
         'Encarnación', 'Av. Costanera 450, Encarnación',
         'Apartamento', 'Alquiler', 2, '550',
         'Apartamento con vista al río Paraná en el edificio más moderno de la Costanera. Amoblado, con aire acondicionado, seguridad y acceso a piscina del edificio.',
         imgs['apartamento2'], -27.3384, -55.8672, 'Disponible', a1),

        ('Terreno en Trinidad',
         'Encarnación', 'Ruta 6 km 3, Trinidad',
         'Terreno', 'Venta', 0, '35.000',
         'Terreno de 1.500m² en zona residencial de Trinidad, a 5 km de Encarnación. Acceso pavimentado, servicios básicos disponibles. Ideal para construir vivienda o complejo.',
         imgs['terreno'], -27.2989, -55.8011, 'Disponible', a3),

        ('Casa en Barrio Obrero',
         'Encarnación', 'Calle Mcal. Estigarribia 340',
         'Casa', 'Venta', 3, '78.000',
         'Casa de 3 dormitorios, living amplio, cocina con mesada de granito y patio trasero de 200m². Construcción sólida en ladrillo, ubicada en barrio consolidado y tranquilo.',
         imgs['casa2'], -27.3411, -55.8790, 'Disponible', a3),

        # --- Ciudad del Este ---
        ('Apartamento en CDE Centro',
         'Ciudad del Este', 'Av. Adrián Jara 1500, Centro',
         'Apartamento', 'Alquiler', 1, '400',
         'Apartamento de 1 dormitorio en el corazón comercial de Ciudad del Este. Ideal para profesional o pareja. Cerca del Shopping del Este, con todos los servicios.',
         imgs['apartamento'], -25.5088, -54.6116, 'Disponible', a2),

        ('Casa en Barrio Minga Guazú',
         'Ciudad del Este', 'Minga Guazú, Ciudad del Este',
         'Casa', 'Venta', 4, '130.000',
         'Amplia casa de 4 dormitorios en Minga Guazú, zona de creciente desarrollo. Doble cochera, jardín, quincho y depósito. Excelente oportunidad de inversión.',
         imgs['casa'], -25.4832, -54.7326, 'Disponible', a3),

        ('Terreno Industrial CDE',
         'Ciudad del Este', 'Zona Franca, Ciudad del Este',
         'Terreno', 'Venta', 0, '85.000',
         'Terreno de 3.000m² en zona industrial con acceso directo a la ruta. Apto para galpón, depósito o planta productiva. Documentación en orden, listo para transferir.',
         imgs['terreno'], -25.5272, -54.6413, 'Disponible', a2),

        # --- Luque ---
        ('Casa Moderna en Luque',
         'Luque', 'Calle General Díaz 890, Luque',
         'Casa', 'Venta', 3, '115.000',
         'Moderna casa de 3 dormitorios en Luque, ciudad vecina a Asunción. Diseño contemporáneo, cocina integrada, jardín frontal y amplio patio trasero. Barrio residencial seguro.',
         imgs['casa2'], -25.2658, -57.4822, 'Disponible', a1),

        ('Apartamento Luque Centro',
         'Luque', 'Av. Mcal. López 120, Luque',
         'Apartamento', 'Alquiler', 2, '500',
         'Apartamento de 2 dormitorios en Luque centro, a minutos de Asunción por la autopista. Ideal para quienes trabajan en la capital pero prefieren tranquilidad suburbana.',
         imgs['apartamento2'], -25.2690, -57.4859, 'Disponible', a3),

        ('Terreno Residencial Luque',
         'Luque', 'Compañía Ytay, Luque',
         'Terreno', 'Venta', 0, '28.000',
         'Terreno de 900m² en zona residencial tranquila de Luque. Todos los servicios disponibles, acceso asfaltado. Perfecto para construir la casa de tus sueños.',
         imgs['terreno'], -25.2810, -57.4750, 'Disponible', a2),
    ]

    ids_propiedades = []
    for p in propiedades:
        c.execute('''
            INSERT INTO propiedades
            (nombre, ciudad, direccion, tipo, operacion, habitaciones, precio, descripcion, imagen, latitud, longitud, estado, vistas, usuario_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (*p, 0))
        pid = c.lastrowid
        ids_propiedades.append(pid)
        c.execute('INSERT INTO imagenes (propiedad_id, nombre) VALUES (?,?)', (pid, p[8]))

    # Agregar algunas vistas realistas
    vistas = [42, 18, 31, 9, 67, 24, 11, 38, 15, 50, 7, 29, 20, 5]
    for i, pid in enumerate(ids_propiedades):
        c.execute('UPDATE propiedades SET vistas=? WHERE id=?', (vistas[i], pid))

    # ── Clientes (tabla clientes, no usuarios) ────────────────────────────────
    print('Creando clientes...')
    clientes_asesor = [
        ('Roberto Cáceres', '0981-600-111', 'Casa', '80.000 - 120.000', 'Busca casa en Luque o San Lorenzo, 3 dorm mínimo.', a1),
        ('María Insaurralde', '0982-700-222', 'Apartamento', '400 - 700', 'Interesada en alquiler en Asunción o Encarnación.', a1),
        ('Jorge Villalba', '0983-800-333', 'Terreno', '25.000 - 50.000', 'Quiere terreno para construir en CDE o Luque.', a2),
        ('Sofía Benítez', '0984-900-444', 'Casa', '150.000 - 250.000', 'Busca casa con piscina en Encarnación.', a2),
        ('Luis Fernández', '0985-000-555', 'Local comercial', '800 - 1.500', 'Necesita local en zona céntrica de Asunción.', a3),
    ]
    ids_clientes_tabla = []
    for nombre, tel, tipo, presupuesto, notas, asesor_id in clientes_asesor:
        c.execute(
            'INSERT INTO clientes (nombre, telefono, tipo_busca, presupuesto, notas, asesor_id) VALUES (?,?,?,?,?,?)',
            (nombre, tel, tipo, presupuesto, notas, asesor_id)
        )
        ids_clientes_tabla.append(c.lastrowid)

    # ── Favoritos ─────────────────────────────────────────────────────────────
    print('Creando favoritos...')
    favoritos = [
        (cl1, ids_propiedades[0]),
        (cl1, ids_propiedades[4]),
        (cl1, ids_propiedades[11]),
        (cl2, ids_propiedades[2]),
        (cl2, ids_propiedades[8]),
        (cl2, ids_propiedades[5]),
    ]
    for uid, pid in favoritos:
        c.execute('INSERT INTO favoritos (usuario_id, propiedad_id) VALUES (?,?)', (uid, pid))

    # ── Consultas con respuestas ──────────────────────────────────────────────
    print('Creando consultas...')
    hoy = datetime.now().strftime('%d/%m/%Y %H:%M')
    consultas = [
        (ids_propiedades[0], cl1,
         '¿La propiedad tiene escritura al día y está libre de deudas?',
         'Sí, la propiedad tiene escritura pública inscrita en la DGRP y está libre de gravámenes. Podemos enviarle los documentos para su revisión.', hoy),

        (ids_propiedades[0], cl1,
         '¿Aceptan financiamiento bancario?',
         'Sí, el propietario acepta financiamiento bancario. Incluso podemos asesorarle con los trámites en BNF o banco privado.', hoy),

        (ids_propiedades[4], cl2,
         '¿La piscina está en buenas condiciones? ¿Qué tan cerca está la playa de la Costanera?',
         'La piscina fue renovada hace 6 meses, está en perfectas condiciones. La Costanera queda a exactamente 180 metros caminando.', hoy),

        (ids_propiedades[8], cl1,
         '¿El alquiler incluye gastos comunes?',
         'El precio incluye expensas del edificio. El inquilino solo paga luz, agua y gas por separado.', hoy),

        (ids_propiedades[11], cl2,
         '¿Cuántos baños tiene la casa y tiene garage?',
         'La casa tiene 2 baños completos más toilette. El garage es doble y techado.', hoy),
    ]
    for prop_id, cliente_id, pregunta, respuesta, fecha in consultas:
        c.execute(
            'INSERT INTO consultas (propiedad_id, cliente_id, pregunta, respuesta, fecha) VALUES (?,?,?,?,?)',
            (prop_id, cliente_id, pregunta, respuesta, fecha)
        )

    # ── Visitas ───────────────────────────────────────────────────────────────
    print('Creando visitas...')
    visitas = [
        (ids_propiedades[0],  ids_clientes_tabla[0], a1, '2026-07-05', '10:00', 'Cliente muy interesado, viene con su familia.',    'Pendiente'),
        (ids_propiedades[4],  ids_clientes_tabla[3], a1, '2026-07-08', '15:30', 'Segunda visita, ya vio fotos y le encantó.',       'Pendiente'),
        (ids_propiedades[11], ids_clientes_tabla[2], a2, '2026-07-03', '09:00', 'Visita confirmada por WhatsApp.',                  'Realizada'),
        (ids_propiedades[2],  ids_clientes_tabla[1], a2, '2026-06-28', '11:00', 'Cliente buscaba algo más económico.',              'Cancelada'),
        (ids_propiedades[8],  ids_clientes_tabla[4], a3, '2026-07-10', '16:00', 'Interesado en alquilar para su empresa.',         'Pendiente'),
    ]
    for v in visitas:
        c.execute(
            'INSERT INTO visitas (propiedad_id, cliente_id, asesor_id, fecha, hora, notas, estado) VALUES (?,?,?,?,?,?,?)', v
        )

    conn.commit()
    conn.close()

    print('\n✅ Base de datos poblada exitosamente.')
    print(f'   {len(propiedades)} propiedades en Asunción, Encarnación, CDE y Luque')
    print(f'   3 asesores + 2 usuarios cliente + 5 clientes en cartera')
    print(f'   {len(favoritos)} favoritos, {len(consultas)} consultas, {len(visitas)} visitas')
    print('\nCredenciales de acceso:')
    print('  Asesor 1:  carlos@estatesystem.com  / 123456')
    print('  Asesor 2:  laura@estatesystem.com   / 123456')
    print('  Asesor 3:  diego@estatesystem.com   / 123456')
    print('  Cliente 1: ana@gmail.com            / 123456')
    print('  Cliente 2: pedro@gmail.com          / 123456')

if __name__ == '__main__':
    seed()
