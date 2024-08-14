import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import json
import os

#  --------------------------------------------------------------------------- UPDATE 1.1 ---------------------------------------------------------------------------
# What I added:
# 1) saving playlists to json files and reading saved jsons (for root only)
# 2) changed stop to skip and zatrzymaj to stop
# 3) added some visual details like bolding titles, playlist names exc.
# 4) added kolejka function which shows what is in given playlist

# What I am working on?:
# 1) deleting playlists from the database (i need to make it that only the creator of the playlist can delete his playlists)
# 2) transfering my databases from flashdisk to google disk
# 3) editing playlists
# 4) not leaking my bot's token

# Why can't I do that now?: Good quesion. Wait for the updates!

# --------------------------------------------------------------------------- UPDATE 1.1 ---------------------------------------------------------------------------

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
    'source_address': '0.0.0.0',  
    'retries': 10  
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
bot = commands.Bot(command_prefix=commands.when_mentioned_or("-"), description='', intents=intents)

playlists = {}
loop_mode = {}

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')
    print('------')
    

@bot.command(name='join', help='Dołącza do kanału głosowego')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f'*{ctx.author.name}*, nie jesteś na kanale głosowym!')
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
            await ctx.send(f'Odtwarzanie: **{player.title}**, link/prompt: {url}')
        except Exception as e:
            await ctx.send(f'Wystąpił błąd podczas próby odtworzenia utworu: {e}')
            print(f'Error details: {e}')

@bot.command(name='skip', help='Zatrzymuje odtwarzanie muzyki')
async def stop(ctx):
    if not ctx.voice_client:
        return await ctx.send('Nie jestem na żadnym kanale głosowym.')

    playlists[ctx.guild.id] = []
    loop_mode[ctx.guild.id] = False
    ctx.voice_client.stop()

@bot.command(name='stop', help='Pauzuje odtwarzanie muzyki')
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
        await ctx.send(f'Playlista o nazwie **{playlist_name}** już istnieje')
    else:
        playlists[playlist_name] = []
        await ctx.send(f'Utworzono playlistę: **{playlist_name}**')

@bot.command(name="zapisz_playliste", help="Zapisuje twoja playliste w systemie")
async def zapisz_playliste(ctx, playlist_name):
    if ctx.author.id == {Your discord ID (int)}:
        if playlist_name in playlists:
            if playlists[playlist_name] != []:
                if os.path.exists("[PATH]" + f"/{playlist_name}.json") == False:
                    with open("[PATH]" + f"/{playlist_name}.json", "w") as file:
                        json.dump(playlists[playlist_name], fp=file)
                        file.close()
                        await ctx.send(f"Pomyslnie zapisano playliste **{playlist_name}** w bazie")
                else:
                    await ctx.send("Taka playlista juz istnieje w bazie i nie mozesz jej nadpisac")
            else:
                await ctx.send(f"Jako iz dbam o pojemnosc mojego dysku nie moge zapisac twojej cienkiej playlisty z okraglym 0 utworow. *niezly gust*")
        else:
            await ctx.send(f"Playlista o nazwie **{playlist_name}** nie istnieje, wiec nie mozesz jej zapisac.")
    else:
        await ctx.send(f"Ciagle pracuje nad podlaczeniem bota do chmury, lecz aktualnie jeszcze nie jestem gotowy na dokonanie operacji. W tym momencie tylko root moze uzywac tej funkcjonalnosci.")
        
@bot.command(name='dodaj_do_playlisty', help='Dodaje utwór do playlisty')
async def add_to_playlist(ctx, playlist_name, *, url):
    if playlist_name not in playlists:
        await ctx.send(f'Playlista o nazwie **{playlist_name}** nie istnieje.')
    else:
        playlists[playlist_name].append(url)
        await ctx.send(f'Dodano utwór do playlisty: **{playlist_name}**')

@bot.command(name='usun_playliste', help='Usuwa istniejaca playliste')
async def delete_playlist(ctx, playlist_name):
    if playlist_name in playlists:
        playlists.pop(playlist_name)
        await ctx.send(f'Usunięto playlistę: **{playlist_name}**')
    else:
        await ctx.send(f'Playlista o nazwie **{playlist_name}** nie istnieje.')

#@bot.command(name="usun_z_bazy", help="Usuwa playliste z bazy") working on auth

@bot.command(name="kolejka", help="Pokazuje kolejke aktualnej playlisty")
async def kolejka(ctx, playlist_name):
    if playlist_name in playlists:
        await ctx.send(f"Zawartosc playlisty **{playlist_name}**: {"; ".join(playlists[playlist_name])}")
    else:
        await ctx.send("Ta playlista nie istnieje")

@bot.command(name="write_saved_playlist", help="Odtwarza zapisana playliste")
async def play_saved_playlist(ctx, playlist_name):
    if ctx.author.id == 781971452600909905:
        if playlist_name not in playlists:
            if os.path.exists("E:/Bot" + f"/{playlist_name}.json"):
                with open("E:/Bot" + f"/{playlist_name}.json", 'r') as file:
                    content = json.load(file)
                    playlists[playlist_name] = content
                    file.close()
                    await ctx.send(f"Wczytywanie playlisty **{playlist_name}** zakonczone powodzeniem")
            else:
                await ctx.send(f"Playlista o nazwie **{playlist_name}** nie jest zapisana w mojej bazie. Jesli chcesz dodac ja do bazy uzyj komendy zapisz_playliste")
        else:
            await ctx.send(f"Playlista o nazwie **{playlist_name}** jest obecna na sesji lokalniej. Jesli chcesz usunac lokalna wersje i wczytac nowa z bazy uzyj komendy usun_playliste")
    else:
        await ctx.send(f"Ciagle pracuje nad podlaczeniem bota do chmury, lecz aktualnie jeszcze nie jestem gotowy na dokonanie operacji. W tym momencie tylko root moze uzywac tej funkcjonalnosci.")
    
@bot.command(name='play_playlist', help='Odtwarza playlistę')
async def play_playlist(ctx, playlist_name):
    if playlist_name not in playlists or not playlists[playlist_name]:
        await ctx.send(f'Playlista o nazwie **{playlist_name}** nie istnieje lub jest pusta.')
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
        if playlist_name == None:
            await ctx.send("Zakonczono odtwarzanie utworu")
            return
        
        await ctx.send(f'Playlista **{playlist_name}** zakończona.')
        return

    url = playlists[playlist_name].pop(0) 
    player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
    playlists[playlist_name].append(url)
    ctx.voice_client.play(player, after=lambda e: bot.loop.create_task(check_queue(ctx, playlist_name)) if not e else print(f'**Błąd odtwarzania: {e}**'))
    await ctx.send(f'Odtwarzanie: **{player.title}**, link/prompt: {url}')


async def check_queue(ctx, playlist_name):
    if ctx.voice_client is not None and not ctx.voice_client.is_playing():
        await play_next_song(ctx, playlist_name)

TOKEN = '#'

bot.run(TOKEN)
