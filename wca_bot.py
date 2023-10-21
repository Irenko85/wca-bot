import discord
from discord.ext import commands, tasks
import os
from datetime import datetime
from dotenv import load_dotenv
import utils as utils

load_dotenv()  # Cargar variables de entorno

"""
Este módulo contiene el código principal del bot de Discord.
Posee los siguientes comandos y funciones:
    - verificar_torneos_nuevos: Verifica si hay torneos nuevos cada 12 horas y envía una notificación al canal #torneos en caso de encontrar nuevos torneos.
    - !torneos [pais]: Envía un mensaje embed con los torneos actuales del país dado, en caso de no especificar un país, se muestran los torneos de Chile.
    - !logo: Envía una imagen con el logo del bot.
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

# Función para settear el país por defecto para uso del bot
@bot.command(name='set-country', help='Settea el país por defecto. Ejemplo: !set-country Chile')
async def set_country(ctx, pais):
    if not pais:
        await ctx.send('No se ha ingresado ningún país.')
        return
    if not utils.validar_pais(pais):
        await ctx.send('El país ingresado no es válido.')
        return
    pais = pais.lower().capitalize()
    utils.pais_default = pais
    await ctx.send(f'Se ha cambiado el país por defecto a {utils.pais_default}.')

# Función para verificar si hay torneos nuevos cada 12 horas
@tasks.loop(hours=12)
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
            print('Se han encontrado torneos nuevos.')
            # Enviar mensaje al canal de Discord
            vista = VistaPaginacion()
            vista.torneos = torneos_nuevos
            mencion = ':tada: **¡@everyone, se han encontrado nuevos torneos!** :tada:\n\n'
            embeds_nuevos_torneos = vista.crear_embed_notificacion(torneos_nuevos)
            await canal.send(mencion, embeds=embeds_nuevos_torneos)

            # Actualizar la base de datos con los nuevos torneos
            for torneo in torneos_nuevos:
                utils.guardar_torneo(torneo)

        else:
            print('No hay torneos nuevos.')
            return

# Comando !test
@bot.command(name='test', help='Muestra los torneos actuales.')
async def mostrar_torneos(ctx, pais='Chile'):
    # Obtener los torneos actuales de la página de la WCA
    torneos = utils.obtener_torneos(utils.URL, pais)

    # Si hay torneos existentes, enviar mensaje con los torneos
    if len(torneos) > 0:
        _pais = utils.obtener_pais(pais)
        mensaje = f'**{ctx.author.mention}, estos son los torneos actuales en {_pais} :eyes: :trophy::**\n\n'
        for torneo in torneos:
            mensaje += f'**{torneos.index(torneo) + 1}.**\n'
            mensaje += f'**Nombre:** {torneo["Nombre torneo"]}\n'
            if torneo["Fecha inicio"] == torneo["Fecha fin"]:
                mensaje += f'**Fecha:** {torneo["Fecha inicio"]}\n'
            else:
                mensaje += f'**Fecha de inicio:** {torneo["Fecha inicio"]}\n'
                mensaje += f'**Fecha de término:** {torneo["Fecha fin"]}\n'
            mensaje += f'**Lugar:** {torneo["Lugar"]}\n'
            mensaje += f'**URL:** {torneo["URL"]}\n\n'

        # Enviar mensaje al canal de Discord
        await ctx.send(mensaje)
    else:
        await ctx.send('No se han encontrado torneos.')

# Comando !logo
@bot.command(name='logo', help='Envía una imagen con el logo del bot.')
async def enviar_logo(ctx):
    embed = discord.Embed(title='WCA Bot Notifier logo', color=discord.Color.blue())
    await ctx.send(embed=embed.set_image(url='https://i.imgur.com/yscsmKO.jpeg'))

# Comando !torneos [pais] para enviar un mensaje embed con los torneos actuales del país dado
@bot.command(name='torneos', help='Muestra un mensaje con los torneos actuales del país dado.')
async def torneos(ctx, pais='Chile'):
    torneos = utils.obtener_torneos(utils.URL, pais)
    pais = utils.obtener_pais(pais)
    vista = VistaPaginacion()
    vista.torneos = torneos
    vista.pais = pais
    await vista.enviar(ctx)

class VistaPaginacion(discord.ui.View):
    # Empezar en la primera pagina
    pagina_actual = 1
    # Cada página tendrá 3 torneos visibles
    separador = 3

    # Función para enviar el mensaje embed con los torneos cuando se usa el comando !torneos
    async def enviar(self, ctx):
        self.message = await ctx.send(view=self)
        await self.actualizar_msg_torneos(self.torneos[:self.separador])

    # Función para enviar una notificación cuando se encuentran nuevos torneos
    async def enviar_notificacion(self, ctx):
        self.message = await ctx.send(view=self)

    # Función para habilitar/deshabilitar botones en casos bordes de paginación
    def actualizar_botones(self):
        if self.pagina_actual == 1:
            self.primera_pagina.disabled = True
            self.anterior.disabled = True
        else:
            self.primera_pagina.disabled = False
            self.anterior.disabled = False
        if self.pagina_actual == (self.separador + len(self.torneos) - 1) // self.separador:
            self.ultima_pagina.disabled = True
            self.siguiente.disabled = True
        else:
            self.ultima_pagina.disabled = False
            self.siguiente.disabled = False
        if (len(self.torneos) <= 3):
            self.primera_pagina.disabled = True
            self.anterior.disabled = True
            self.ultima_pagina.disabled = True
            self.siguiente.disabled = True

    # Función para crear el mensaje embed con los torneos
    def crear_embed_torneo(self, torneos):
        # Crear el mensaje embed
        embed = discord.Embed(title=f':trophy: Estos son los torneos actuales en {self.pais} :trophy:', color=discord.Color.blue())
        # Agregar el footer
        embed.set_footer(text='WCA Notifier Bot', icon_url='https://i.imgur.com/yscsmKO.jpeg')

        # Caso en el que no se encuentren torneos
        if not torneos:
            embed.add_field(name='No se han encontrado torneos.', value='\u200b', inline=False)
            return embed

        # Caso en el que sí hay torneos
        for torneo in torneos:
            # Formatear las fechas para que sean mas legibles
            _fecha_inicio = torneo['Fecha inicio'].strftime('%d/%m/%Y')
            _fecha_fin = torneo['Fecha fin'].strftime('%d/%m/%Y')

            embed.add_field(name=torneo['Nombre torneo'], value=torneo['URL'], inline=False)
            embed.add_field(name=':world_map: ' + 'Lugar', value=torneo['Lugar'], inline=True)
            
            # Si la fecha de inicio y fin son iguales, el torneo dura solo un día
            if torneo['Fecha inicio'] == torneo['Fecha fin']:
                embed.add_field(name=':calendar: ' + 'Fecha', value=_fecha_inicio, inline=True)

            # En otro caso, el torneo dura más de un día y se agrega al mensaje la fecha de inicio y fecha de término
            else:
                embed.add_field(name=':calendar: ' + 'Fecha de inicio', value=_fecha_inicio, inline=True)
                embed.add_field(name=':calendar: ' + 'Fecha de término', value=_fecha_fin, inline=True)
            
            # Si no es el ultimo torneo, agregar un separador
            if torneos.index(torneo) != len(torneos) - 1:
                embed.add_field(name='', value='\u200b', inline=False)
        
        # En caso de tener menos de 3 torneos, actualizar el total de páginas
        if (len(self.torneos) <= 3):
            total_paginas = 1
        else:
            total_paginas = (self.separador + len(self.torneos) - 1) // self.separador
        
        # Número de página actual de un total de páginas
        embed.add_field(name='\u200b', value=f'**Página {self.pagina_actual} de {total_paginas}**', inline=False)
        
        return embed
    
    # Función para actualizar el mensaje embed una vez se interactúa con un botón
    async def actualizar_msg_torneos(self, torneos):
        self.actualizar_botones()
        await self.message.edit(embed=self.crear_embed_torneo(torneos), view=self)

    # Función para crear un array con los nuevos torneos encontrados en formato embed
    def crear_embed_notificacion(self, torneos):
        embed_torneos = []        
        for torneo in torneos:
            # Crear el mensaje embed
            embed = discord.Embed(color=discord.Color.blue())
            embed.set_thumbnail(url='https://i.imgur.com/yscsmKO.jpeg')
            embed.set_footer(text='WCA Notifier Bot', icon_url='https://i.imgur.com/yscsmKO.jpeg')

            # Formatear las fechas para que sean mas legibles
            _fecha_inicio = torneo['Fecha inicio'].strftime('%d/%m/%Y')
            _fecha_fin = torneo['Fecha fin'].strftime('%d/%m/%Y')

            # Agregar los datos del torneo al mensaje embed
            embed.add_field(name=torneo['Nombre torneo'], value=torneo['URL'], inline=False)
            embed.add_field(name=':world_map: ' + 'Lugar', value=torneo['Lugar'], inline=True)
            if torneo['Fecha inicio'] == torneo['Fecha fin']:
                embed.add_field(name=':calendar: ' + 'Fecha', value=_fecha_inicio, inline=True)
            else:
                embed.add_field(name=':calendar: ' + 'Fecha de inicio', value=_fecha_inicio, inline=True)
                embed.add_field(name=':calendar: ' + 'Fecha de término', value=_fecha_fin, inline=True)
            
            # Agregarlo al arreglo
            embed_torneos.append(embed)

        return embed_torneos
    
    # Botón que te lleva a la primera página
    @discord.ui.button(label='Primera', style=discord.ButtonStyle.primary, emoji='⏮️')
    async def primera_pagina(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.pagina_actual = 1
        await self.actualizar_msg_torneos(self.torneos[:self.separador])

    # Botón que te lleva a la página anterior
    @discord.ui.button(label='Anterior', style=discord.ButtonStyle.green, emoji='⬅️')
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.pagina_actual -= 1
        hasta = self.pagina_actual * self.separador
        desde = hasta - self.separador
        await self.actualizar_msg_torneos(self.torneos[desde:hasta])

    # Botón que te lleva a la página siguiente
    @discord.ui.button(label='Siguiente', style=discord.ButtonStyle.green, emoji='➡️')
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.pagina_actual += 1
        hasta = self.pagina_actual * self.separador
        desde = hasta - self.separador
        await self.actualizar_msg_torneos(self.torneos[desde:hasta])

    # Botón que te lleva a la última página
    @discord.ui.button(label='Última', style=discord.ButtonStyle.primary, emoji='⏭️')
    async def ultima_pagina(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.pagina_actual = (self.separador + len(self.torneos) - 1) // self.separador
        hasta = self.pagina_actual * self.separador
        desde = hasta - self.separador
        await self.actualizar_msg_torneos(self.torneos[desde:])

if __name__ == '__main__':
    # Iniciar el bot
    bot.run(TOKEN)