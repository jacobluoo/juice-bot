import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from db import Database

load_dotenv()

EXTENSIONS = [
    "cogs.general",
    "cogs.valorant",
    "cogs.gambling",
    "cogs.blackjack",
    "cogs.poker",
    "cogs.jobs",
    "cogs.tracker",
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


async def main():
    async with bot:
        bot.db = Database()
        await bot.db.setup()
        try:
            for ext in EXTENSIONS:
                await bot.load_extension(ext)
            await bot.start(os.getenv("DISCORD_TOKEN"))
        finally:
            await bot.db.close()


asyncio.run(main())
