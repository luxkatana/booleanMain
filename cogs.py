import discord, aiomysql, random, time, asyncio
from datetime import datetime
import random as rdm

from discord.ext import commands


class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.slash_command(name="autorespond")
    @discord.option(name="switch", required=True, choices=["on", "off"])
    @discord.option(name="trigger", required=False, type=str)
    @discord.option(name="respond", required=False, type=str)
    async def autorespond(
        self, ctx: discord.ApplicationContext, switch: str, trigger: str, respond: str
    ) -> None:
        async def update() -> None:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "UPDATE autorespond SET trigger_text=%s, respond=%s WHERE guildID=%s;",
                        (trigger, respond, ctx.guild_id),
                    )
                    await conn.commit()
                    return

        async def create() -> None:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "INSERT INTO autorespond VALUES(%s, %s, %s, %s)",
                        (ctx.guild_id, True, trigger, respond),
                    )
                    await conn.commit()
                    return

        async def change_bool(sw: bool) -> None:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "UPDATE autorespond SET listen=%s WHERE guildID=%s;",
                        (sw, ctx.guild.id),
                    )
                    await conn.commit()
                    return

        async def exists() -> bool | dict:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT * FROM autorespond WHERE guildID=%s;", (ctx.guild.id,)
                    )
                    fetch = await cursor.fetchall()
                    if fetch == ():
                        return False
                    return fetch[0]

        if None in [trigger, respond] and switch == "on":
            embed = discord.Embed(
                title="Failed",
                description="Missing the required arguments...",
                colour=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        GUILDEXISTS = await exists()
        on_embed = discord.Embed(
            title="Success",
            description="Successfully switched it to **on**!",
            colour=discord.Color.green(),
        )
        match switch:
            case "on":
                if isinstance(GUILDEXISTS, bool):  # does not exist
                    await create()
                    on_embed.title += " || created too ||"
                else:
                    await change_bool(True)
                    await update()

                on_embed.add_field(name="trigger", value=f"*{trigger}*", inline=False)
                on_embed.add_field(
                    name="respond text", value=f"*{respond}*", inline=False
                )
                await ctx.respond(embed=on_embed)
            case "off":
                if isinstance(GUILDEXISTS, bool):
                    await ctx.respond(
                        embed=discord.Embed(
                            title="oh..",
                            description="It was never on...",
                            colour=discord.Color.red(),
                        )
                    )
                else:
                    await change_bool(False)
                    await ctx.respond(
                        embed=discord.Embed(
                            title="Done",
                            description="Successfully switched it to **off**!",
                            colour=discord.Color.green(),
                        )
                    )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        async def get_info() -> dict | bool:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT listen, trigger_text, respond FROM autorespond WHERE guildID=%s;",
                        (message.guild.id,),
                    )
                    fetch = await cursor.fetchall()
                    if fetch == ():
                        return False
                    return fetch[0]

        if (
            message.author != self.bot.user
            and (info := await get_info()) != False
            and info["listen"] == 1
            and info["trigger_text"] in message.content.split()
        ):
            await message.reply(info["respond"])

        await self.bot.process_commands(message)

    @commands.slash_command(
        name="invitetracker", description="Shows how must people  you invited before"
    )
    async def invitetracker(self, ctx: discord.ApplicationContext) -> None:
        if ctx.guild.invites_disabled:  # if invites disabled
            embed = discord.Embed(
                title="RIP",
                description="Invites are disabled in this server...",
                colour=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            invites = await ctx.guild.invites()
            inv_count = 0
            for invite in invites:
                if invite.inviter == ctx.author:
                    inv_count += invite.uses
            embed = discord.Embed(
                title="Total Invites",
                description=f"You invited in total **{inv_count}** people.",
                colour=discord.Color.green(),
            )
            await ctx.respond(embed=embed)

    @commands.slash_command(
        name="invitetracker-leaderboard", description="Leaderboard of invites"
    )
    async def invitetracker_leaderboard(self, ctx: discord.ApplicationContext) -> None:
        async def remove(array: list[discord.Invite]) -> list:
            highest = None
            number_buffer = 0
            for inv in array:
                print(inv.uses)
                if inv.uses > number_buffer:
                    highest = inv
                    number_buffer = highest.uses
                    print(highest, number_buffer, sep="\n")
                elif inv.uses == 0:
                    continue
            del array[array.index(highest)]
            return [array, highest]

        if ctx.guild.invites_disabled:
            await ctx.respond(
                embed=discord.Embed(
                    title="Invites disabled",
                    description="Invites are disabled in this server...",
                    colour=discord.Color.red(),
                )
            )
        else:
            numbers = [random.randint(0, 10) for _ in range(0, 3)]
            hint = await ctx.respond(
                embed=discord.Embed(
                    title="Did you know...",
                    description="That {} + {} = {}? ".format(
                        numbers[0], numbers[1], numbers[0] + numbers[1]
                    ),
                    fields=[
                        discord.EmbedField(
                            name="Waiting",
                            value="Waiting for response... Be patient",
                            inline=False,
                        )
                    ],
                )
            )
            invites = await ctx.guild.invites()
            high_to_low = []
            invites = list(filter(lambda j: j.uses != 0, invites))
            print(invites)

            while invites != []:
                new, high = await remove(invites)
                if 0 in [new, high]:
                    break
                invites = new.copy()
                high_to_low.append(high)
            embed = discord.Embed(
                title="Invites Leaderboard", color=discord.Color.green()
            )
            for i in range(0, 6):  # get 5
                try:
                    target = high_to_low[i]
                except:
                    break
                embed.add_field(
                    name=f"{i + 1}st - {target.inviter}",
                    value=f"**{target.uses}** invites",
                    inline=False,
                )
            await hint.edit_original_response(embed=embed)


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.EMOJIS = ["🔴", "🟢"]

    @commands.slash_command(name="speedgame")
    @discord.option(name="show_leaderboard", description="Show the leaderboard from the begin?", required=False, default=False, type=bool)
    async def speedgame(self, ctx: discord.ApplicationContext, show_leaderboard: bool) -> None:
        async def get_leaderboard() -> list[dict] | bool:
            async with self.bot.pool.acquire()as conn:
                async with conn.cursor(aiomysql.DictCursor)as cursor:
                    await cursor.execute("SELECT record, authorID FROM speedgame WHERE guildID=%s ORDER BY record ASC;", (ctx.guild_id,))
                    fetch = await cursor.fetchall()
                    if fetch == ():
                        return False
                    return fetch
        async def update_record(new_record: float) -> None:
            async with self.bot.pool.acquire()as conn:
                async with conn.cursor()as cursor:
                    await cursor.execute("UPDATE speedgame SET record=%s WHERE guildID=%s and authorID=%s;", (new_record, ctx.guild_id, ctx.author.id))
                    await conn.commit()
                    return
        async def create_record(to_float: float) -> None:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "INSERT INTO speedgame VALUES(%s, %s, %s);",
                        (
                            to_float,
                            ctx.author.id,
                            ctx.guild_id,
                        ),
                    )
                    await conn.commit()
                    return

        async def get_record() -> bool | dict:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT record FROM speedgame WHERE authorID=%s AND guildID=%s;",
                        (ctx.author.id, ctx.guild_id),
                    )
                    fetch = await cursor.fetchall()
                    if fetch == ():
                        return False
                    return fetch[0]

        v = discord.ui.View(timeout=10)

        async def on_timeout() -> None:

            await m.edit(
                view=None,
                embed=discord.Embed(
                    title="Cancelled",
                    description="It took more then 10 seconds to respond",
                    colour=discord.Color.red(),
                ),
            )

        v.on_timeout = on_timeout
        rand_btn = rdm.choice(self.EMOJIS)
        for emoji in self.EMOJIS:
            if emoji == rand_btn:

                async def now_callback(interaction: discord.Interaction) -> None:
                    if interaction.user != ctx.user:
                        await interaction.response.send_message(
                            "This is not your game!", ephemeral=True
                        )
                        return
                    difference = float(time.time() - now)
                    
                    if record == False: # if no record
                        await create_record(difference)
                    else: # if has
                        if difference < record["record"]:
                            embed = discord.Embed(title="WOW!", description="Congrats!, You've beaten your old record!", colour=discord.Color.green())
                            embed.add_field(name="old record", value="{:.2f} seconds".format(record["record"]), inline=False)
                            embed.add_field(name="new record", value="{:.2f} seconds".format(difference), inline=False)
                            dcv = discord.ui.View(timeout=None)
                            btn = discord.ui.Button(label="leaderboard", style=discord.ButtonStyle.green)
                            dcv.add_item(btn)
                            async def in_callback(inner: discord.Interaction) -> None:
                                if inner.user != ctx.user:
                                    await ctx.respond(embed=discord.Embed(title="dude no", description="This is not meant for you!", colour=discord.Color.red()), ephemeral=True)
                                else:
                                    em = discord.Embed(title="Leaderboard", colour=discord.Color.gold())
                                    leaderboard = await get_leaderboard()
                                    if leaderboard == False:
                                        em.add_field(name="OOPS!", value="There are no records currently available...", inline=False)
                                    else:
                                        for i in range(0, 6):
                                            try:
                                                rc = leaderboard[i]
                                            except:
                                                break
                                            if (user := ctx.guild.get_member(rc["authorID"])) == None:
                                                break
                                            em.add_field(name=f"{i + 1}st - {user}", value="**{:.2f}** seconds".format(rc["record"]), inline=False)
                                        await inner.response.send_message(embed=em, ephemeral=True)
                            btn.callback = in_callback
                            await interaction.response.send_message(embed=embed, view=dcv)
                            v.stop()
                            await update_record(difference)
                            return
                        
                    success_embed = discord.Embed(
                        title=f":stopwatch: {ctx.author.name}'s Speedgame result",
                        description=f"``You played with a ping of {round(self.bot.latency * 1000)}ms``\n\n{ctx.author.mention} you clicked the **right** button!\n> Your time is ``{difference:.3f}ms``!\n> Button {rand_btn}",
                        colour=discord.Color.green(),
                    )

                    await interaction.response.send_message(embed=success_embed)

                    v.stop()

                succ = discord.ui.Button(emoji=rand_btn, style=discord.ButtonStyle.gray)
                v.add_item(succ)
                succ.callback = now_callback
            else:
                d = discord.ui.Button(style=discord.ButtonStyle.gray, emoji=emoji)
                v.add_item(d)

                async def fail_callback(interaction: discord.Interaction) -> None:
                    if interaction.user != ctx.user:
                        await interaction.response.send_message(
                            "This is not your game!", ephemeral=True
                        )
                        return
                    failed_embed = discord.Embed(
                        title="Failed",
                        description=f"You Failed! the button was {rand_btn}",
                        colour=discord.Color.red(),
                    )
                    failed_embed.set_footer(text="For {}".format(ctx.author))
                    await interaction.response.send_message(embed=failed_embed)

                    v.stop()

                d.callback = fail_callback
        record = await get_record()
        leaderboard_view = discord.ui.View(timeout=None)
        leaderboard_btn = discord.ui.Button(label="leaderboard", style=discord.ButtonStyle.green)
        async def btn_callback(inner_interaction: discord.Interaction) -> None:
            if inner_interaction.user != ctx.user:
                await inner_interaction.response.send_message(embed=discord.Embed(title="bruh", description="That was not meant for you!", color=discord.Color.red()), ephemeral=True)
                return
            leaderboard = await get_leaderboard()
            if leaderboard == False:
                await inner_interaction.response.send_message(embed=discord.Embed(title="Sorry", description="There are no records in this server.", colour=discord.Color.red()), ephemeral=True)
            else:
                embed = discord.Embed(title="Leaderboard", color=discord.Color.gold())
                for i in range(0, 6):
                    try:
                        rc = leaderboard[i]
                    except:
                        break
                    user = ctx.guild.get_member(rc["authorID"])
                    if user == None:
                        pass
                    embed.add_field(name=f"{i + 1}st - {user}", value="**{:.2f}** seconds".format(rc["record"]), inline=False)
                await inner_interaction.response.send_message(embed=embed, ephemeral=True)
                return
        if show_leaderboard == True:
            leaderboard_view.add_item(leaderboard_btn)
            leaderboard_btn.callback = btn_callback

        tip_hint = discord.Embed(
            title="starting",
            description="Starting {}".format(
                discord.utils.format_dt(
                    datetime.fromtimestamp(int(time.time()) + 5), style="R"
                )
            ),
            colour=discord.Color.green(),
        )
        
        if record != False:
            tip_hint.add_field(name="TIP", value=f"Beat your record!", inline=False)
            tip_hint.add_field(name="old record", value=" {:.2f} seconds".format(record["record"]), inline=False)
        else:
            tip_hint.add_field(name="first time", value="click fast as possible! wish you luck!",inline=False)
        m = None
        if show_leaderboard == False:
            
            m = await ctx.respond(
                embed=tip_hint
            )
        else:
            m = await ctx.respond(embed=tip_hint, view=leaderboard_view)
        if record != False:
            pass
        await asyncio.sleep(5)

        embed = discord.Embed(
            title="Reaction game",
            description=f"Lets do a reaction game\nthe emoji that i choose is...\n click the button with the {rand_btn} below",
            color=discord.Color.random(),
        )

        m = await m.edit_original_response(embed=embed, view=v)
        now = time.time()

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Utils(bot))
    bot.add_cog(Games(bot))
