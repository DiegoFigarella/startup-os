"""Startup OS Discord bot: ingests team sources, answers /catchup."""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

if Path(".env").exists():
    for line in Path(".env").read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())

import discord
from discord import app_commands
from discord.ext import tasks

import brain
import db
import sources

log = logging.getLogger("startup-os")
GUILD = discord.Object(int(os.environ["DISCORD_GUILD_ID"]))
CHANNELS = {int(c) for c in os.getenv("DISCORD_CHANNEL_IDS", "").split(",") if c.strip()}

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def watched(channel):
    ch = getattr(channel, "parent", None) or channel  # threads inherit their parent's allowlisting
    return not CHANNELS or ch.id in CHANNELS


def save(msg):
    text = msg.clean_content
    if msg.attachments:
        text += "\nAttachments: " + ", ".join(a.filename for a in msg.attachments)
    if text.strip():
        db.add("discord", str(msg.id), msg.created_at, msg.author.display_name,
               f"#{msg.channel.name}", text, msg.jump_url)


async def backfill(guild):
    """Catch up on messages posted while the bot was offline."""
    last = db.latest("discord")
    after = datetime.fromisoformat(last) if last else datetime.now(timezone.utc) - sources.BACKFILL
    # ponytail: top-level channels only; live on_message still captures threads
    for ch in guild.text_channels:
        if watched(ch) and ch.permissions_for(guild.me).read_message_history:
            async for msg in ch.history(after=after, limit=None):
                if not msg.author.bot:
                    save(msg)


@tasks.loop(minutes=int(os.getenv("POLL_MINUTES", "15")))
async def poll():
    for ingest in sources.ALL:
        try:
            await asyncio.to_thread(ingest)
        except Exception:
            log.exception("%s ingest failed", ingest.__name__)


@client.event
async def on_ready():
    tree.copy_global_to(guild=GUILD)
    await tree.sync(guild=GUILD)
    guild = client.get_guild(GUILD.id)
    if guild:
        await backfill(guild)
    if not poll.is_running():
        poll.start()
    log.info("ready as %s", client.user)


@client.event
async def on_message(msg):
    if msg.guild and msg.guild.id == GUILD.id and not msg.author.bot and watched(msg.channel):
        save(msg)


@tree.command(description="What you missed across Discord, Zoom, Drive and invoices")
@app_commands.describe(since="How far back to look (default 1 week)")
@app_commands.choices(since=[app_commands.Choice(name=k, value=v) for k, v in brain.RANGES.items()])
async def catchup(inter: discord.Interaction, since: app_commands.Choice[int] | None = None):
    window, days = (since.name, since.value) if since else ("1 week", 7)
    await inter.response.defer(ephemeral=True, thinking=True)
    items = db.since(datetime.now(timezone.utc) - timedelta(days=days))
    if not items:
        await inter.followup.send(f"Nothing recorded in the last {window}.", ephemeral=True)
        return
    try:
        text = await brain.catchup(items, inter.user.display_name, window)
    except Exception:
        log.exception("catchup failed")
        text = "Something broke while summarizing. Check the bot logs."
    for part in brain.chunks(f"**Since {window} ago** ({len(items)} updates)\n{text}"):
        await inter.followup.send(part, ephemeral=True)


if __name__ == "__main__":
    client.run(os.environ["DISCORD_TOKEN"], root_logger=True)
