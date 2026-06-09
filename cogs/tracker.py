import discord
from discord.ext import commands
from datetime import datetime, timezone


class Tracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="project", invoke_without_command=True)
    async def project(self, ctx: commands.Context):
        if not ctx.guild:
            return
        embed = discord.Embed(
            title="Project Tracker",
            description="Use the subcommands below to manage projects.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="!project create <name>", value="Create a new project", inline=False)
        embed.add_field(name="!projects", value="List all projects", inline=False)
        embed.add_field(name="!update <project> <message>", value="Log a progress update", inline=False)
        embed.add_field(name="!log <project>", value="View last 5 updates", inline=False)
        await ctx.send(embed=embed)

    @project.command(name="create")
    async def project_create(self, ctx: commands.Context, *, name: str):
        if not ctx.guild:
            return
        project_id = await self.bot.db.create_project(ctx.guild.id, name, ctx.author.display_name)
        if project_id is None:
            embed = discord.Embed(
                title="Project Already Exists",
                description=f"A project named **{name}** already exists in this server.",
                color=discord.Color.red(),
            )
        else:
            embed = discord.Embed(
                title="Project Created",
                description=f"**{name}** has been created.",
                color=discord.Color.green(),
            )
            embed.add_field(name="Created by", value=ctx.author.display_name, inline=True)
            embed.set_footer(text="Project names are single words for !update and !log. Use !projects to list all.")
        await ctx.send(embed=embed)

    @commands.command(name="update")
    async def update(self, ctx: commands.Context, project_name: str, *, message: str):
        if not ctx.guild:
            return
        row = await self.bot.db.get_project(ctx.guild.id, project_name)
        if row is None:
            embed = discord.Embed(
                title="Project Not Found",
                description=f"No project named **{project_name}** exists. Use `!projects` to see all projects.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        await self.bot.db.add_update(row["id"], ctx.author.display_name, message)
        embed = discord.Embed(
            title="Update Logged",
            description=f"Progress update added to **{project_name}**.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Message", value=message, inline=False)
        embed.add_field(name="Logged by", value=ctx.author.display_name, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="log")
    async def log(self, ctx: commands.Context, *, project_name: str):
        if not ctx.guild:
            return
        row = await self.bot.db.get_project(ctx.guild.id, project_name)
        if row is None:
            embed = discord.Embed(
                title="Project Not Found",
                description=f"No project named **{project_name}** exists. Use `!projects` to see all projects.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        updates = await self.bot.db.get_recent_updates(row["id"])
        embed = discord.Embed(
            title=f"Project Log: {project_name}",
            color=discord.Color.blue(),
        )
        if not updates:
            embed.add_field(name="No updates yet", value="Use `!update " + project_name + " <message>` to log progress.", inline=False)
        else:
            for update in updates:
                ts = datetime.fromisoformat(update["timestamp"])
                formatted = ts.strftime("%Y-%m-%d %H:%M UTC")
                embed.add_field(
                    name=f"{update['user']} — {formatted}",
                    value=update["message"],
                    inline=False,
                )
        embed.set_footer(text=f"Showing last {len(updates)} update(s)")
        await ctx.send(embed=embed)

    @commands.command(name="projects")
    async def projects(self, ctx: commands.Context):
        if not ctx.guild:
            return
        rows = await self.bot.db.list_projects(ctx.guild.id)
        embed = discord.Embed(title="Projects", color=discord.Color.blue())
        if not rows:
            embed.description = "No projects yet. Use `!project create <name>` to get started."
        else:
            for i, row in enumerate(rows):
                embed.add_field(
                    name=f"{i + 1}. {row['name']}",
                    value=f"Created by {row['created_by']} on {row['created_at'][:10]}",
                    inline=False,
                )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tracker(bot))
