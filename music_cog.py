from yt_dlp import YoutubeDL as YouTubeDL
from discord import app_commands
from discord.ext import commands
import discord, math

class MusicCog(commands.Cog):
    def __init__(self, client):
        self.bot = client

        self.is_playing = False
        self.is_paused = False

        self.music_queue = []
        self.ytdl_options = {
            "format": "bestaudio",
            "noplaylist": "True"
        }
        self.ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1"
        }

        self.vc = None
    
    def search_youtube(self, query):
        with YouTubeDL(self.ytdl_options) as ytdl:
            try:
                info = ytdl.extract_info(f"ytsearch: {query}", download=False)
            except Exception as e:
                return(e)
        return({
            "source": info["entries"][0]["url"],
            "title": info["title"]
        })
    
    def play_next(self):
        if(len(self.music_queue) > 0):
            self.is_playing = True
            playing_url = self.music_queue[0][0]["source"]
            self.music_queue.pop(0)
            self.vc.play(
                discord.FFmpegPCMAudio(playing_url, **self.ffmpeg_options), 
                after=lambda e: self.play_next()
            )
        else:
            self.is_playing = False
    
    async def play_song(self, interaction: discord.Interaction):
        if(len(self.music_queue) > 0):
            self.is_playing = True
            playing_url = self.music_queue[0][0]["source"]

            if(self.vc == None or (not self.vc.is_connected())):
                self.vc = await self.music_queue[0][1].connect()
                if(self.vc == None or (not self.vc.is_connected())):
                    await interaction.response.send_message("Could not connect to voice channel")
                    return
            else:
                await self.vc.move_to(self.music_queue[0][1])
            
            self.music_queue.pop(0)

            self.vc.play(
                discord.FFmpegPCMAudio(playing_url, **self.ffmpeg_options), 
                after=lambda e: self.play_next()
            )

        else:
            self.is_playing = False
    
    @app_commands.command(name="play", description="play")
    async def play(self, interaction: discord.Interaction, query: str):
        voice_channel = interaction.user.voice.channel
        if(voice_channel is None):
            await interaction.response.send_message("Connect to a voice channel!", ephemeral=True)
        song = self.search_youtube(query)
        if(type(song) != dict):
            await interaction.response.send_message(str(song))
        else:
            await interaction.response.send_message("Song added to the queue!")
            self.music_queue.append([song, voice_channel])

            if(not self.is_playing):
                await self.play_song(interaction)
        
    
    @app_commands.command(name="pause", description="pause")
    async def pause(self, interaction: discord.Interaction):
        if(self.is_playing):
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
            await interaction.response.send_message("Paused.")
        else:
            await interaction.response.send_message("Cannot resume! (Not paused)", ephemeral=True)
    
    @app_commands.command(name="resume", description="resume")
    async def resume(self, interaction: discord.Interaction):
        if(self.is_playing):
            await interaction.response.send_message("Cannot pause! (Not playing)", ephemeral=True)
        else:
            self.is_playing = True
            self.is_paused = False
            self.vc.resume()
            await interaction.response.send_message("Resumed.")
    
    @app_commands.command(name="skip", description="skip")
    async def skip(self, interaction: discord.Interaction):
        if(self.vc == None or not self.vc):
            await interaction.response.send_message("Cannot skip! (Not in Voice Channel)", ephemeral=True)
        else:
            self.vc.stop()
            await self.play_song(interaction)
            await interaction.response.send_message("Skipped.")
        
    # @app_commands.command(name="queue", description="queue")
    # async def queue(self, interaction: discord.Interaction, page: int=1):
    #     queue_pages = int(math.ceil(len(self.music_queue) / 10))
    #     if(len(self.music_queue) < 1):
    #         await interaction.response.send_message("Qeueu is empty.", ephemeral=True)
    #         return
    #     if(page > queue_pages):
    #         await interaction.response.send_message(f"Queue page does not exist! (Only {queue_pages} pages)", ephemeral=True)
    #         return

    #     embed = discord.Embed(
    #         title=f"Queue",
    #         color=discord.Color.from_rgb(0, 255, 255)
    #     )
    #     embed.add_field(
    #         name=None,
    #         value=f"**Now Playing:** {self.music_queue[0][0]['title']}"
    #     )
    #     if(len(self.music_queue) == 1):
    #         embed.add_field(
    #             name=None,
    #             value="Queue is empty."
    #         )
    #     else:
    #         for i in range(10*page, min(10*(page+1), len(self.music_queue))):
    #             embed.add_field(
    #                 name=None,
    #                 value=f"**{i}.** {self.music_queue[i][0]['title']}"
    #             )
    #     embed.set_footer(
    #         text=f"Page {page}/{queue_pages}"
    #     )
    #     await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="clear", description="clear")
    async def clear(self, interaction: discord.Interaction):
        if(self.vc != None and self.is_playing):
            self.vc.stop()
        self.music_queue = []
        await interaction.response.send_message("Music queue cleared.")
    
    @app_commands.command(name="leave", description="leave")
    async def leave(self, interaction:discord.Interaction):
        self.is_playing = False
        self.is_paused = False
        self.music_queue = []
        await self.vc.disconnect()
        await interaction.response.send_message("Disconnected.")

    # youtube
    # youtube music
    # spotify
    # soundcloud