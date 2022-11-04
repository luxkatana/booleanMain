import discord, aiomysql, time
import config
from discord.ext import commands
bot = commands.Bot(command_prefix="./", intents=discord.Intents.all(),
                   activity=discord.Game("Tests!!"),
                   debug_guilds=config.DEBUG_GUILDS)
messagecounter = discord.SlashCommandGroup(name="messagecounter")
bot.add_application_command(messagecounter)
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



@messagecounter.command(name="me", description="Get the amount of messages sent by me(You)")
async def count(ctx: discord.ApplicationContext) -> None:
    ctr = 0
    now = time.time()
    waiting_embed = discord.Embed(title="Please be patient", description="It might take some time to get the message count", colour=discord.Color.random())
    msg = await ctx.respond(embed=waiting_embed)
    for channel in ctx.guild.text_channels:
        async for message in channel.history():
            if message.author == ctx.author:
                ctr += 1
            
            continue
    
    waiting_embed.title = "Done!"
    waiting_embed.description = ""
    waiting_embed.add_field(name="count", value=f"**{ctr}** messages(total every channel)", inline=False)
    waiting_embed.add_field(name="Time needed(in seconds)", value=f"{time.time() - now:.2f} seconds", inline=False)
    await msg.edit_original_response(embed=waiting_embed)


@messagecounter.command(name="leaderboard", description="Who sent the most messages?")
async def leaderboard(ctx: discord.ApplicationContext) -> None:
    async def remove_highest(array: list[dict]) -> list:
        highest = {"count": 0}
        for i in array:
            if array[i]["count"] > highest["count"]:
                highest = {"count": array[i]["count"], "authorID": i}
        authorID = highest["authorID"]
        del array[authorID]
        return [array, highest]
    waiting_embed = discord.Embed(title="...", description="Please be patient...", colour=discord.Color.random())
    respond_message = await ctx.respond(embed=waiting_embed)
    counters = {}
    for channel in ctx.guild.text_channels:
        async for message in channel.history():
            if message.author.id in counters:
                counters[message.author.id]["count"] += 1
            elif message.author.id not in counters:
                counters.update({message.author.id: {"count": 1}})
    high_to_low = []
    copy = counters
    while copy != {}:
        result, highest_one = await remove_highest(copy)
        copy = result.copy()
        high_to_low.append(highest_one)
    embed = discord.Embed(title="Leaderboard", colour=discord.Color.green())
    for i in range(0, 5): # get 5 people from begin
        try:
            record = high_to_low[i]
        except: 
            break
        authorID = record["authorID"]
        member = ctx.guild.get_member(authorID)
        if member == None:
            break
        embed.add_field(name=f"{i + 1}st - {member}", value="**{}** message(s)".format(record["count"]), inline=False)
    await respond_message.edit_original_response(embed=embed)
bot.run(config.BOT_TOKEN)