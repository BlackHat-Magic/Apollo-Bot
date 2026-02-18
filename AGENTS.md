# AGENTS.md

Coding agent guidelines for the Apollo-Bot project - a Discord music bot built with discord.py.

## Project Overview

Apollo-Bot is a Discord music bot that supports YouTube search and playback via yt-dlp. It uses discord.py's cog system for organizing commands and manages per-guild state for queues, loops, and voice connections.

## Build/Run Commands

```bash
# Install dependencies (uses uv)
uv sync

# Run the bot locally
uv run python bot.py

# Run with Docker
docker build -t apollo-bot .
docker run --env-file .env apollo-bot
```

## Linting/Type Checking

No linting or type checking is currently configured. Consider running:
```bash
# Ruff (recommended linter/formatter)
uv run ruff check .
uv run ruff format .

# Type checking with mypy
uv run mypy .
```

## Testing

No tests currently exist. When adding tests:
```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_music_cog.py

# Run a single test function
uv run pytest tests/test_music_cog.py::test_search_youtube -v
```

## Project Structure

```
Apollo-Bot/
├── bot.py           # Entry point, bot initialization, event handlers
├── music_cog.py     # MusicCog class with all music commands
├── pyproject.toml   # Project dependencies (uv)
├── Dockerfile       # Container configuration
└── .env             # Environment variables (not in repo)
```

## Code Style Guidelines

### Imports

Order imports as follows, separated by blank lines:
1. Standard library
2. Third-party packages
3. Local modules

```python
# Standard library
import asyncio
import math
import os
import random

# Third-party
import discord
from discord import app_commands
from discord.ext import commands
from yt_dlp import YoutubeDL

# Local
from music_cog import MusicCog
```

Prefer `from x import y` for specific imports. Multiple related imports on one line are acceptable:
```python
import discord, math, asyncio, random
```

### Naming Conventions

- **Classes**: PascalCase (e.g., `MusicCog`)
- **Functions/Methods**: snake_case (e.g., `play_next`, `search_youtube`)
- **Variables**: snake_case (e.g., `guild_data`, `music_queue`)
- **Constants**: snake_case at class/module level (e.g., `ytdl_options`)
- **Private methods**: Prefix with underscore (e.g., `_helper_method`)
- **Command names**: lowercase, single word when possible (e.g., `/play`, `/queue`)

### Type Hints

Use type hints for function parameters and return types:

```python
def search_youtube(self, query: str, userid: int) -> dict:
    ...

async def play_next(self, guild_id: int) -> None:
    ...

async def queue(self, interaction: discord.Interaction, page: int = 1) -> None:
    ...
```

### Docstrings

Use triple-quoted docstrings for all public methods:

```python
def search_youtube(self, query: str, userid: int) -> dict:
    """
    Search YouTube for a video and return metadata
    """
    ...

async def play_next(self, guild_id: int) -> None:
    """
    Play the next song in the queue for a given guild
    """
    ...
```

### Error Handling

- Use try/except for external operations (API calls, file I/O)
- Return exceptions from helper methods when appropriate
- Always provide user-friendly error messages in command handlers
- Use `ephemeral=True` for error responses to avoid cluttering channels

```python
# Helper method - return exception
def search_youtube(self, query: str, userid: int) -> dict:
    try:
        info = ytdl.extract_info(f"ytsearch: {query}", download=False)
    except Exception as e:
        return e
    return {...}

# Command handler - show user-friendly message
if type(song) != dict:
    await interaction.followup.send(str(song))
```

### Async Patterns

- Use `asyncio` for asynchronous operations
- Always `await` coroutines
- Use `interaction.response.defer()` for slow operations, then `interaction.followup.send()`
- For callbacks that need async (e.g., FFmpeg `after`), use `bot.loop.create_task()`:

```python
guild_data["vc"].play(
    discord.FFmpegPCMAudio(playing_url, **self.ffmpeg_options),
    after=lambda x: self.bot.loop.create_task(self.play_next(guild_id))
)
```

### Discord.py Patterns

- Use `app_commands` for slash commands (preferred over prefix commands)
- Check for voice channel membership before audio operations
- Use embeds for rich message formatting
- Store per-guild state in a dictionary keyed by guild ID

```python
# Per-guild state pattern
self.guild_data = {}

# Access pattern
guild_data = self.guild_data.get(guild_id, False)
if not guild_data:
    return
```

### Guild State Management

The bot maintains state per Discord guild in `self.guild_data`:

```python
self.guild_data[guild_id] = {
    "is_playing": False,
    "is_paused": False,
    "music_queue": [],      # List of [song_dict, voice_channel]
    "now_playing": None,    # Current [song_dict, voice_channel]
    "text_channel": None,   # Channel for updates
    "loop_queue": [],
    "is_looping": False,
    "add_current_to_loop": True,
    "shuffle": False,
    "vc": None              # VoiceClient instance
}
```

Always check if guild data exists before accessing:
```python
guild_data = self.guild_data.get(guild_id, False)
if not guild_data:
    await interaction.response.send_message(
        "Not playing music in this server.", ephemeral=True
    )
    return
```

### Formatting

- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)
- Blank lines between methods
- No trailing whitespace
- Single quotes or double quotes are acceptable (be consistent within files)

### Comments

- Use comments sparingly; prefer self-documenting code
- Comment complex logic or non-obvious decisions
- Remove commented-out code before committing (or delete it)

## Environment Variables

Required in `.env`:
- `DISCORD_CLIENT_TOKEN` - Bot token from Discord Developer Portal

## Dependencies

Managed via `pyproject.toml` with uv:
- `discord` - Discord.py library
- `python-dotenv` - Environment variable loading
- `yt-dlp` - YouTube video extraction

## Notes

- Bot command prefix: `a!` (for legacy text commands)
- Slash commands are synced on startup via `client.tree.sync()`
- FFmpeg is required in the runtime environment for audio playback
