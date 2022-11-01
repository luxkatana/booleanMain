import discord, aiomysql
from discord.ext import commands

bot = commands.Bot(command_prefix="./", intents=discord.Intents.all(),
                   activity=discord.Game("Tests!!"),
                   debug_guilds=[941803156633956362])

bot.load_extension("cogs")
@bot.event
async def on_ready() -> None:
    bot.pool = await aiomysql.create_pool(
        host="localhost",
        port=3306,
        user="root",
        password="inchem2009",
        db="testdb"
    )
    print(f"Logged in as {bot.user}")


bot.run("MTAxNDk1ODIzNTUxOTgzMjIwNg.G583j3.SLSxBkRPCmuK71FNrZhO8TG67_x5b6-iTNMKvI")