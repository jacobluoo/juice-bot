import discord
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="hello")
    async def hello(self, ctx: commands.Context):
        await ctx.send("Hey! Bot is alive.")


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
