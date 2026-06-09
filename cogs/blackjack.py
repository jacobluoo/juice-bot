import discord
from discord.ext import commands
import random

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]


def make_deck() -> list[str]:
    return [r + s for r in RANKS for s in SUITS]


def draw_card(deck: list[str]) -> str:
    return deck.pop()


def card_value(card: str) -> int:
    rank = card[:-1]
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(hand: list[str]) -> int:
    total = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[:-1] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def fmt_hand(hand: list[str]) -> str:
    return "  ".join(hand)


class Blackjack(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: set[tuple[int, int]] = set()

    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx: commands.Context, bet: int = 0):
        db = self.bot.db
        uid, gid = ctx.author.id, ctx.guild.id

        if bet <= 0:
            await ctx.send("Usage: `!blackjack <bet>`  e.g. `!blackjack 50`")
            return

        if (uid, gid) in self.active_games:
            await ctx.send("You already have a game in progress. Finish it first.")
            return

        balance = await db.get_balance(uid, gid)
        if bet > balance:
            await ctx.send(f"Not enough coins. You have **{balance}**.")
            return

        self.active_games.add((uid, gid))

        try:
            deck = make_deck()
            random.shuffle(deck)
            player = [draw_card(deck), draw_card(deck)]
            dealer = [draw_card(deck), draw_card(deck)]

            if hand_value(player) == 21:
                winnings = int(bet * 1.5)
                new_bal = await db.add_balance(uid, gid, winnings)
                await ctx.send(
                    f"**Blackjack!** {fmt_hand(player)} = 21\n"
                    f"You win **{winnings}** coins! Balance: **{new_bal}**"
                )
                return

            def is_player(m):
                return (
                    m.author == ctx.author
                    and m.channel == ctx.channel
                    and m.content.lower() in ("hit", "stand", "h", "s")
                )

            while True:
                pval = hand_value(player)
                embed = discord.Embed(title="Blackjack", color=discord.Color.green())
                embed.add_field(name="Your hand", value=f"{fmt_hand(player)} = **{pval}**", inline=False)
                embed.add_field(name="Dealer shows", value=dealer[0], inline=False)
                embed.set_footer(text="Type 'hit' or 'stand'")
                await ctx.send(embed=embed)

                if pval == 21:
                    break

                try:
                    msg = await self.bot.wait_for("message", check=is_player, timeout=30)
                except TimeoutError:
                    await ctx.send("Game timed out. Your bet is returned.")
                    return

                if msg.content.lower() in ("stand", "s"):
                    break

                player.append(draw_card(deck))
                if hand_value(player) > 21:
                    new_bal = await db.add_balance(uid, gid, -bet)
                    await ctx.send(
                        f"**Bust!** {fmt_hand(player)} = {hand_value(player)}\n"
                        f"You lose **{bet}** coins. Balance: **{new_bal}**"
                    )
                    return

            while hand_value(dealer) < 17:
                dealer.append(draw_card(deck))

            pval = hand_value(player)
            dval = hand_value(dealer)

            result_lines = [
                f"Your hand:   {fmt_hand(player)} = **{pval}**",
                f"Dealer hand: {fmt_hand(dealer)} = **{dval}**",
            ]

            if dval > 21 or pval > dval:
                new_bal = await db.add_balance(uid, gid, bet)
                result_lines.append(f"\nYou **win {bet}** coins! Balance: **{new_bal}**")
            elif pval == dval:
                new_bal = await db.get_balance(uid, gid)
                result_lines.append(f"\n**Push** — bet returned. Balance: **{new_bal}**")
            else:
                new_bal = await db.add_balance(uid, gid, -bet)
                result_lines.append(f"\nYou **lose {bet}** coins. Balance: **{new_bal}**")

            await ctx.send("\n".join(result_lines))

        finally:
            self.active_games.discard((uid, gid))


async def setup(bot: commands.Bot):
    await bot.add_cog(Blackjack(bot))
