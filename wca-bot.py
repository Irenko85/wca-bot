import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import utils as utils

load_dotenv()  # Cargar variables de entorno

"""
Este módulo contiene el código principal del bot de Discord.
Posee los siguientes comandos y funciones:
    - verificar_torneos_nuevos: Verifica si hay torneos nuevos cada 12 horas y envía una notificación al canal #torneos en caso de encontrar nuevos torneos.
    - !torneos: Muestra los torneos actuales.
    - !logo: Envía una imagen con el logo del bot.

TODO:
    - Agregar funcionalidad al comando !torneos para que muestre los torneos de un país específico, ejemplo !torneos Argentina.
"""

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

# Función para verificar si hay torneos nuevos cada 12 horas
@tasks.loop(hours = 12)
async def verificar_torneos_nuevos():
    # Obtener el canal de Discord
    canal = bot.get_channel(int(CHANNEL_ID))
    utils.limpiar_base_de_datos()

    if canal:
        print("Verificando torneos nuevos...")
        # Obtener los torneos actuales
        torneos_actuales = utils.obtener_torneos(utils.URL)

        # Cargar los torneos ya guardados
        torneos_conocidos = utils.cargar_torneos_conocidos()

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
            for torneo in torneos_nuevos:
                utils.guardar_torneo(torneo)

        else:
            print('No hay torneos nuevos.')
            return

# Comando !torneos
@bot.command(name = 'torneos', help = 'Muestra los torneos actuales.')
async def mostrar_torneos(ctx, pais = 'Chile'):
    # Obtener los torneos actuales de la página de la WCA
    torneos = utils.obtener_torneos(utils.URL, pais)

    # Si hay torneos existentes, enviar mensaje con los torneos
    if len(torneos) > 0:
        mensaje = f'**{ctx.author.mention}, estos son los torneos actuales :eyes: :trophy::**\n\n'
        for torneo in torneos:
            mensaje += f'**Nombre:** {torneo["Nombre torneo"]}\n'
            mensaje += f'**Fecha:** {torneo["Fecha"]}\n'
            mensaje += f'**Lugar:** {torneo["Pais"]}, {torneo["Lugar"]}\n'
            mensaje += f'**URL:** {torneo["URL"]}\n\n'

        await ctx.send(mensaje)
    else:
        await ctx.send('No se han encontrado torneos.')

# Comando !logo
@bot.command(name = 'logo', help = 'Envía una imagen con el logo del bot.')
async def enviar_logo(ctx):
    await ctx.send('https://i.imgur.com/yscsmKO.jpeg')

if __name__ == '__main__':
    # Iniciar el bot
    bot.run(TOKEN)