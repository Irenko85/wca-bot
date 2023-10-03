import time
import psycopg2
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

# Conectarse a la base de datos de PostgreSQL
DB_URL = os.getenv('DATABASE_URL')
DB_NAME = os.getenv('PGDATABASE')
DB_PORT = os.getenv('PGPORT')
DB_HOST = os.getenv('PGHOST')
DB_USER = os.getenv('PGUSER')
DB_PASSWORD = os.getenv('PGPASSWORD')

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

# Verificar los torneos guardados en la base de datos
def cargar_torneos_conocidos():
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute('SELECT * FROM torneos;')
        torneos = cur.fetchall()
        cur.close()
        conn.close()
        return torneos
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

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

# Función para verificar si hay torneos nuevos cada 12 horas
@tasks.loop(hours=24)
async def verificar_torneos_nuevos():
    print("Verificando torneos nuevos...")
    # Obtener el canal de Discord
    canal = bot.get_channel(int(CHANNEL_ID))
    if canal:
        # Obtener los torneos actuales
        torneos_actuales = obtener_torneos(URL)

        # Cargar los torneos ya guardados
        torneos_conocidos = cargar_torneos_conocidos()

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

            # Actualizar la base de datos con los nuevos torneos
            try:
                conn = db_conn()
                cur = conn.cursor()
                for torneo in torneos_nuevos:
                    cur.execute('INSERT INTO torneos (nombre, fecha, pais, lugar, url) VALUES (%s, %s, %s, %s, %s);', (torneo['Nombre torneo'], torneo['Fecha'], 'Chile', torneo['Lugar'], torneo['URL']))
                conn.commit()
                cur.close()
                conn.close()
            except (Exception, psycopg2.DatabaseError) as error:
                print(error)

        else:
            return


@bot.command(name='torneos', help='Muestra los torneos actuales.')
async def mostrar_torneos(ctx):
    torneos = obtener_torneos(URL)
    test = cargar_torneos_conocidos()
    print(test)
    if len(torneos) > 0:
        mensaje = f'**{ctx.author.mention}, estos son los torneos actuales 🏆:**\n\n'
        for torneo in torneos:
            mensaje += f'**Nombre:** {torneo["Nombre torneo"]}\n'
            mensaje += f'**Fecha:** {torneo["Fecha"]}\n'
            mensaje += f'**Lugar:** {torneo["Lugar"]}\n'
            mensaje += f'**URL:** {torneo["URL"]}\n\n'

        await ctx.send(mensaje)
    else:
        await ctx.send('No se han encontrado torneos.')

def db_conn():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

if __name__ == "__main__":
    # Iniciar el bot
    bot.run(TOKEN)
