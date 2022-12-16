import discord, aiomysql, time
import config
from discord.ext import commands
bot = commands.Bot(command_prefix="./", intents=discord.Intents.all(),
                   activity=discord.Game("Tests!!"),
                   debug_guilds=config.DEBUG_GUILDS)
messagecounter = discord.SlashCommandGroup(name="messagecounter")
checklists = discord.SlashCommandGroup(name="checklists", description="create checklists!")
bot.add_application_command(messagecounter)
bot.add_application_command(checklists)
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
            async with conn.cursor()as cursor:
                await cursor.execute("UPDATE messagecounter SET messagecount = messagecount + 1 WHERE authorID=%s AND guildID=%s;", (message.author.id, message.guild.id))
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
@messagecounter.command(name="leaderboard-resetted-people", description="Leaderboard for resetted people")
async def leaderboard_reset(ctx: discord.ApplicationContext) -> None:
    async with bot.pool.acquire()as conn:
        async with conn.cursor(aiomysql.DictCursor)as cursor:
            await cursor.execute("SELECT authorID, messagecount FROM messagecounter WHERE guildID=%s ORDER BY messagecount DESC;", (ctx.guild_id,))
            fetch = await cursor.fetchall()
            if fetch == ():
                await ctx.respond(embed=discord.Embed(title="Oh", description="Wow, there are no resetted people in this server.", color=discord.Color.random()), ephemeral=True)
            else:
                e = discord.Embed(title="Leaderboard", colour=discord.Color.gold())
                for i in range(0, 6):
                    try:
                        concept = fetch[i]
                    except:
                        break
                    usr = ctx.guild.get_member(concept["authorID"])
                    if usr == None:
                        break
                    e.add_field(name=f"{i + 1}st - {usr}", value="**{}** messages".format(concept["messagecount"]), inline=False)
                await ctx.respond(embed=e, ephemeral=True)
@checklists.command(name="add")
@discord.option(name="text", type=str, max_length=90, required=True)
async def checklist_add(ctx:  discord.ApplicationContext, text: str) -> None:
    async with bot.pool.acquire()as  conn:
        async with conn.cursor(aiomysql.DictCursor)as cursor:
            await cursor.execute("SELECT COUNT(*) AS COUNT FROM checklists WHERE authorID=%s AND guildID=%s;", (ctx.author.id, ctx.guild_id))
            fetch = await cursor.fetchall()
            if fetch[0]["COUNT"] >= 20:
                embed = discord.Embed(title="No", description="You can only have 20 checklists.. Thats the max.", colour=discord.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                count = fetch[0]["COUNT"]
                await cursor.execute("INSERT INTO checklists(authorID, guildID, note_text) VALUES(%s, %s, %s);", (ctx.author.id, ctx.guild_id, text))
                await conn.commit()
                await cursor.execute("SELECT ID from checklists WHERE authorID=%s AND guildID=%s;", (ctx.author.id, ctx.guild_id))
                fetch = await cursor.fetchall()
                embed = discord.Embed(title="Done", description="Successfully added a new checklist with the id of **{}**".format(fetch[-1]["ID"]), color=discord.Color.green())
                embed.add_field(name="slots over", value="**{}** slots over".format( 20 - count - 1), inline=False)
                embed.add_field(name="used", value="**{}** slots used".format(count + 1), inline=False)
                embed.add_field(name="checklist text", value=text, inline=False)
                await ctx.respond(embed=embed, ephemeral=True)
@checklists.command(name="list")
async def checklist_list(ctx:  discord.ApplicationContext) -> None:
    async with bot.pool.acquire()as conn:
        async with conn.cursor(aiomysql.DictCursor)as cursor:
            await cursor.execute("SELECT ID, note_text FROM checklists WHERE authorID=%s AND guildID=%s;", (ctx.author.id, ctx.guild_id))
            fetch = await cursor.fetchall()
            if fetch == ():
                await ctx.respond(embed=discord.Embed(title="Nothing", description="You dont have any checklists.", color=discord.Color.green()), ephemeral=True)
            else:
                embed = discord.Embed(title="checklist of {}".format(ctx.author), colour=discord.Color.green())
                embed.set_footer(text="length -> {} checklists".format(len(fetch)), icon_url=ctx.author.display_avatar.url)
                for value in fetch:
                    embed.add_field(name="checklist ID-{}".format(value["ID"]), value=value["note_text"], inline=False)
                await ctx.respond(embed=embed, ephemeral=True)
@checklists.command(name="delete")
@discord.option(name="checklist_id", required=True, type=int)
async  def checklist_delete(ctx: discord.ApplicationContext, checklist_id: int) ->  None:
    async with bot.pool.acquire()as conn:
        async with conn.cursor(aiomysql.DictCursor)as cursor:
            await cursor.execute("SELECT note_text FROM checklists WHERE authorID=%s AND guildID=%s AND ID=%s;", (ctx.author.id, ctx.guild_id, checklist_id))
            fetch = await cursor.fetchall()
            if fetch == ():
                await ctx.respond(embed=discord.Embed(title="No", description=f"There is no checklist with the ID of **{checklist_id}**", color=discord.Color.red()), ephemeral=True)
            else:
                await cursor.execute("DELETE FROM checklists WHERE ID=%s;", (checklist_id,))
                await conn.commit()
                embed = discord.Embed(title="deleted", description=f"Successfully deleted the checklist with the id of **{checklist_id}**", color=discord.Color.green())
                embed.add_field(name="checklist text", value=fetch[0]["note_text"], inline=False)
                await ctx.respond(embed=embed, ephemeral=True)
@bot.slash_command(name="profile")
@discord.option(name="member", type=discord.Member, default=None)
async def profile(ctx: discord.ApplicationContext, member: discord.Member=None) -> None:
    await ctx.defer()
    target = ctx.author
    if member != None:
        target = member
    profile_embed = discord.Embed(title=f"Profile of {target}")
    async with bot.pool.acquire()as conn:
        async with conn.cursor(aiomysql.DictCursor)as cursor:
            await cursor.execute("SELECT messagecount FROM messagecounter WHERE authorID=%s AND guildID=%s;", (target.id, ctx.guild_id))
            messagecount_fetch = await cursor.fetchall()
            if messagecount_fetch == ():# does not exist
                ctr = 0
                for channel in ctx.guild.text_channels:
                    async for message in channel.history():
                        if message.author == target:
                            ctr += 1
                profile_embed.add_field(name="messages sent", value=f"**{ctr}** messages")
                await cursor.execute("INSERT INTO messagecounter VALUES(%s, %s, %s);", (target.id, ctx.guild_id, ctr)) # caching the result
                await conn.commit()
            else:
                profile_embed.add_field(name="messages sent", value="**{}** messages".format(messagecount_fetch[0]["messagecount"]))
            # getting the invites
            if ctx.guild.invites_disabled == False:
                ctr = 0
                invites = await ctx.guild.invites()
                for invite in invites:
                    if invite.inviter == target:
                        ctr += invite.uses
                profile_embed.add_field(name="invite count", value=f"**{ctr}** invites")
            await ctx.respond(embed=profile_embed)
bot.run(config.BOT_TOKEN)