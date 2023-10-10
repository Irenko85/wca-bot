import requests
from bs4 import BeautifulSoup
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
import difflib

"""
Este módulo contiene funciones para:
- Obtener los torneos actuales desde una URL de la WCA.
- Guardar los torneos en una base de datos PostgreSQL.
- Verificar si hay torneos nuevos cada 12 horas.

TODO:
    - Agregar función que elimine torneos ya realizados de la base de datos.
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
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

# Verificar los torneos guardados en la base de datos
# cargar_torneos_conocidos() -> list
def cargar_torneos_conocidos():
    try:
        conn = db_conn()
        cur = conn.cursor()
        # Obtener los torneos con fecha mayor o igual a la fecha actual
        cur.execute('SELECT * FROM torneos WHERE fecha >= %s;', (obtener_fecha_actual(),))
        resultados = cur.fetchall()
        cur.close()
        conn.close()

        torneos_conocidos = []
        for resultado in resultados:
            torneo = {
                "Nombre torneo": resultado[1],
                "URL": resultado[5],
                "Fecha": resultado[2],
                "Lugar": resultado[4],
                "Pais": resultado[3]
            }
            torneos_conocidos.append(torneo)

        return torneos_conocidos
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

# Función para obtener los torneos desde la URL y retornar una lista de diccionarios con los torneos encontrados
# obtener_torneos(url: str) -> list
def obtener_torneos(url, pais = 'Chile'):
    try:
        pais = obtener_pais(pais)
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
            _fecha = fecha.get_text(strip=True)
            fecha = datetime.strptime(_fecha, "%b %d, %Y").date()
            lugar = lugar.get_text(strip=True).replace(pais + ', ', '')

            torneo = {
                "Nombre torneo": nombre_torneo,
                "URL": url,
                "Fecha": fecha,
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
        cur.execute('INSERT INTO torneos (nombre, fecha, pais, lugar, url) VALUES (%s, %s, %s, %s, %s);', (torneo['Nombre torneo'], torneo['Fecha'], torneo['Pais'], torneo['Lugar'], torneo['URL']))
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

def limpiar_base_de_datos():
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM torneos WHERE fecha < %s;', (obtener_fecha_actual(),))
        conn.commit()
        cur.close()
        conn.close()
        print(f'Se han eliminado los torneos con fecha menor a {obtener_fecha_actual()} de la base de datos.')
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

# Función para obtener el país usando la API de la WCA
def obtener_pais(pais):
    API = 'https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/countries.json'
    respuesta = requests.get(API)
    respuesta.raise_for_status() # Genera una excepción si la solicitud no es exitosa
    paises = respuesta.json()

    # Listas con los nombres y códigos de los países
    nombres_paises = [p['name'].lower() for p in paises['items']]
    codigos_paises = [p['iso2Code'].lower() for p in paises['items']]

    pais = pais.lower()

    # Si se proporciona el nombre completo del país, retornar el mismo nombre
    if pais in nombres_paises:
        return pais.replace(' ', '+')

    # Si el argumento es un código de dos letras, retornar el nombre del país
    if pais in codigos_paises:
        indice = codigos_paises.index(pais)
        return nombres_paises[indice].replace(' ', '+')

    # Si no se encuentra una coincidencia exacta, buscar sugerencias de corrección
    sugerencias = difflib.get_close_matches(pais, nombres_paises, n=1, cutoff=0.8)
    if sugerencias:
        return nombres_paises[nombres_paises.index(sugerencias[0])]
    
    # Si no se encuentra una sugerencia, retornar Chile
    print('No se han encontrado coincidencias. Buscando torneos en Chile...')
    return 'Chile'