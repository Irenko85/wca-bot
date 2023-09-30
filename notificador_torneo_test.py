import time
import discord
from discord.ext import commands, tasks
from bs4 import BeautifulSoup
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de entorno desde el archivo .env

# URLs con torneos actuales
URL = 'https://www.worldcubeassociation.org/competitions?region=Chile&search=&state=present&year=all+years&from_date=&to_date=&delegate=&display=list'
# URL = 'https://www.worldcubeassociation.org/competitions?region=Mexico&search=&state=present&year=all+years&from_date=&to_date=&delegate=&display=list'
WCA_URL = 'https://www.worldcubeassociation.org'

TOKEN = os.getenv('TOKEN') # Token del bot
GUILD_ID = os.getenv('GUILD_ID')  # ID del servidor de Discord
CHANNEL_ID = os.getenv('CHANNEL_ID')  # ID del canal de Discord

# Definir los intents requeridos
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Crear una instancia del bot con el prefijo ! para comandos y los intents definidos
bot = commands.Bot(command_prefix='!', intents=intents)

# Función ejecutada al iniciar el bot
@bot.event
async def on_ready():
    print(f'Bot iniciado correctamente. Conectado como {bot.user.name}')
    verificar_torneos_nuevos.start()  # Iniciar la tarea de verificación de torneos nuevos después de iniciar el bot

# Función para cargar los torneos guardados desde un archivo JSON
def cargar_torneos_conocidos(archivo):
    try:
        with open(archivo, 'r', encoding='utf-8') as archivo_json:
            return json.load(archivo_json)
    except FileNotFoundError:
        # Si el archivo no existe, crearlo con una lista vacía
        with open(archivo, 'w', encoding='utf-8') as archivo_json:
            json.dump([], archivo_json)
        return []

# Función para guardar los torneos en un archivo JSON
def guardar_torneos_en_json(torneos, archivo):
    try:
        with open(archivo, 'w', encoding='utf-8') as archivo_json:
            json.dump(torneos, archivo_json, indent=2, ensure_ascii=False)
        print('El archivo JSON se guardó correctamente.')

    except Exception as e:
        print('Error al guardar el archivo JSON:', e)

# Función para obtener los torneos desde la URL y retornar una lista de diccionarios con los torneos encontrados
def obtener_torneos(url):
    try:
        respuesta = requests.get(url)
        respuesta.raise_for_status()  # Genera una excepción si la solicitud no es exitosa
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
            fecha = fecha.get_text(strip=True)
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

# Función que se ejecuta cada 10 segundos para verificar si hay torneos nuevos (testeo), TODO: hacer que se ejecute a cierta hora del día, todos los días
@tasks.loop(seconds=10)
async def verificar_torneos_nuevos():
    print("Verificando torneos nuevos...")
    # Obtener el canal de Discord
    canal = bot.get_channel(int(CHANNEL_ID))
    if canal:
        # Obtener los torneos actuales
        torneos_actuales = obtener_torneos(URL)

        # Cargar los torneos ya guardados
        torneos_conocidos = cargar_torneos_conocidos('torneos.json')

        # Comparar los torneos actuales con los conocidos
        torneos_nuevos = [torneo for torneo in torneos_actuales if torneo not in torneos_conocidos]

        if len(torneos_nuevos) > 0:
            # Hay nuevos torneos disponibles, enviar notificación al canal de Discord
            mensaje = '¡**@everyone**, se han encontrado nuevos torneos! :tada:\n\n'
            for torneo in torneos_nuevos:
                mensaje += f'**Nombre:** {torneo["Nombre torneo"]}\n'
                mensaje += f'**Fecha:** {torneo["Fecha"]}\n'
                mensaje += f'**Lugar:** {torneo["Lugar"]}\n'
                mensaje += f'**URL:** {torneo["URL"]}\n\n'

            # Enviar el mensaje al canal de Discord
            await canal.send(mensaje)

            # Actualizar la lista de torneos guardados
            torneos_conocidos.extend(torneos_nuevos)
            guardar_torneos_en_json(torneos_conocidos, 'torneos.json')

        else:
            hora_actual = time.strftime('%H:%M:%S', time.localtime())
            mensaje = f'No se han encontrado torneos nuevos ({hora_actual}).'
            await canal.send(mensaje)

# Inicializar la lista de torneos conocidos
torneos_conocidos = cargar_torneos_conocidos('torneos.json')

if __name__ == "__main__":
    # Iniciar el bot
    bot.run(TOKEN)