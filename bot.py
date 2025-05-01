from discord.ext import commands
import config
import data
from commands import register_commands

bot = commands.Bot(command_prefix="!", intents=config.intents, case_insensitive=True)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
data.move_log = data.load_move_log()
print(f"🔧 Move log: {data.move_log}")  
print("✅ Move log loaded successfully.")

data.load_dummy_data_from_json("tiles.json")
print("✅ Teams and boards created successfully.")
register_commands(bot)

bot.run(config.TOKEN)