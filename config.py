from dotenv import load_dotenv
import os
import discord

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_IDS = []

intents = discord.Intents.default()
intents.message_content = True
