from yt_dlp import YoutubeDL as YouTubeDL
from discord import app_commands
from discord.ext import commands
import discord, math, asyncio, random

class MusicCog(commands.Cog):
    def __init__(self, client):
        self.bot = client

        # keep track of playing status
        self.is_playing = False
        self.is_paused = False

        # keep track of queue status
        self.music_queue = []
        self.now_playing = None
        self.text_channel = None

        # keep track of loop status
        self.loop_queue = []
        self.is_looping = False
        self.add_current_to_loop = True

        self.shuffle = False

        # options
        self.ytdl_options = {
            "format": "bestaudio",
            "noplaylist": "True"
        }
        self.ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1"
        }

        # keep track of VC
        self.vc = None
    
    # search yt
    def search_youtube(self, query, userid) -> dict:
        with YouTubeDL(self.ytdl_options) as ytdl:
            try:
                info = ytdl.extract_info(f"ytsearch: {query}", download=False)
            except Exception as e:
                return(e)
        return({
            "source": info["entries"][0]["url"],
            "title": info["title"],
            "video_title": info["entries"][0]["title"],
            "video_id": info["entries"][0]["id"],
            "thumbnail_url": info["entries"][0]["thumbnail"],
            "video_url": info["entries"][0]["webpage_url"],
            "channel": info["entries"][0]["channel"],
            "channel_url": info["entries"][0]["channel_url"],
            "requested_by": userid
        })

    # send update to channel when a new song starts playing
    async def send_update(self) -> None:
        embed = self.now_playing_embed("Now Playing", discord.Color.from_rgb(0, 255, 255), self.now_playing[0])
        await self.text_channel.send(embed=embed)
    
    # play next song
    async def play_next(self) -> None:
        if(len(self.music_queue) > 0 or self.is_looping):
            print(self.now_playing)
            self.is_playing = True
            if(self.shuffle):
                if(self.is_looping):
                    if(self.add_current_to_loop):
                        self.loop_queue.append(self.now_playing)
                    self.now_playing = self.loop_queue.pop(random.randint(0, len(self.loop_queue) - 1))
                else:
                    self.now_playing = self.music_queue.pop(random.randint(0, len(self.music_queue) - 1))
            else:
                # if looping, get from loop queue
                if(self.is_looping):
                    if(self.add_current_to_loop):
                        self.loop_queue.append(self.now_playing)
                    self.add_current_to_loop = True
                    if(len(self.loop_queue) > 0):
                        self.now_playing = self.loop_queue.pop(0)
                # else, get from normal queue
                else:
                    self.now_playing = self.music_queue.pop(0)
            playing_url = self.now_playing[0]["source"]
            self.vc.play(
                discord.FFmpegPCMAudio(playing_url, **self.ffmpeg_options),
                after=lambda x: self.bot.loop.create_task(self.play_next())
            )
            # update text channel
            await self.send_update()
        else:
            self.is_playing = False
    
    def now_playing_embed(self, title, color, song) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            color=color
        )
        embed.set_thumbnail(url=song["thumbnail_url"])
        embed.add_field(
            name="",
            value=f"**Query:** {song['title']}",
            inline=False
        )
        embed.add_field(
            name="",
            value=f"[{song['video_title'].title()}]({song['video_url']}) - [{song['channel']}]({song['channel_url']})",
            inline=False
        )
        embed.add_field(
            name="",
            value=f"Requested by <@{song['requested_by']}>",
            inline=False
        )
        return(embed)
    
    async def play_song(self, interaction: discord.Interaction) -> None:
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
            
            self.now_playing = self.music_queue.pop(0)

            self.vc.play(
                discord.FFmpegPCMAudio(playing_url, **self.ffmpeg_options), 
                after=lambda x: self.bot.loop.create_task(self.play_next())
            )
        else:
            self.is_playing = False
    
    @app_commands.command(name="play", description="play")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        voice_channel = interaction.user.voice.channel
        self.text_channel = interaction.channel
        if(voice_channel is None):
            await interaction.followup.send("Connect to a voice channel!", ephemeral=True)
        song = self.search_youtube(query, interaction.user.id)
        if(type(song) != dict):
            await interaction.followup.send(str(song))
        else:
            if(not self.is_playing):
                embed_title = "Now Playing"
                embed_color = discord.Color.from_rgb(0, 255, 255)
            else:
                embed_title = "Enqueued"
                embed_color = discord.Color.from_rgb(255, 0, 255)
            embed = self.now_playing_embed(embed_title, embed_color, song)
            if(self.is_playing):
                embed.add_field(
                    name="",
                    value=f"In position: {len(self.music_queue) + 1}"
                )
            await interaction.followup.send(embed=embed)
            self.music_queue.append([song, voice_channel])

            if(not self.is_playing):
                await self.play_song(interaction)
        
    
    @app_commands.command(name="pause", description="pause")
    async def pause(self, interaction: discord.Interaction) -> None:
        if(self.is_playing):
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
            await interaction.response.send_message("Paused.")
        else:
            await interaction.response.send_message("Cannot resume! (Not paused)", ephemeral=True)
    
    @app_commands.command(name="resume", description="resume")
    async def resume(self, interaction: discord.Interaction) -> None:
        if(self.is_playing):
            await interaction.response.send_message("Cannot pause! (Not playing)", ephemeral=True)
        else:
            self.is_playing = True
            self.is_paused = False
            self.vc.resume()
            await interaction.response.send_message("Resumed.")
    
    @app_commands.command(name="skip", description="skip")
    async def skip(self, interaction: discord.Interaction) -> None:
        if(self.vc == None or not self.vc):
            await interaction.response.send_message("Cannot skip! (Not in Voice Channel)", ephemeral=True)
        else:
            self.vc.stop()
            await interaction.response.send_message("Skipped.")
    
    @app_commands.command(name="shuffle", description="shuffle")
    async def shuffle(self, interaction: discord.Interaction) -> None:
        self.shuffle = not self.shuffle
        if(self.shuffle):
            await interaction.response.send_message("Queue is now shuffling.")
        else:
            await interaction.response.send_message("Queue is no longer shuffling.")
        
    @app_commands.command(name="queue", description="queue")
    async def queue(self, interaction: discord.Interaction, page: int=1) -> None:
        queue_pages = int(math.ceil(len(self.music_queue) / 10))
        if(len(self.music_queue) < 1):
            await interaction.response.send_message("Qeueu is empty.", ephemeral=True)
            return
        if(page > queue_pages or page < 1):
            await interaction.response.send_message(f"Queue page does not exist! (Only {queue_pages} pages)", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Queue",
            color=discord.Color.from_rgb(128, 0, 255)
        )
        if(self.shuffle):
            embed.add_field(
                name="",
                value="Queue is shuffling; this is not the order it will play in."
            )
        now_playing = self.now_playing[0]
        embed.add_field(
            name="Now Playing",
            value=f"[{now_playing['video_title']}]({now_playing['video_url']}) - [{now_playing['channel']}]({now_playing['channel_url']})\nRequested by <@{now_playing['requested_by']}>",
            inline=False
        )
        for i in range(10*(page - 1), min(10*page, len(self.music_queue))):
            item = self.music_queue[i][0]
            embed.add_field(
                name="",
                value=f"**{i + 1}.** [{item['video_title']}]({item['video_url']}) - [{item['channel']}]({item['channel_url']}) Requested by <@{item['requested_by']}>",
            inline=False
            )
        if(len(self.music_queue) > 10):
            embed.set_footer(
                text=f"Page {page}/{queue_pages}"
            )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="nowplaying", description="Now Playing")
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        title = "Now Playing"
        color = discord.Color.from_rgb(0, 255, 255)
        song = self.now_playing[0]
        embed = self.now_playing_embed(title, color, song)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="clear", description="clear")
    async def clear(self, interaction: discord.Interaction) -> None:
        if(self.vc != None and self.is_playing):
            self.vc.stop()
        self.music_queue = []
        self.loop_queue = []
        self.is_looping = False
        self.add_current_to_loop = True
        await interaction.response.send_message("Music queue cleared.")
    
    @app_commands.command(name="leave", description="leave")
    async def leave(self, interaction:discord.Interaction) -> None:
        self.is_playing = False
        self.is_paused = False
        self.music_queue = []
        await self.vc.disconnect()
        await interaction.response.send_message("Disconnected.")
    
    @app_commands.command(name="dequeue", description="remove")
    async def remove(self, interaction: discord.Interaction, position: int) -> None:
        if(position > len(self.music_queue)):
            await interaction.response.send_message(
                f"Only {len(self.music_queue)} items in queue.",
                ephemeral=True
            )
            return
        if(position < 1):
            await interaction.response.send_message(
                "Invalid queue position specified.",
                ephemeral=True
            )
            return
        removed = self.music_queue.pop(position - 1)
        embed = self.now_playing_embed("Removed from Queue", discord.Color.from_rgb(192, 0, 0), removed[0])
        await interaction.response.send_message(f"{removed[0]['video_title']} removed from queue.", embed=embed)
    
    @app_commands.command(name="loop", description="loop")
    async def loop(self, interaction: discord.Interaction, start_loop: int = 0, end_loop: int = 0) -> None:
        if(end_loop == 0):
            end_loop = start_loop
        if(self.is_looping == True and start_loop == 0 and end_loop == 0):
            await interaction.response.send_message("Stopped looping.")
            self.is_looping = False
            self.loop_queue = []
            return
        self.is_looping = True
        if(start_loop > 0):
            self.add_current_to_loop = False
        for i in range(start_loop, end_loop):
            self.loop_queue.append(self.music_queue[i])
        await interaction.response.send_message("Started looping.")
        # await self.loopqueue(interaction, 1)
    
    @app_commands.command(name="loopqueue", description="Loop queue")
    async def loopqueue(self, interaction: discord.Interaction, page: int = 1) -> None:
        queue_pages = int(math.ceil(len(self.loop_queue) / 10))
        if(not self.is_looping):
            await interaction.response.send_message("Not currently looping.", ephemeral=True)
            return
        if(len(self.loop_queue) < 1):
            await interaction.response.send_message("Loop qeueu is empty.", ephemeral=True)
            return
        if(page > queue_pages or page < 1):
            await interaction.response.send_message(f"Loop queue page does not exist! (Only {queue_pages} pages)", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Loop Queue",
            color=discord.Color.from_rgb(0, 255, 192)
        )
        if(self.shuffle):
            embed.add_field(
                name="",
                value="Queue is shuffling; this is not the order it will play in."
            )
        now_playing = self.now_playing[0]
        embed.add_field(
            name="Now Playing",
            value=f"[{now_playing['video_title']}]({now_playing['video_url']}) - [{now_playing['channel']}]({now_playing['channel_url']})\nRequested by <@{now_playing['requested_by']}>",
            inline=False
        )
        for i in range(10*(page - 1), min(10*page, len(self.loop_queue))):
            item = self.loop_queue[i][0]
            embed.add_field(
                name="",
                value=f"**{i + 1}.** [{item['video_title']}]({item['video_url']}) - [{item['channel']}]({item['channel_url']}) Requested by <@{item['requested_by']}>",
            inline=False
            )
        if(len(self.loop_queue) > 10):
            embed.set_footer(
                text=f"Page {page}/{queue_pages}"
            )
        await interaction.response.send_message(embed=embed)

    # youtube
    # youtube music
    # spotify
    # soundcloud