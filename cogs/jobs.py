import discord
from discord.ext import commands
from datetime import datetime, timezone

JOBS = {
    "cashier": {
        "emoji": "🛒",
        "description": "Ring up customers at a local store",
        "base_salary": 50,
        "salary_per_level": 20,
        "xp_per_work": 10,
        "levelup_xp": 100,
        "levelup_cost_mult": 150,
    },
    "chef": {
        "emoji": "👨‍🍳",
        "description": "Cook meals at a busy restaurant",
        "base_salary": 80,
        "salary_per_level": 35,
        "xp_per_work": 15,
        "levelup_xp": 150,
        "levelup_cost_mult": 250,
    },
    "programmer": {
        "emoji": "💻",
        "description": "Write code for tech companies",
        "base_salary": 120,
        "salary_per_level": 60,
        "xp_per_work": 20,
        "levelup_xp": 200,
        "levelup_cost_mult": 400,
    },
    "streamer": {
        "emoji": "🎮",
        "description": "Entertain audiences online",
        "base_salary": 60,
        "salary_per_level": 80,
        "xp_per_work": 12,
        "levelup_xp": 120,
        "levelup_cost_mult": 300,
    },
    "trader": {
        "emoji": "📈",
        "description": "Buy and sell assets on the market",
        "base_salary": 100,
        "salary_per_level": 100,
        "xp_per_work": 25,
        "levelup_xp": 250,
        "levelup_cost_mult": 600,
    },
}

MAX_LEVEL = 5
WORK_COOLDOWN_HOURS = 4


def salary(job: dict, level: int) -> int:
    return job["base_salary"] + (level - 1) * job["salary_per_level"]


def xp_required(job: dict, level: int) -> int:
    return job["levelup_xp"] * level


def levelup_cost(job: dict, level: int) -> int:
    return job["levelup_cost_mult"] * level


class Jobs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="jobs")
    async def list_jobs(self, ctx):
        embed = discord.Embed(title="Available Jobs", color=discord.Color.blue())
        for name, job in JOBS.items():
            embed.add_field(
                name=f"{job['emoji']} {name.capitalize()}",
                value=(
                    f"{job['description']}\n"
                    f"Base salary: **{job['base_salary']}** coins/shift\n"
                    f"+{job['salary_per_level']} per level | Max level {MAX_LEVEL}"
                ),
                inline=False,
            )
        embed.set_footer(text="Use !apply <job> to start working")
        await ctx.send(embed=embed)

    @commands.command(name="apply")
    async def apply(self, ctx, *, job_name: str = None):
        if not job_name:
            await ctx.send("Usage: `!apply <job name>`")
            return
        job_name = job_name.lower()
        if job_name not in JOBS:
            await ctx.send(f"Unknown job. Use `!jobs` to see available options.")
            return

        row = await self.bot.db.get_job(ctx.author.id, ctx.guild.id)
        if row["job_name"] is not None:
            await ctx.send(
                f"You're already working as a **{row['job_name'].capitalize()}**. Use `!quit` first."
            )
            return

        await self.bot.db.set_job(ctx.author.id, ctx.guild.id, job_name)
        job = JOBS[job_name]
        embed = discord.Embed(
            title=f"{job['emoji']} Hired as {job_name.capitalize()}!",
            description=f"Starting salary: **{job['base_salary']}** coins per shift.\nUse `!work` every {WORK_COOLDOWN_HOURS} hours to earn coins and XP.",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="quit")
    async def quit_job(self, ctx):
        row = await self.bot.db.get_job(ctx.author.id, ctx.guild.id)
        if row["job_name"] is None:
            await ctx.send("You don't have a job to quit.")
            return

        job_name = row["job_name"]
        await self.bot.db.set_job(ctx.author.id, ctx.guild.id, None)
        await ctx.send(f"You quit your job as **{job_name.capitalize()}**. All XP and level progress has been reset.")

    @commands.command(name="work")
    async def work(self, ctx):
        row = await self.bot.db.get_job(ctx.author.id, ctx.guild.id)
        if row["job_name"] is None:
            await ctx.send("You don't have a job. Use `!apply <job>` to get one.")
            return

        now = datetime.now(timezone.utc)
        if row["last_work"]:
            last = datetime.fromisoformat(row["last_work"]).replace(tzinfo=timezone.utc)
            elapsed = (now - last).total_seconds() / 3600
            if elapsed < WORK_COOLDOWN_HOURS:
                remaining = WORK_COOLDOWN_HOURS - elapsed
                hours = int(remaining)
                minutes = int((remaining - hours) * 60)
                await ctx.send(
                    f"You're tired. Come back in **{hours}h {minutes}m** to work again."
                )
                return

        job_name = row["job_name"]
        job = JOBS[job_name]
        level = row["job_level"]
        earned = salary(job, level)
        xp_gain = job["xp_per_work"]

        new_balance = await self.bot.db.add_balance(ctx.author.id, ctx.guild.id, earned)
        await self.bot.db.update_job_progress(
            ctx.author.id, ctx.guild.id, xp_gain, now.isoformat()
        )

        # re-fetch for updated XP
        updated = await self.bot.db.get_job(ctx.author.id, ctx.guild.id)
        xp_now = updated["job_xp"]
        xp_need = xp_required(job, level) if level < MAX_LEVEL else None

        embed = discord.Embed(
            title=f"{job['emoji']} Shift Complete!",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Earned", value=f"**+{earned}** coins", inline=True)
        embed.add_field(name="Balance", value=f"**{new_balance}** coins", inline=True)
        embed.add_field(name="XP", value=f"**{xp_now}** / {xp_need if xp_need else 'MAX'}", inline=True)
        if xp_need and xp_now >= xp_need:
            embed.set_footer(text="You have enough XP to level up! Use !levelup")
        else:
            embed.set_footer(text=f"Next shift available in {WORK_COOLDOWN_HOURS} hours")
        await ctx.send(embed=embed)

    @commands.command(name="job")
    async def job_status(self, ctx):
        row = await self.bot.db.get_job(ctx.author.id, ctx.guild.id)
        if row["job_name"] is None:
            await ctx.send("You're unemployed. Use `!apply <job>` to get a job.")
            return

        job_name = row["job_name"]
        job = JOBS[job_name]
        level = row["job_level"]
        xp = row["job_xp"]
        xp_need = xp_required(job, level) if level < MAX_LEVEL else None
        current_salary = salary(job, level)
        cost = levelup_cost(job, level) if level < MAX_LEVEL else None

        embed = discord.Embed(
            title=f"{job['emoji']} {job_name.capitalize()} — Level {level}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Salary", value=f"**{current_salary}** coins/shift", inline=True)
        embed.add_field(
            name="XP",
            value=f"**{xp}** / {xp_need if xp_need else 'MAX'}",
            inline=True,
        )
        if level < MAX_LEVEL:
            embed.add_field(
                name="Level Up Cost",
                value=f"**{cost}** coins (requires {xp_need} XP)",
                inline=False,
            )
            next_salary = salary(job, level + 1)
            embed.add_field(name="Next Level Salary", value=f"**{next_salary}** coins/shift", inline=True)
        else:
            embed.add_field(name="Level", value="**MAX LEVEL**", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="levelup")
    async def level_up(self, ctx):
        row = await self.bot.db.get_job(ctx.author.id, ctx.guild.id)
        if row["job_name"] is None:
            await ctx.send("You don't have a job.")
            return

        job_name = row["job_name"]
        job = JOBS[job_name]
        level = row["job_level"]
        xp = row["job_xp"]

        if level >= MAX_LEVEL:
            await ctx.send(f"You're already at max level ({MAX_LEVEL}) for {job_name.capitalize()}!")
            return

        xp_need = xp_required(job, level)
        if xp < xp_need:
            await ctx.send(
                f"Not enough XP. You have **{xp}** / **{xp_need}** XP needed to level up."
            )
            return

        cost = levelup_cost(job, level)
        balance = await self.bot.db.get_balance(ctx.author.id, ctx.guild.id)
        if balance < cost:
            await ctx.send(
                f"Not enough coins. Level up costs **{cost}** coins but you only have **{balance}**."
            )
            return

        await self.bot.db.add_balance(ctx.author.id, ctx.guild.id, -cost)
        new_level = level + 1
        await self.bot.db.set_job_level(ctx.author.id, ctx.guild.id, new_level, 0)

        new_salary = salary(job, new_level)
        embed = discord.Embed(
            title=f"{job['emoji']} Level Up! {job_name.capitalize()} → Level {new_level}",
            description=f"Paid **{cost}** coins. New salary: **{new_salary}** coins/shift.",
            color=discord.Color.green(),
        )
        if new_level == MAX_LEVEL:
            embed.set_footer(text="You've reached max level!")
        else:
            next_xp = xp_required(job, new_level)
            next_cost = levelup_cost(job, new_level)
            embed.set_footer(text=f"Next level up: {next_xp} XP + {next_cost} coins")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Jobs(bot))
