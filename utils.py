import requests
from bs4 import BeautifulSoup
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

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
        cur.execute('SELECT * FROM torneos;')
        resultados = cur.fetchall()
        cur.close()
        conn.close()

        torneos_conocidos = []
        for resultado in resultados:
            torneo = {
                "Nombre torneo": resultado[1],
                "URL": resultado[5],
                "Fecha": resultado[2],
                "Lugar": resultado[4]
            }
            torneos_conocidos.append(torneo)

        return torneos_conocidos
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

# Función para obtener los torneos desde la URL y retornar una lista de diccionarios con los torneos encontrados
# obtener_torneos(url: str) -> list
def obtener_torneos(url):
    try:
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
            lugar = lugar.get_text(strip=True).replace('Chile, ', '')

            torneo = {
                "Nombre torneo": nombre_torneo,
                "URL": url,
                "Fecha": fecha,
                "Lugar": lugar
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
        cur.execute('INSERT INTO torneos (nombre, fecha, pais, lugar, url) VALUES (%s, %s, %s, %s, %s);', (torneo['Nombre torneo'], torneo['Fecha'], 'Chile', torneo['Lugar'], torneo['URL']))
        conn.commit()
        cur.close()
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)