import discord
from discord.ext import commands
import random
from collections import Counter
from itertools import combinations

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["♠", "♥", "♦", "♣"]
RANK_VALUE = {r: i for i, r in enumerate(RANKS)}

HAND_NAMES = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "Pair",
    0: "High Card",
}


def make_deck() -> list[str]:
    deck = [r + s for r in RANKS for s in SUITS]
    random.shuffle(deck)
    return deck


def deal(deck: list[str], n: int) -> list[str]:
    cards = deck[:n]
    del deck[:n]
    return cards


def fmt(cards: list[str]) -> str:
    return "  ".join(cards)


def _rank(card: str) -> str:
    return card[:-1]


def _suit(card: str) -> str:
    return card[-1]


def _evaluate(cards: list[str]) -> tuple:
    vals = sorted((RANK_VALUE[_rank(c)] for c in cards), reverse=True)
    flush = len({_suit(c) for c in cards}) == 1
    straight = (vals[0] - vals[4] == 4 and len(set(vals)) == 5) or set(vals) == {12, 0, 1, 2, 3}
    rank_counts = Counter(_rank(c) for c in cards)
    counts = sorted(rank_counts.values(), reverse=True)
    # Sort by (count desc, rank value desc) so high cards break ties
    count_vals = sorted(RANK_VALUE.keys(), key=lambda r: (rank_counts.get(r, 0), RANK_VALUE[r]), reverse=True)
    count_vals = [RANK_VALUE[r] for r in count_vals if r in rank_counts]

    if straight and flush:
        # Wheel (A-2-3-4-5) straight flush: ace acts as low, use -1 so it ranks
        # below a 5-high straight flush ([3,2,1,0,-1] < [8,7,6,5,4]).
        sf_vals = [-1, 3, 2, 1, 0] if set(vals) == {12, 0, 1, 2, 3} else vals
        return (8, sf_vals)
    if counts[0] == 4:
        return (7, count_vals)
    if counts[:2] == [3, 2]:
        return (6, count_vals)
    if flush:
        return (5, vals)
    if straight:
        return (4, vals)
    if counts[0] == 3:
        return (3, count_vals)
    if counts[:2] == [2, 2]:
        return (2, count_vals)
    if counts[0] == 2:
        return (1, count_vals)
    return (0, vals)


def best_five(hole: list[str], community: list[str]) -> tuple:
    return max(_evaluate(list(combo)) for combo in combinations(hole + community, 5))


class Poker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: set[tuple[int, int]] = set()

    @commands.command(name="poker")
    async def poker(self, ctx: commands.Context, bet: int = 0):
        db = self.bot.db
        uid, gid = ctx.author.id, ctx.guild.id

        if bet <= 0:
            await ctx.send("Usage: `!poker <bet>`  e.g. `!poker 100`")
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
            await self._run_game(ctx, db, uid, gid, bet)
        finally:
            self.active_games.discard((uid, gid))

    async def _run_game(self, ctx, db, uid, gid, bet):
        deck = make_deck()
        player_hole = deal(deck, 2)
        bot_hole = deal(deck, 2)
        community: list[str] = []
        pot = bet * 2  # player ante + bot ante
        player_spent = bet
        await db.add_balance(uid, gid, -bet)

        def valid_response(m, valid: set[str]) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in valid

        SHORTCUTS = {"c": "call", "f": "fold", "r": "raise", "k": "check"}

        async def betting_round(label: str) -> str | None:
            """
            Bot acts first (50/50 raise or check), then player responds.
            Returns 'fold', 'bot_fold', or 'timeout' to end the game early, else None.
            """
            nonlocal pot, player_spent

            bot_action = random.choice(["raise", "check"])

            embed = discord.Embed(title=f"Poker — {label}", color=discord.Color.gold())
            embed.add_field(name="Your hand", value=fmt(player_hole), inline=False)
            if community:
                embed.add_field(name="Community", value=fmt(community), inline=False)
            embed.add_field(name="Pot", value=f"**{pot}** coins", inline=True)
            embed.add_field(name="Dealer's hand", value="🂠  🂠", inline=True)

            if bot_action == "raise":
                pot += bet
                embed.add_field(
                    name="Dealer action",
                    value=f"raises +{bet} coins.\nType `call` or `fold`.",
                    inline=False,
                )
                valid = {"call", "fold", "c", "f"}
            else:
                embed.add_field(
                    name="Dealer action",
                    value="checks.\nType `check` or `raise`.",
                    inline=False,
                )
                valid = {"check", "raise", "k", "r"}

            await ctx.send(embed=embed)

            try:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: valid_response(m, valid),
                    timeout=45,
                )
            except TimeoutError:
                await db.add_balance(uid, gid, player_spent)
                await ctx.send(f"Game timed out. Your **{player_spent}** coins are returned.")
                return "timeout"

            action = SHORTCUTS.get(msg.content.lower(), msg.content.lower())

            if action == "fold":
                await ctx.send(f"You folded. Dealer wins the pot of **{pot}** coins.")
                return "fold"

            current_balance = await db.get_balance(uid, gid)

            if action == "call":
                if current_balance < bet:
                    await ctx.send(f"Not enough coins to call (need **{bet}**, have **{current_balance}**). You fold.")
                    return "fold"
                pot += bet
                player_spent += bet
                await db.add_balance(uid, gid, -bet)
                await ctx.send(f"You call. Pot: **{pot}** coins.")

            if action == "raise":
                if current_balance < bet:
                    await ctx.send(f"Not enough coins to raise (need **{bet}**, have **{current_balance}**). You fold.")
                    return "fold"
                pot += bet
                player_spent += bet
                await db.add_balance(uid, gid, -bet)
                # Bot responds to player raise: 50/50
                if random.choice([True, False]):
                    winnings = pot
                    new_bal = await db.add_balance(uid, gid, winnings)
                    await ctx.send(
                        f"You raise. Dealer folds!\n"
                        f"You win **{winnings}** coins. Balance: **{new_bal}**"
                    )
                    return "bot_fold"
                else:
                    pot += bet
                    await ctx.send(f"You raise. Dealer calls. Pot: **{pot}** coins.")

            return None

        for label, new_cards in [("Pre-Flop", []), ("Flop", 3), ("Turn", 1), ("River", 1)]:
            if new_cards:
                community += deal(deck, new_cards)
            result = await betting_round(label)
            if result:
                return

        # Showdown
        player_score = best_five(player_hole, community)
        bot_score = best_five(bot_hole, community)

        embed = discord.Embed(title="Showdown", color=discord.Color.dark_gold())
        embed.add_field(name="Community", value=fmt(community), inline=False)
        embed.add_field(
            name="Your hand",
            value=f"{fmt(player_hole)} — **{HAND_NAMES[player_score[0]]}**",
            inline=False,
        )
        embed.add_field(
            name="Dealer's hand",
            value=f"{fmt(bot_hole)} — **{HAND_NAMES[bot_score[0]]}**",
            inline=False,
        )
        embed.add_field(name="Pot", value=f"**{pot}** coins", inline=False)

        if player_score > bot_score:
            new_bal = await db.add_balance(uid, gid, pot)
            embed.add_field(name="Result", value=f"You win **{pot}** coins! Balance: **{new_bal}**", inline=False)
        elif player_score < bot_score:
            new_bal = await db.get_balance(uid, gid)
            embed.add_field(name="Result", value=f"Dealer wins. Balance: **{new_bal}**", inline=False)
        else:
            split = pot // 2
            new_bal = await db.add_balance(uid, gid, split)
            embed.add_field(
                name="Result",
                value=f"Split pot — you each get **{split}** coins. Balance: **{new_bal}**",
                inline=False,
            )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Poker(bot))
