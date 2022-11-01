import discord, aiomysql
import config
from discord.ext import commands
bot = commands.Bot(command_prefix="./", intents=discord.Intents.all(),
                   activity=discord.Game("Tests!!"),
                   debug_guilds=config.DEBUG_GUILDS)

bot.load_extension("cogs")
@bot.event
async def on_ready() -> None:
    bot.pool = await aiomysql.create_pool(
        host=config.HOST,
        user=config.USER,
        password=config.PASSWORD,
        port=config.PORT,
        db=config.DB
        
    )
    print(f"Logged in as {bot.user}")


bot.run(config.BOT_TOKEN)