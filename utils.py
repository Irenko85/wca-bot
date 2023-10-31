"""
Módulo con funciones que utiliza el bot de Discord.

Funciones:
    db_conn() -> psycopg2.extensions.connection
    cargar_torneos_conocidos() -> list
    obtener_torneos(url: str, pais: str = 'Chile') -> list
    guardar_torneo(torneo: dict) -> None
    obtener_fecha_actual() -> datetime.date
    eliminar_torneo(url: str) -> None
    limpiar_base_de_datos() -> None
    api_paises() -> dict
    obtener_pais_para_url(pais: str) -> str
    obtener_pais(pais: str) -> str
    validar_pais(pais: str) -> bool
    traducir_texto(idioma_output: str, texto: str) -> str

Variables:
    URL (str): URL de la WCA para obtener los torneos actuales.
    WCA_URL (str): URL de la WCA.
    DB_URL (str): URL de la base de datos.
    DB_NAME (str): Nombre de la base de datos.
    DB_HOST (str): Host de la base de datos.
    DB_PASSWORD (str): Contraseña de la base de datos.
    DB_PORT (str): Puerto de la base de datos.
    DB_USER (str): Usuario de la base de datos.
"""


import json
import requests
from bs4 import BeautifulSoup
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime


# URLs con torneos actuales
URL = 'https://www.worldcubeassociation.org/competitions?region=Chile&search=&state=present&year=all+years&from_date=&to_date=&delegate=&display=list'
WCA_URL = 'https://www.worldcubeassociation.org'

load_dotenv()  # Cargar variables de entorno desde el archivo .env

# Variables de entorno para la base de datos
DB_URL = os.getenv('DATABASE_URL')
DB_NAME = os.getenv('PGDATABASE')
DB_HOST = os.getenv('PGHOST')
DB_PASSWORD = os.getenv('PGPASSWORD')
DB_PORT = os.getenv('PGPORT')
DB_USER = os.getenv('PGUSER')


def db_conn():
    '''
    Función para conectarse a la base de datos.

    Parámetros:
    None

    Retorna:
    psycopg2.extensions.connection: Conexión a la base de datos.
    '''
    return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
            )


def cargar_torneos_conocidos():
    '''
    Carga los torneos guardados en la base de datos y los retorna en una lista de diccionarios con los torneos.

    Parámetros:
    None

    Retorna:
    list: Lista de diccionarios con los torneos guardados en la base de datos.
    '''
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


def obtener_torneos(url, pais):
    '''
    Obtiene los torneos desde la URL ingresada y retorna una lista de diccionarios con los torneos encontrados.

    Parámetros:
    url (str): URL de la WCA.
    pais (str): Nombre o código de país.

    Retorna:
    list: Lista de diccionarios con los torneos encontrados.
    '''
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


def guardar_torneo(torneo: dict):
    '''
    Guarda el torneo ingresado en la base de datos.

    Parámetros:
    torneo (dict): Torneo a guardar.

    Retorna:
    None
    '''
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
    '''
    Retorna la fecha actual.

    Parámetros:
    None

    Retorna:
    datetime.date: Fecha actual.
    '''
    return datetime.now().date()


def eliminar_torneo(url: str):
    '''
    Función para eliminar un torneo de la base de datos.

    Parámetros:
    url (str): URL del torneo a eliminar.

    Retorna:
    None
    '''
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
    '''
    Función para eliminar torneos antiguos de la base de datos.

    Parámetros:
    None

    Retorna:
    None
    '''
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


def api_paises():
    '''
    Obtiene los países desde la API de la WCA y los retorna en formato JSON.

    Parámetros:
    None

    Retorna:
    dict: Países en formato JSON.
    '''
    API = 'https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/countries.json'
    respuesta = requests.get(API)
    respuesta.raise_for_status() # Genera una excepción si la solicitud no es exitosa
    paises = respuesta.json()

    return paises


def obtener_pais_para_url(pais):
    '''
    Retorna el país entregado con formato de URL para reemplazar en la URL de la WCA.

    Parámetros:
    pais (str): Nombre o código de país.

    Retorna:
    str: Nombre del país con formato de URL.
    '''
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
    
    # Si no se encuentra una sugerencia, retornar Chile
    print('No se han encontrado coincidencias. Buscando torneos en Chile...')
    return 'Chile'


def obtener_pais(pais):
    '''
    Retorna el nombre del país con formato de título.

    Parámetros:
    pais (str): Nombre o código de país.

    Retorna:
    str: Nombre del país con formato de título.

    Ejemplo:
    >>> obtener_pais('chile')
    'Chile'

    >>> obtener_pais('cl')
    'Chile'
    '''
    return obtener_pais_para_url(pais).title().replace('+', ' ')


def validar_pais(pais):
    '''
    Verifica si el país ingresado existe en la API de la WCA.

    Parámetros:
    pais (str): Nombre o código de país.

    Retorna:
    bool: True si el país existe, False en caso contrario.
    '''
    paises = api_paises()
    nombres_paises = [p['name'].lower() for p in paises['items']]
    codigos_paises = [p['iso2Code'].lower() for p in paises['items']]
    pais = obtener_pais(pais).lower()
    es_valido = False
    if pais in nombres_paises or pais in codigos_paises:
        es_valido = True

    return es_valido


def cargar_traducciones():
    '''
    Carga las traducciones desde el archivo JSON.

    Parámetros:
    idioma (str): Idioma de las traducciones.

    Retorna:
    dict: Traducciones en formato JSON.
    '''
    try:
        with open(f'./json/mensajes.json', 'r', encoding='utf-8') as archivo:
            traducciones = json.load(archivo)
            return traducciones
    except FileNotFoundError:
        print(f'No se ha encontrado el archivo mensajes.json')
        return {}


def traducir(idioma, key):
    '''
    Retorna el texto traducido.

    Parámetros:
    idioma (str): Idioma de las traducciones.
    key (str): Llave del texto a traducir (se encuentra en los archivos JSON).

    Retorna:
    str: Texto traducido.
    '''
    traducciones = cargar_traducciones()
    # print(traducciones)
    if traducciones and key in traducciones:
        return traducciones[key][idioma]
    else:
        return f'No se ha encontrado la traducción para la llave {key}.'
    

def cargar_idiomas():
    '''
    Carga los idiomas disponibles desde el archivo mensajes.JSON

    Parámetros:
    None

    Retorna:
    dict: Idiomas en formato JSON.
    '''
    try:
        with open(f'./json/mensajes.json', 'r', encoding='utf-8') as archivo:
            traducciones = json.load(archivo)
            return traducciones['Languages']

    except FileNotFoundError:
        print(f'No se ha encontrado el archivo mensajes.json')
        return []


def validar_idioma(idioma):
    '''
    Verifica si el idioma ingresado existe en el archivo JSON.

    Parámetros:
    idioma (str): Idioma de las traducciones.

    Retorna:
    bool: True si el idioma existe, False en caso contrario.
    '''
    es_valido = False
    idiomas = cargar_idiomas()
    if idioma in idiomas.keys():
        es_valido = True
    return es_valido
