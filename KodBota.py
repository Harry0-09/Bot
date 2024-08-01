import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio

# Ustawienia yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # ipv6 addresses cause issues sometimes
    'retries': 10  # Adding retries to handle temporary network issues
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or("-"), description='Jakby chyba ok', intents=intents)

playlists = {}
loop_mode = {}

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command(name='join', help='Dołącza do kanału głosowego')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f'{ctx.author.name}, nie jesteś na kanale głosowym!')
        return
    else:
        channel = ctx.message.author.voice.channel

    await channel.connect()

@bot.command(name='opusc_nas', help='Odlącza od kanału głosowego')
async def leave(ctx):
    if not ctx.voice_client:
        return await ctx.send('Nie jestem na żadnym kanale głosowym.')

    await ctx.voice_client.disconnect()
    await ctx.send("Aha czyli juz mnie nie lubicie? Ok ;( ahh")

@bot.command(name='play', help='Odtwarza muzykę z YouTube')
async def play(ctx, *, url):
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send('Musisz być na kanale głosowym, aby użyć tej komendy.')
            return

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            if ctx.guild.id not in playlists:
                playlists[ctx.guild.id] = []
            playlists[ctx.guild.id].append(url)
            ctx.voice_client.play(player, after=lambda e: print(f'Błąd odtwarzania: {e}') if e else bot.loop.create_task(check_queue(ctx, None)))
            await ctx.send(f'Odtwarzanie: {player.title}, link: {url}')
        except Exception as e:
            await ctx.send(f'Wystąpił błąd podczas próby odtworzenia utworu: {e}')
            print(f'Error details: {e}')

@bot.command(name='stop', help='Zatrzymuje odtwarzanie muzyki')
async def stop(ctx):
    if not ctx.voice_client:
        return await ctx.send('Nie jestem na żadnym kanale głosowym.')

    playlists[ctx.guild.id] = []
    loop_mode[ctx.guild.id] = False
    ctx.voice_client.stop()

@bot.command(name='zatrzymaj', help='Pauzuje odtwarzanie muzyki')
async def pause(ctx):
    if not ctx.voice_client.is_playing():
        return await ctx.send('Muzyka nie jest odtwarzana.')

    ctx.voice_client.pause()

@bot.command(name='wznow', help='Wznawia odtwarzanie muzyki')
async def resume(ctx):
    if not ctx.voice_client.is_paused():
        return await ctx.send('Muzyka nie jest zapauzowana.')

    ctx.voice_client.resume()

@bot.command(name='stworz_playliste', help='Tworzy nową playlistę')
async def create_playlist(ctx, playlist_name):
    if playlist_name in playlists:
        await ctx.send(f'Playlista o nazwie {playlist_name} już istnieje.')
    else:
        playlists[playlist_name] = []
        await ctx.send(f'Utworzono playlistę: {playlist_name}')

@bot.command(name='dodaj_do_playlisty', help='Dodaje utwór do playlisty')
async def add_to_playlist(ctx, playlist_name, *, url):
    if playlist_name not in playlists:
        await ctx.send(f'Playlista o nazwie {playlist_name} nie istnieje.')
    else:
        playlists[playlist_name].append(url)
        await ctx.send(f'Dodano utwór do playlisty: {playlist_name}')

@bot.command(name='usun_playliste', help='Usuwa istniejaca playliste')
async def delete_playlist(ctx, playlist_name):
    if playlist_name in playlists:
        playlists.pop(playlist_name)
        await ctx.send(f'Usunięto playlistę: {playlist_name}')
    else:
        await ctx.send(f'Playlista o nazwie {playlist_name} nie istnieje.')

@bot.command(name='play_playlist', help='Odtwarza playlistę')
async def play_playlist(ctx, playlist_name):
    if playlist_name not in playlists or not playlists[playlist_name]:
        await ctx.send(f'Playlista o nazwie {playlist_name} nie istnieje lub jest pusta.')
        return

    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send('Musisz być na kanale głosowym, aby użyć tej komendy.')
            return

    loop_mode[ctx.guild.id] = True
    await play_next_song(ctx, playlist_name)

async def play_next_song(ctx, playlist_name):
    if playlist_name not in playlists or not playlists[playlist_name]:
        await ctx.send(f'Playlista {playlist_name} zakończona.')
        return

    url = playlists[playlist_name].pop(0) 
    player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
    playlists[playlist_name].append(url)
    ctx.voice_client.play(player, after=lambda e: bot.loop.create_task(check_queue(ctx, playlist_name)) if not e else print(f'Błąd odtwarzania: {e}'))
    await ctx.send(f'Odtwarzanie: {player.title}, link: {url}')


async def check_queue(ctx, playlist_name):
    if ctx.voice_client is not None and not ctx.voice_client.is_playing():
        await play_next_song(ctx, playlist_name)

# Twój token bota
TOKEN = '#'

bot.run(TOKEN)
