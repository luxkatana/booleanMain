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
@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author != bot.user:
        async with bot.pool.acquire()as conn:
            async with conn.cursor(aiomysql.DictCursor)as cursor:
                await cursor.execute("SELECT messagecount FROM messagecounter WHERE authorID=%s and guildID=%s;", (message.author.id, message.guild.id))
                fetch = await cursor.fetchall()
                if fetch != ():
                    await cursor.execute("UPDATE messagecounter SET messagecount=%s WHERE authorID=%s AND guildID=%s;", (fetch[0]["messagecount"] + 1,message.author.id, message.guild.id))
                    await conn.commit()
    await bot.process_commands(message)
@messagecounter.command(name="reset-all")
async def reset_everyone(ctx: discord.ApplicationContext) -> None:
    async def reset_memb(member: discord.Member) -> bool:
        async with bot.pool.acquire()as conn:
            async with conn.cursor(aiomysql.DictCursor)as cursor:
                await cursor.execute("SELECT * FROM messagecounter WHERE authorID=%s AND guildID=%s;", (member.id, member.guild.id))
                fetch = await cursor.fetchall()
                if fetch == ():
                    await cursor.execute("INSERT INTO messagecounter VALUES(%s, %s, %s);", (member.id, member.guild.id, 0))
                else:
                    await cursor.execute("UPDATE messagecounter SET messagecount=0 WHERE authorID=%s AND guildID=%s;", (member.id, member.guild.id))
                await conn.commit()
                return True
    NOW = time.time()
    m = discord.Embed(title="It might take some time", description="It might some time... <t:{}:R> ".format(NOW), colour=discord.Color.og_blurple())
    msg = await ctx.respond(embed=m)
    for member in ctx.guild.members:
        await reset_memb(member)
    m.title = "Done"
    m.description = "Successfully resetted everyones messages to **0**"
    m.color = discord.Color.random()
    needed_time = time.time() - NOW
    m.add_field(name="Needed time", value=f"**{needed_time:.2f}** seconds", inline=False)
    await msg.edit_original_response(embed=m)
@messagecounter.command(name="add-messages-user")
@discord.option(name="member", type=discord.Member, required=True)
@discord.option(name="amount", type=int, required=True)
async def addmessages(ctx: discord.ApplicationContext, member: discord.Member, amount: int) -> None:
    if amount <= 0:
        await ctx.respond(embed=discord.Embed(title="OOps", description="``amount`` can't be lower than 0.", color=discord.Color.red()), ephemeral=True)
        return
    async with bot.pool.acquire()as conn:
        async with conn.cursor(aiomysql.DictCursor)as cursor:
            await cursor.execute("SELECT messagecount FROM messagecounter WHERE authorID=%s AND guildID=%s;", (member.id, member.guild.id))
            fetch = await cursor.fetchall()
            if fetch == ():
                pass
            else:
                await cursor.execute('''
                                     UPDATE messagecounter SET messagecount=%s WHERE authorID=%s AND guildID=%s;
                                     ''', (fetch[0]["messagecount"] + amount, member.id, member.guild.id))
                await conn.commit()
    e = discord.Embed(title="Done", description="Successfully added **{}** messages to  <@{}>".format(amount, member.id), color=discord.Color.green())
    e.add_field(name="Before", value="**{}** messages".format(fetch[0]["messagecount"]), inline=False)
    e.add_field(name="After", value="**{}** messages".format(fetch[0]["messagecount"] + amount), inline=False)
    await ctx.respond(embed=e, ephemeral=True)
    return
@messagecounter.command(name="reset-user")
@discord.option(name="member", type=discord.Member, required=True)
async def reset(ctx: discord.ApplicationContext, member: discord.Member) -> None:
    async with bot.pool.acquire()as conn:
        async with conn.cursor()as cursor:
            await cursor.execute("SELECT * FROM messagecounter WHERE authorID=%s AND guildID=%s;", (member.id, ctx.guild_id))
            fetch = await cursor.fetchall()
            if fetch == ():
                await cursor.execute("INSERT INTO messagecounter VALUES(%s, %s, 0);", (member.id, ctx.guild_id))
            else:
                await cursor.execute("UPDATE messagecounter SET messagecount=0 WHERE authorID=%s AND guildID=%s;", (member.id, ctx.guild_id))
            await conn.commit()
    embed = discord.Embed(title="Done", description=f"Successfully resetted the count of messages from <@{member.id}> to **0**", colour=discord.Color.green())
    await ctx.respond(embed=embed)
@messagecounter.command(name="me", description="Get the amount of messages sent by me(You)")
async def count(ctx: discord.ApplicationContext) -> None:
    async def get():
        async with bot.pool.acquire()as conn:
            async with conn.cursor(aiomysql.DictCursor)as cursor:
                await cursor.execute("SELECT messagecount FROM messagecounter WHERE authorID=%s AND guildID=%s;", (ctx.author.id, ctx.guild_id))
                fetch = await cursor.fetchall()
                if fetch == ():
                    return None
                return fetch[0]["messagecount"]
    cc = await get()
    if cc != None:
        embed = discord.Embed(title="Got it", description=f"You have sent **{cc}** messages here", color=discord.Color.green())
        embed.set_footer(text="Note that it has been resetted once.")
        await ctx.respond(embed=embed)
        return
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
            elif message.author.id not in counters and message.author.bot == False:
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