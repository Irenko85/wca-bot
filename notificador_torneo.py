import requests
import json
import os
import discord
from discord.ext import commands
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv() # Cargar variables de entorno desde el archivo .env

# URLs con torneos actuales
URL = 'https://www.worldcubeassociation.org/competitions?region=Chile&search=&state=present&year=all+years&from_date=&to_date=&delegate=&display=list'
WCA_URL = 'https://www.worldcubeassociation.org'

# Obtener token del bot y el ID del servidor de Discord desde el archivo .env
TOKEN = os.getenv('TOKEN')
GUILD_ID = os.getenv('GUILD_ID') # ID del servidor de Discord

# Definir los intents requeridos 
intent = discord.Intents.default()
intent.messages = True
intent.message_content = True

# Crear una instancia del bot con el prefijo ! para comandos y los intents definidos
bot = commands.Bot(command_prefix='!', intents=intent)

# Función ejecutada al iniciar el bot
@bot.event
async def on_ready():
    print(f'Bot iniciado correctamente. Conectado como {bot.user.name}')

# Comando !torneo, envía un mensaje con los torneos actuales
@bot.command()
async def torneo(ctx):
    # Obtener los torneos actuales
    torneos = obtener_torneos(URL)
    
    if len(torneos) > 0:
        # Mensaje que enviará el bot al canal de Discord
        mensaje = '**Torneos actuales:\n**'
        for torneo in torneos:
            mensaje += f'{torneo["Nombre torneo"]} - {torneo["Fecha"]} - {torneo["Lugar"]} - {torneo["URL"]}\n'
        
        # Enviar el mensaje al canal de Discord
        await ctx.send(mensaje)
    else:
        await ctx.send('No se encontraron torneos actuales.')

# Función que obtiene los torneos desde la URL y retorna una lista de diccionarios con los torneos encontrados
def obtener_torneos(url):
    try:
        respuesta = requests.get(url)
        respuesta.raise_for_status()  # Genera una excepción si la solicitud no es exitosa
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        elementos_competencia = soup.find_all('span', class_='competition-info')
        elementos_fecha = soup.find_all('span', class_='date')
        elementos_lugar = soup.find_all('div', class_='location')
        
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

# Función que guarda los torneos en un archivo JSON    
def guardar_torneos_en_json(torneos, archivo):
    try:
        with open(archivo, 'w', encoding='utf-8') as archivo_json:
            json.dump(torneos, archivo_json, indent=2, ensure_ascii=False)
        print('El archivo JSON se guardó correctamente.')

    except Exception as e:
        print('Error al guardar el archivo JSON:', e)

# Iniciar el bot
if __name__ == "__main__":
    bot.run(TOKEN)

# if respuesta.status_code == 200:
#     soup = BeautifulSoup(respuesta.text, 'html.parser')
#     elementos_competencia = soup.find_all('span', class_='competition-info')
#     elementos_fecha = soup.find_all('span', class_='date')
#     elementos_lugar = soup.find_all('div', class_='location')
#     torneos = []

#     for competencia, fecha, lugar in zip(elementos_competencia, elementos_fecha, elementos_lugar):
#         enlace = competencia.find('a')
#         nombre_torneo = enlace.text.strip()
#         url = WCA_URL + enlace['href']
#         fecha = fecha.get_text(strip=True)
#         lugar = lugar.get_text(strip=True).replace('Chile, ', '')

#         torneo = {
#             "Nombre torneo": nombre_torneo,
#             "URL": url,
#             "Fecha": fecha,
#             "Lugar": lugar
#         }

#         torneos.append(torneo)
#     try:
#         with open('torneos.json', 'w', encoding='utf-8') as archivo:
#             json.dump(torneos, archivo, indent=2, ensure_ascii=False)
#         print('El archivo JSON se guardó correctamente.')

#     except Exception as e:
#         print('Error al guardar el archivo JSON.', e)

#     torneos_actuales = []
#     with open('torneos.json', 'r', encoding='utf-8') as archivo:
#         torneos_actuales = json.load(archivo)

#     # Comparar las listas de torneos
#     torneos_nuevos = [torneo for torneo in torneos if torneo not in torneos_actuales]

#     if len(torneos_nuevos) > 0:
#         print('Hay nuevos torneos disponibles.')
#         for torneo in torneos_nuevos:
#             print(torneo)

# else:
#     print('Error con la petición.')