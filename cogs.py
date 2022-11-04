import discord, aiomysql, random

from discord.ext import commands
class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.slash_command(name="autorespond")
    @discord.option(name="switch", required=True, choices=["on", "off"])
    @discord.option(name="trigger", required=False, type=str)
    @discord.option(name="respond", required=False, type=str)
    async def autorespond(self, ctx:discord.ApplicationContext, switch: str, trigger: str, respond: str) -> None:
        async def update() -> None:
            async with self.bot.pool.acquire()as conn:
                async with conn.cursor()as cursor:
                    await cursor.execute("UPDATE autorespond SET trigger_text=%s, respond=%s WHERE guildID=%s;", (trigger, respond, ctx.guild_id))
                    await conn.commit()
                    return
        async def create() -> None:
            async with self.bot.pool.acquire()as conn:
                async with conn.cursor()as cursor:
                    await cursor.execute("INSERT INTO autorespond VALUES(%s, %s, %s, %s)", (ctx.guild_id, True, trigger, respond))
                    await conn.commit()
                    return
        async def change_bool(sw: bool) -> None:
            async with self.bot.pool.acquire()as conn:
                async with conn.cursor()as cursor:
                    await cursor.execute("UPDATE autorespond SET listen=%s WHERE guildID=%s;", (sw, ctx.guild.id))
                    await conn.commit()
                    return
        async def exists() -> bool | dict:
            async with self.bot.pool.acquire()as conn:
                async with conn.cursor(aiomysql.DictCursor)as cursor:
                    await cursor.execute("SELECT * FROM autorespond WHERE guildID=%s;", (ctx.guild.id,))
                    fetch = await cursor.fetchall()
                    if fetch == (): return False
                    return fetch[0]
        if None in [trigger, respond] and switch == "on":
            embed=discord.Embed(title="Failed", description="Missing the required arguments...", colour=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
            return
        GUILDEXISTS = await exists()
        on_embed = discord.Embed(title="Success", description="Successfully switched it to **on**!", colour=discord.Color.green())
        match switch:
            case "on":
                if isinstance(GUILDEXISTS, bool): # does not exist
                    await create()
                    on_embed.title += " || created too ||"
                else:
                    await change_bool(True)
                    await update()
                    
                on_embed.add_field(name="trigger", value=f"*{trigger}*", inline=False)
                on_embed.add_field(name="respond text", value=f"*{respond}*", inline=False)
                await ctx.respond(embed=on_embed)
            case "off":
                if isinstance(GUILDEXISTS, bool):
                    await ctx.respond(embed=discord.Embed(title="oh..", description="It was never on...", colour=discord.Color.red()))
                else:
                    await change_bool(False)
                    await ctx.respond(embed=discord.Embed(title="Done", description="Successfully switched it to **off**!", colour=discord.Color.green()))
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        async def get_info() -> dict | bool:
            async with self.bot.pool.acquire()as conn:
                async with conn.cursor(aiomysql.DictCursor)as cursor:
                    await cursor.execute("SELECT listen, trigger_text, respond FROM autorespond WHERE guildID=%s;", (message.guild.id,))
                    fetch = await cursor.fetchall()
                    if fetch == (): return False
                    return fetch[0]
        if message.author != self.bot.user and (info := await get_info()) != False and info["listen"] == 1 and info["trigger_text"] in message.content.split():
            await message.reply(info["respond"])

        await self.bot.process_commands(message)
    @commands.slash_command(name="invitetracker", description="Shows how must people  you invited before")
    async def invitetracker(self, ctx: discord.ApplicationContext) -> None:
        if ctx.guild.invites_disabled: # if invites disabled
            embed = discord.Embed(title="RIP", description="Invites are disabled in this server...", colour=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            invites = await ctx.guild.invites()
            inv_count = 0
            for invite in invites:
                if invite.inviter == ctx.author:
                    inv_count += invite.uses
            embed = discord.Embed(title="Total Invites", description=f"You invited in total **{inv_count}** people.", colour=discord.Color.green())
            await ctx.respond(embed=embed)
    @commands.slash_command(name="invitetracker-leaderboard", description="Leaderboard of invites")
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
            await ctx.respond(embed=discord.Embed(title="Invites disabled", description="Invites are disabled in this server...", colour=discord.Color.red()))
        else:
            numbers = [random.randint(0, 10) for _ in range(0, 3)]
            hint = await ctx.respond(embed=discord.Embed(title="Did you know...", description="That {} + {} = {}? ".format(numbers[0], numbers[1], numbers[0] + numbers[1]),
                                                         fields=
                                                        [
                                                            discord.EmbedField(name="Waiting", value="Waiting for response... Be patient", inline=False)
                                                        ]))
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
            embed = discord.Embed(title="Invites Leaderboard", color=discord.Color.green())
            for i in range(0, 6): # get 5
                try:
                    target = high_to_low[i]
                except:
                    break
                embed.add_field(name=f"{i + 1}st - {target.inviter}", value=f"**{target.uses}** invites", inline=False)
            await hint.edit_original_response(embed=embed)
def setup(bot: commands.Bot) -> None:
    bot.add_cog(Utils(bot))
