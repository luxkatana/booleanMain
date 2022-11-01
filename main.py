import discord, aiomysql
from os import environ
from dotenv import load_dotenv
from discord.ext import commands
load_dotenv()
bot = commands.Bot(command_prefix="./", intents=discord.Intents.all(),
                   activity=discord.Game("Tests!!"),
                   debug_guilds=[941803156633956362])

bot.load_extension("cogs")
@bot.event
async def on_ready() -> None:
    bot.pool = await aiomysql.create_pool(
        host=environ["HOST"],
        port=environ["PORT"],
        user=environ["USER"],
        password=environ["PASSWORD"],
        db=environ["DB"]
    )
    print(f"Logged in as {bot.user}")


bot.run(environ["BOT_TOKEN"])