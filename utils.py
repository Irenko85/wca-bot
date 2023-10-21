import requests
from bs4 import BeautifulSoup
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
import difflib
from googletrans import Translator

"""
Este módulo contiene funciones para:
- Obtener los torneos actuales desde una URL de la WCA.
- Obtener los torneos guardados en la base de datos.
- Guardar los torneos en una base de datos PostgreSQL.
- Eliminar torneos antiguos de la base de datos.
- Obtener el país usando la API de la WCA.
- Validar el país ingresado por el usuario.
"""

# URLs con torneos actuales
URL = 'https://www.worldcubeassociation.org/competitions?region=Chile&search=&state=present&year=all+years&from_date=&to_date=&delegate=&display=list'
WCA_URL = 'https://www.worldcubeassociation.org'

load_dotenv()  # Cargar variables de entorno desde el archivo .env

# Conectarse a la base de datos de PostgreSQL
DB_URL = os.getenv('DATABASE_URL')
DB_NAME = os.getenv('PGDATABASE')
DB_HOST = os.getenv('PGHOST')
DB_PASSWORD = os.getenv('PGPASSWORD')
DB_PORT = os.getenv('PGPORT')
DB_USER = os.getenv('PGUSER')

# Función para conectarse a la base de datos
def db_conn():
    return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
            )

# Verificar los torneos guardados en la base de datos
# cargar_torneos_conocidos() -> list
def cargar_torneos_conocidos():
    try:
        conn = db_conn()
        cur = conn.cursor()
        # Obtener los torneos con fecha mayor o igual a la fecha actual
        cur.execute('SELECT * FROM torneos WHERE inicio >= %s;', (obtener_fecha_actual(),))
        resultados = cur.fetchall()
        cur.close()
        conn.close()

        torneos_conocidos = []
        for resultado in resultados:
            torneo = {
                "Nombre torneo": resultado[1],
                "URL": resultado[6],
                "Fecha inicio": resultado[2],
                "Fecha fin": resultado[3],
                "Lugar": resultado[5],
                "Pais": resultado[4]
            }
            torneos_conocidos.append(torneo)

        return torneos_conocidos
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

# Función para obtener los torneos desde la URL y retornar una lista de diccionarios con los torneos encontrados
# obtener_torneos(url: str) -> list
def obtener_torneos(url, pais='Chile'):
    try:
        pais = obtener_pais_para_url(pais)
        url = url.replace('Chile', pais)
        respuesta = requests.get(url)
        respuesta.raise_for_status() # Genera una excepción si la solicitud no es exitosa
        soup = BeautifulSoup(respuesta.text, 'html.parser')

        elementos_competencia = soup.find_all('span', class_='competition-info')
        elementos_fecha = soup.find_all('span', class_='date')
        elementos_lugar = soup.find_all('div', class_='location')

        # Verificar si existen torneos
        if not elementos_competencia or not elementos_fecha or not elementos_lugar:
            print('No se encontraron torneos.')
            return []

        torneos = []

        for competencia, fecha, lugar in zip(elementos_competencia, elementos_fecha, elementos_lugar):
            enlace = competencia.find('a')
            nombre_torneo = enlace.text.strip()
            url = WCA_URL + enlace['href']

            _fecha = fecha.get_text(strip=True).replace(',', '')
            mes = _fecha.split(' ')[0].strip()

            if '-' in _fecha:
                anio = _fecha.split(' ')[4]

                _fecha_inicio = mes + ' ' + _fecha.split(' ')[1] + ' ' + anio
                fecha_inicio = datetime.strptime(_fecha_inicio, "%b %d %Y").date()
                
                _fecha_fin = mes + ' ' + _fecha.split(' ')[3] + ' ' + anio
                fecha_fin = datetime.strptime(_fecha_fin, "%b %d %Y").date()
                
            else:
                fecha_inicio = datetime.strptime(_fecha, "%b %d %Y").date()
                fecha_fin = fecha_inicio

            lugar = lugar.get_text(strip=True).replace(pais + ', ', '')

            torneo = {
                "Nombre torneo": nombre_torneo,
                "URL": url,
                "Fecha inicio": fecha_inicio,
                "Fecha fin": fecha_fin,
                "Lugar": lugar,
                "Pais": pais
            }

            torneos.append(torneo)

        return torneos

    except requests.exceptions.RequestException as e:
        print('Error con la petición HTTP:', e)
        return []

# Función para guardar un torneo en la base de datos
# guardar_torneo(torneo: dict) -> None
def guardar_torneo(torneo: dict):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO torneos (nombre, inicio, fin, pais, lugar, url) VALUES (%s, %s, %s, %s, %s, %s);', (torneo['Nombre torneo'], torneo['Fecha inicio'], torneo['Fecha fin'], torneo['Pais'], torneo['Lugar'], torneo['URL']))
        conn.commit()
        cur.close()
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

def obtener_fecha_actual():
    return datetime.now().date()

# Función para eliminar un torneo de la base de datos
# eliminar_torneo(url: str) -> None
def eliminar_torneo(url: str):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM torneos WHERE url = %s;', (url,))
        conn.commit()
        cur.close()
        conn.close()
        print(f'Se ha eliminado el torneo con URL: {url}')
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

# Función para eliminar torneos antiguos de la base de datos
def limpiar_base_de_datos():
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM torneos WHERE fin < %s;', (obtener_fecha_actual(),))
        conn.commit()
        cur.close()
        conn.close()
        print(f'Se han eliminado los torneos con fecha menor a {obtener_fecha_actual()} de la base de datos.')
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

# Función para obtener los países desde la API de la WCA
def api_paises():
    API = 'https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/countries.json'
    respuesta = requests.get(API)
    respuesta.raise_for_status() # Genera una excepción si la solicitud no es exitosa
    paises = respuesta.json()

    return paises

# Función para retornar el nombre del país con formato de URL
def obtener_pais_para_url(pais):
    paises = api_paises()

    # Listas con los nombres y códigos de los países
    nombres_paises = [p['name'].lower() for p in paises['items']]
    codigos_paises = [p['iso2Code'].lower() for p in paises['items']]

    pais = pais.lower()

    # Si se proporciona el nombre completo del país, retornar el mismo nombre
    if pais in nombres_paises:
        # Se retorna el nombre del país con formato de URL
        return pais.replace(' ', '+')

    # Si el argumento es un código de dos letras, retornar el nombre del país
    if pais in codigos_paises:
        # Se obtiene el índice del código de país
        indice = codigos_paises.index(pais)
        # Se retorna el nombre del país con formato de URL
        return nombres_paises[indice].replace(' ', '+')

    # Si no se encuentra una coincidencia exacta, buscar sugerencias de corrección
    sugerencias = difflib.get_close_matches(pais, nombres_paises, n=1, cutoff=0.8)
    if sugerencias:
        return nombres_paises[nombres_paises.index(sugerencias[0])]
    
    # Si no se encuentra una sugerencia, retornar Chile
    print('No se han encontrado coincidencias. Buscando torneos en Chile...')
    return 'Chile'

# Función para obtener el nombre del país con formato de título
def obtener_pais(pais):
    return obtener_pais_para_url(pais).title().replace('+', ' ')

def validar_pais(pais):
    paises = api_paises()
    nombres_paises = [p['name'].lower() for p in paises['items']]
    codigos_paises = [p['iso2Code'].lower() for p in paises['items']]
    pais = obtener_pais(pais)
    print(pais)
    es_valido = False
    if pais in nombres_paises or pais in codigos_paises:
        es_valido = True
    else:
        sugerencias = difflib.get_close_matches(pais, nombres_paises, n=1, cutoff=0.8)
        if sugerencias:
            pais = nombres_paises[nombres_paises.index(sugerencias[0])]
            es_valido = True
    return es_valido

def traducir_texto(idioma_output, texto):
    traductor = Translator()
    res = traductor.translate(texto, dest=idioma_output).text
    return res