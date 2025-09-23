from dotenv import load_dotenv
# from help_cog import help_cog
from music_cog import MusicCog
from discord.ext import commands
from discord import app_commands
import discord, os

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix="a!", intents=intents)

async def prepare_bot():
    """
    Prepare bot to run
    """
    await client.add_cog(MusicCog(client))

@client.event
async def on_ready():
    """
    Code to execute when bot is ready
    """
    print(f"Logged in as {client.user}.")
    try:
        await prepare_bot()
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(e)

client.run(os.getenv("DISCORD_CLIENT_TOKEN"))
