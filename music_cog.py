from yt_dlp import YoutubeDL as YouTubeDL
from discord import app_commands
from discord.ext import commands
import discord, math, asyncio, random

class MusicCog(commands.Cog):
    def __init__(self, client):
        self.bot = client

        # # keep track of playing status
        # guild_data["is_playing"] = False
        # self.is_paused = False

        # # keep track of queue status
        # self.music_queue = []
        # self.now_playing = None
        # self.text_channel = None

        # # keep track of loop status
        # self.loop_queue = []
        # self.is_looping = False
        # self.add_current_to_loop = True

        # self.shuffle = False

        self.guild_data = {}

        # options
        self.ytdl_options = {
            "format": "bestaudio",
            "noplaylist": "True"
        }
        self.ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1"
        }

        # keep track of VC
        # self.vc = None
    
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
    async def send_update(self, guild_id: int) -> None:
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            return
        embed = self.now_playing_embed("Now Playing", discord.Color.from_rgb(0, 255, 255), guild_data["now_playing"][0])
        await guild_data["text_channel"].send(embed=embed)
    
    # play next song
    async def play_next(self, guild_id: int) -> None:
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            return
        if(not guild_data["vc"].is_connected()):
            del guild_data
            return
        if(len(guild_data["music_queue"]) > 0 or guild_data["is_looping"]):
            guild_data["is_playing"] = True
            if(guild_data["shuffle"]):
                if(guild_data["is_looping"]):
                    if(guild_data["add_current_to_loop"]):
                        guild_data["loop_queue"].append(guild_data["now_playing"])
                    guild_data["now_playing"] = guild["loop_queue"].pop(random.randint(0, len(guild_data["loop_queue"]) - 1))
                else:
                    guild_data["now_playing"] = guild_data["music_queue"].pop(random.randint(0, len(guild_data["music_queue"]) - 1))
            else:
                # if looping, get from loop queue
                if(guild_data["is_looping"]):
                    if(guild_data["add_current_to_loop"]):
                        guild_data["loop_queue"].append(guild_data["now_playing"])
                    guild_data["add_current_to_loop"] = True
                    if(len(guild_data["loop_queue"]) > 0):
                        guild_data["now_playing"] = guild_data["loop_queue"].pop(0)
                # else, get from normal queue
                else:
                    guild_data["now_playing"] = guild_data["music_queue"].pop(0)
            playing_url = guild_data["now_playing"][0]["source"]
            guild_data["vc"].play(
                discord.FFmpegPCMAudio(playing_url, **self.ffmpeg_options),
                after=lambda x: self.bot.loop.create_task(self.play_next(guild_id))
            )
            # update text channel
            await self.send_update(guild_id)
        else:
            guild_data["is_playing"] = False
    
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
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            return
        if(len(guild_data["music_queue"]) > 0):
            guild_data["is_playing"] = True
            playing_url = guild_data["music_queue"][0][0]["source"]

            if(guild_data["vc"] == None or (not guild_data["vc"].is_connected())):
                voice_channel = guild_data["music_queue"][0][1]
                can_join = voice_channel.permissions_for(interaction.guild.me).connect
                can_play = voice_channel.permissions_for(interaction.guild.me).speak
                if(not all([can_join, can_play])):
                    await interaction.followup.send("Cannot connect to voice channel (insufficient permissions).", ephemeral=True)
                    del guild_data
                    return
                guild_data["vc"] = await guild_data["music_queue"][0][1].connect()
                # guild_data["vc"] = discord.VoiceClient(self.bot, guild_data["music_queue"][0][1])
                # await guild_data["vc"].connect(timeout=300.0, reconnect=False)
            else:
                await guild_data["vc"].move_to(guild_data["music_queue"][0][1])
            
            guild_data["now_playing"] = guild_data["music_queue"].pop(0)

            guild_data["vc"].play(
                discord.FFmpegPCMAudio(playing_url, **self.ffmpeg_options), 
                after=lambda x: self.bot.loop.create_task(self.play_next(guild_id))
            )
        else:
            guild_data["is_playing"] = False

    @app_commands.command(name="play", description="play")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        voice_channel = interaction.user.voice.channel
        if(voice_channel is None):
            await interaction.followup.send("Connect to a voice channel!", ephemeral=True)
            return
        song = self.search_youtube(query, interaction.user.id)
        if(interaction.guild.id not in self.guild_data.keys()):
            self.guild_data[interaction.guild.id] = {
                "is_playing": False,
                "is_paused": False,
                "music_queue": [],
                "now_playing": None,
                "text_channel": interaction.channel,
                "loop_queue": [],
                "is_looping": False,
                "add_current_to_loop": True,
                "shuffle": False,
                "vc": None
            }
        guild_data = self.guild_data[interaction.guild.id]
        if(type(song) != dict):
            await interaction.followup.send(str(song))
        else:
            if(not guild_data["is_playing"]):
                embed_title = "Now Playing"
                embed_color = discord.Color.from_rgb(0, 255, 255)
            else:
                embed_title = "Enqueued"
                embed_color = discord.Color.from_rgb(255, 0, 255)
            embed = self.now_playing_embed(embed_title, embed_color, song)
            if(guild_data["is_playing"]):
                embed.add_field(
                    name="",
                    value=f"In position: {len(guild_data['music_queue']) + 1}"
                )
            await interaction.followup.send(embed=embed)
            guild_data["music_queue"].append([song, voice_channel])

            if(not guild_data["is_playing"]):
                await self.play_song(interaction)
        
    
    @app_commands.command(name="pause", description="pause")
    async def pause(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        if(guild_data["is_playing"]):
            guild_data["is_playing"] = False
            guild_data["is_paused"] = True
            guild_data["vc"].pause()
            await interaction.response.send_message("Paused.")
        else:
            await interaction.response.send_message("Cannot pause! (Not playing)", ephemeral=True)
    
    @app_commands.command(name="resume", description="resume")
    async def resume(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        if(guild_data["is_playing"]):
            await interaction.response.send_message("Cannot resume! (Not paused)", ephemeral=True)
        else:
            guild_data["is_playing"] = True
            guild_data["is_paused"] = False
            guild_data["vc"].resume()
            await interaction.response.send_message("Resumed.")
    
    @app_commands.command(name="skip", description="skip")
    async def skip(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        if(guild_data["vc"] is None or not guild_data["vc"]):
            await interaction.response.send_message("Cannot skip! (Not in Voice Channel)", ephemeral=True)
        else:
            guild_data["vc"].stop()
            await interaction.response.send_message("Skipped.")
    
    @app_commands.command(name="shuffle", description="shuffle")
    async def shuffle(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        guild_data["shuffle"] = not guild_data["shuffle"]
        if(guild_data["shuffle"]):
            await interaction.response.send_message("Queue is now shuffling.")
        else:
            await interaction.response.send_message("Queue is no longer shuffling.")
        
    @app_commands.command(name="queue", description="queue")
    async def queue(self, interaction: discord.Interaction, page: int=1) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        queue_pages = int(math.ceil(len(guild_data["music_queue"]) / 10))
        if(queue_pages == 0):
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        if(page > queue_pages or page < 1):
            await interaction.response.send_message(f"Queue page does not exist! (Only {queue_pages} pages)", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Queue",
            color=discord.Color.from_rgb(128, 0, 255)
        )
        if(guild_data["shuffle"]):
            embed.add_field(
                name="",
                value="Queue is shuffling; this is not the order it will play in."
            )
        now_playing = guild_data["now_playing"][0]
        embed.add_field(
            name="Now Playing",
            value=f"[{now_playing['video_title']}]({now_playing['video_url']}) - [{now_playing['channel']}]({now_playing['channel_url']})\nRequested by <@{now_playing['requested_by']}>",
            inline=False
        )
        for i in range(10*(page - 1), min(10*page, len(guild_data["music_queue"]))):
            item = guild_data["music_queue"][i][0]
            embed.add_field(
                name="",
                value=f"**{i + 1}.** [{item['video_title']}]({item['video_url']}) - [{item['channel']}]({item['channel_url']}) Requested by <@{item['requested_by']}>",
                inline=False
            )
        if(len(guild_data["music_queue"]) > 10):
            embed.set_footer(
                text=f"Page {page}/{queue_pages}"
            )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="nowplaying", description="Now Playing")
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        title = "Now Playing"
        color = discord.Color.from_rgb(0, 255, 255)
        song = guild_data["now_playing"][0]
        embed = self.now_playing_embed(title, color, song)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="clear", description="clear")
    async def clear(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        if(guild_data["vc"] and guild_data["vc"].is_connected() and guild_data["is_playing"]):
            guild_data["vc"].stop()
        guild_data["music_queue"] = []
        guild_data["loop_queue"] = []
        guild_data["is_looping"] = False
        guild_data["add_current_to_loop"] = True
        await interaction.response.send_message("Music queue cleared.")
    
    @app_commands.command(name="leave", description="leave")
    async def leave(self, interaction:discord.Interaction) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        guild_data["is_playing"] = False
        guild_data["is_paused"] = False
        guild_data["music_queue"] = []
        if(guild_data["vc"].is_connected()):
            await guild_data["vc"].disconnect()
        del self.guild_data[guild_id]
        await interaction.response.send_message("Disconnected.")
    
    @app_commands.command(name="dequeue", description="remove")
    async def remove(self, interaction: discord.Interaction, position: int) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data or guild_data["vc"] is None or not guild_data["vc"].is_connected()):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        if(position > len(guild_data["music_queue"])):
            await interaction.response.send_message(
                f"Only {len(guild_data['music_queue'])} items in queue.",
                ephemeral=True
            )
            return
        if(position < 1):
            await interaction.response.send_message(
                "Invalid queue position specified.",
                ephemeral=True
            )
            return
        removed = guild_data["music_queue"].pop(position - 1)
        embed = self.now_playing_embed("Removed from Queue", discord.Color.from_rgb(192, 0, 0), removed[0])
        await interaction.response.send_message(f"{removed[0]['video_title']} removed from queue.", embed=embed)
    
    @app_commands.command(name="loop", description="loop")
    async def loop(self, interaction: discord.Interaction, start_loop: int = 0, end_loop: int = 0) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data or guild_data["vc"] is None or not guild_data["vc"].is_connected()):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        if(end_loop == 0):
            end_loop = start_loop
        if(guild_data["is_looping"] == True and start_loop == 0 and end_loop == 0):
            await interaction.response.send_message("Stopped looping.")
            guild_data["is_looping"] = False
            guild_data["loop_queue"] = []
            return
        guild_data["is_looping"] = True
        if(start_loop > 0):
            guild_data["add_current_to_loop"] = False
        for i in range(start_loop, end_loop):
            guild_data["loop_queue"].append(guild_data["music_queue"][i])
        await interaction.response.send_message("Started looping.")
        # await self.loopqueue(interaction, 1)
    
    @app_commands.command(name="loopqueue", description="Loop queue")
    async def loopqueue(self, interaction: discord.Interaction, page: int = 1) -> None:
        guild_id = interaction.guild.id
        guild_data = self.guild_data.get(guild_id, False)
        if(not guild_data or guild_data["vc"] is None or not guild_data["vc"].is_connected()):
            await interaction.response.send_message("Not playing music in this server.", ephemeral=True)
            return
        queue_pages = int(math.ceil(len(guild_data["loop_queue"]) / 10))
        if(not guild_data["is_looping"]):
            await interaction.response.send_message("Not currently looping.", ephemeral=True)
            return
        if(len(guild_data["loop_queue"]) < 1):
            await interaction.response.send_message("Loop qeueu is empty.", ephemeral=True)
            return
        if(page > queue_pages or page < 1):
            await interaction.response.send_message(f"Loop queue page does not exist! (Only {queue_pages} pages)", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Loop Queue",
            color=discord.Color.from_rgb(0, 255, 192)
        )
        if(guild_data["shuffle"]):
            embed.add_field(
                name="",
                value="Queue is shuffling; this is not the order it will play in."
            )
        now_playing = guild_data["now_playing"][0]
        embed.add_field(
            name="Now Playing",
            value=f"[{now_playing['video_title']}]({now_playing['video_url']}) - [{now_playing['channel']}]({now_playing['channel_url']})\nRequested by <@{now_playing['requested_by']}>",
            inline=False
        )
        for i in range(10*(page - 1), min(10*page, len(guild_data["loop_queue"]))):
            item = guild_data["loop_queue"][i][0]
            embed.add_field(
                name="",
                value=f"**{i + 1}.** [{item['video_title']}]({item['video_url']}) - [{item['channel']}]({item['channel_url']}) Requested by <@{item['requested_by']}>",
            inline=False
            )
        if(len(guild_data["loop_queue"]) > 10):
            embed.set_footer(
                text=f"Page {page}/{queue_pages}"
            )
        await interaction.response.send_message(embed=embed)

    # youtube
    # youtube music
    # spotify
    # soundcloud