import discord
from discord.ext import commands
import aiohttp
import io
import os

HENRIK_API_KEY = os.getenv("HENRIK_API_KEY")
HENRIK_BASE = "https://api.henrikdev.xyz"

if not HENRIK_API_KEY:
    import warnings
    warnings.warn("HENRIK_API_KEY is not set — Valorant commands will fail at runtime.", stacklevel=2)


class Valorant(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    async def _resolve_account(self, name: str, tag: str) -> dict | None:
        headers = {"Authorization": HENRIK_API_KEY}
        try:
            url = f"{HENRIK_BASE}/valorant/v2/account/{name}/{tag}"
            async with self.session.get(url, headers=headers) as resp:
                data = await resp.json()
            if data.get("status") == 200:
                return data["data"]
            return None
        except aiohttp.ClientError:
            return None

    @commands.command(name="stats")
    async def stats(self, ctx: commands.Context, player: str = None):
        if not player or "#" not in player:
            await ctx.send("Usage: `!stats Name#TAG`  —  e.g. `!stats Jacob#NA1`")
            return

        name, tag = player.split("#", 1)
        headers = {"Authorization": HENRIK_API_KEY}

        try:
            # 1. Resolve account → get puuid + region
            account_url = f"{HENRIK_BASE}/valorant/v2/account/{name}/{tag}"
            async with self.session.get(account_url, headers=headers) as resp:
                account_data = await resp.json()

            if account_data.get("status") != 200:
                await ctx.send(f"Player **{player}** not found. Check the name and tag.")
                return

            account = account_data["data"]
            puuid = account["puuid"]
            region = account["region"].lower()

            # 2. Fetch current rank / RR
            mmr_url = f"{HENRIK_BASE}/valorant/v3/mmr/{region}/pc/{name}/{tag}"
            async with self.session.get(mmr_url, headers=headers) as resp:
                mmr_data = await resp.json()

            # 3. Fetch last 10 competitive matches
            matches_url = (
                f"{HENRIK_BASE}/valorant/v3/matches/{region}/{name}/{tag}"
                "?mode=competitive&size=10"
            )
            async with self.session.get(matches_url, headers=headers) as resp:
                matches_data = await resp.json()

        except aiohttp.ClientConnectorDNSError:
            await ctx.send("Could not reach the Valorant API — DNS resolution failed. Check your internet connection or try again later.")
            return
        except aiohttp.ClientError as e:
            await ctx.send(f"Network error while contacting the Valorant API: `{e}`")
            return

        # --- Parse rank ---
        rank_label = "Unranked"
        rr = 0
        if mmr_data.get("status") == 200:
            current = mmr_data["data"].get("current", {})
            rank_label = current.get("tier", {}).get("name", "Unranked")
            rr = current.get("rr", 0)

        # --- Parse match stats ---
        total_kills = total_deaths = total_hs = total_shots = total_wins = 0
        match_lines = []

        matches = (matches_data.get("data") or []) if matches_data.get("status") == 200 else []

        for match in matches:
            all_players = match.get("players", {}).get("all_players", [])
            target = next((p for p in all_players if p.get("puuid") == puuid), None)
            if not target:
                continue

            s = target.get("stats", {})
            kills = s.get("kills", 0)
            deaths = s.get("deaths", 0)
            hs = s.get("headshots", 0)
            body = s.get("bodyshots", 0)
            legs = s.get("legshots", 0)

            total_kills += kills
            total_deaths += deaths
            total_hs += hs
            total_shots += hs + body + legs

            team = target.get("team", "").lower()
            teams = match.get("teams", {})
            team_info = teams.get(team, {})
            won = team_info.get("has_won", False)
            if won:
                total_wins += 1
            result = "W" if won else "L"

            map_name = match.get("metadata", {}).get("map", "?")
            match_lines.append(f"{result} · {map_name} · {kills}/{deaths}/{s.get('assists', 0)}")

        kd = round(total_kills / max(total_deaths, 1), 2)
        hs_pct = round((total_hs / max(total_shots, 1)) * 100, 1)
        win_pct = round((total_wins / max(len(match_lines), 1)) * 100, 1)

        # --- Build embed ---
        embed = discord.Embed(
            title=f"Valorant Stats — {name}#{tag}",
            color=discord.Color.red(),
        )
        embed.add_field(name="Rank", value=rank_label, inline=True)
        embed.add_field(name="RR", value=str(rr), inline=True)
        embed.add_field(name="​", value="​", inline=True)

        if match_lines:
            n = len(match_lines)
            embed.add_field(name=f"K/D (last {n})", value=str(kd), inline=True)
            embed.add_field(name=f"HS% (last {n})", value=f"{hs_pct}%", inline=True)
            embed.add_field(name="​", value="​", inline=True)
            troll = "\n💀 you have to lock in bro" if win_pct < 50 else ""
            embed.add_field(
                name=f"Last {n} matches — Win Rate: {win_pct}%{troll}",
                value="\n".join(match_lines),
                inline=False,
            )
        else:
            embed.add_field(name="Matches", value="No recent competitive matches found.", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="rank")
    async def rank(self, ctx: commands.Context, player: str = None):
        await ctx.send("🚧 `!rank` is coming soon.")

    @commands.command(name="history")
    async def history(self, ctx: commands.Context, player: str = None):
        await ctx.send("🚧 `!history` is coming soon.")

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        await ctx.send("🚧 `!leaderboard` is coming soon.")

    @commands.command(name="agent")
    async def agent(self, ctx: commands.Context, player: str = None):
        await ctx.send("🚧 `!agent` is coming soon.")

    @commands.command(name="server")
    async def server(self, ctx: commands.Context, region: str = "na"):
        VALID_REGIONS = {"na", "eu", "ap", "kr", "latam", "br"}
        if region not in VALID_REGIONS:
            await ctx.send(f"Invalid region. Choose from: {', '.join(sorted(VALID_REGIONS))}")
            return
        headers = {"Authorization": HENRIK_API_KEY}
        try:
            async with self.session.get(f"{HENRIK_BASE}/valorant/v1/status/{region}", headers=headers) as resp:
                data = await resp.json()
        except aiohttp.ClientError as e:
            await ctx.send(f"Network error: `{e}`")
            return
        if data.get("status") != 200:
            await ctx.send("Could not fetch server status.")
            return
        maintenances = data["data"].get("maintenances", [])
        incidents = data["data"].get("incidents", [])
        def get_title(entry):
            titles = entry.get("titles", [])
            en = next((t["content"] for t in titles if t.get("locale") == "en_US"), None)
            return en or (titles[0]["content"] if titles else "Unknown")
        if not maintenances and not incidents:
            embed = discord.Embed(title=f"Valorant Server Status — {region.upper()}", description="✅ All systems operational", color=discord.Color.green())
        else:
            embed = discord.Embed(title=f"Valorant Server Status — {region.upper()}", color=discord.Color.orange())
            for m in maintenances:
                embed.add_field(name=f"🔧 Maintenance — {m.get('maintenance_status', '?')}", value=get_title(m), inline=False)
            for i in incidents:
                embed.add_field(name=f"⚠️ Incident — {i.get('incident_severity', '?')}", value=get_title(i), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="news")
    async def news(self, ctx: commands.Context):
        headers = {"Authorization": HENRIK_API_KEY}
        try:
            async with self.session.get(f"{HENRIK_BASE}/valorant/v1/website/en-us", headers=headers) as resp:
                data = await resp.json()
        except aiohttp.ClientError as e:
            await ctx.send(f"Network error: `{e}`")
            return
        if data.get("status") != 200:
            await ctx.send("Could not fetch Valorant news.")
            return
        articles = (data.get("data") or [])[:5]
        embed = discord.Embed(title="Valorant News", color=discord.Color.red())
        for a in articles:
            embed.add_field(
                name=f"[{a.get('category', '?').title()}] {a.get('title', '?')}",
                value=f"{a.get('date', '?')} — {a.get('url', '')}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="rr")
    async def rr(self, ctx: commands.Context, player: str = None):
        if not player or "#" not in player:
            await ctx.send("Usage: `!rr Name#TAG`")
            return
        name, tag = player.split("#", 1)
        account = await self._resolve_account(name, tag)
        if not account:
            await ctx.send(f"Player **{player}** not found.")
            return
        region = account["region"].lower()
        headers = {"Authorization": HENRIK_API_KEY}
        try:
            async with self.session.get(f"{HENRIK_BASE}/valorant/v1/mmr-history/{region}/{name}/{tag}", headers=headers) as resp:
                history_data = await resp.json()
            async with self.session.get(f"{HENRIK_BASE}/valorant/v3/mmr/{region}/pc/{name}/{tag}", headers=headers) as resp:
                mmr_data = await resp.json()
        except aiohttp.ClientError as e:
            await ctx.send(f"Network error: `{e}`")
            return
        entries = (history_data.get("data") or [])[:10]
        changes = [e.get("mmr_change_to_last_game", 0) for e in entries]
        sparkline = "  ".join(f"+{c}" if c >= 0 else str(c) for c in changes)
        net = sum(changes)
        net_str = f"+{net}" if net >= 0 else str(net)
        current_rr = 0
        if mmr_data.get("status") == 200:
            current_rr = mmr_data["data"].get("current", {}).get("rr", 0)
        embed = discord.Embed(title=f"RR History — {name}#{tag}", color=discord.Color.red())
        embed.add_field(name=f"Last {len(changes)} Games", value=sparkline or "No data", inline=False)
        embed.add_field(name="Net", value=net_str, inline=True)
        embed.add_field(name="Current RR", value=str(current_rr), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="map")
    async def map_stats(self, ctx: commands.Context, player: str = None):
        if not player or "#" not in player:
            await ctx.send("Usage: `!map Name#TAG`")
            return
        name, tag = player.split("#", 1)
        account = await self._resolve_account(name, tag)
        if not account:
            await ctx.send(f"Player **{player}** not found.")
            return
        region = account["region"].lower()
        puuid = account["puuid"]
        headers = {"Authorization": HENRIK_API_KEY}
        try:
            async with self.session.get(
                f"{HENRIK_BASE}/valorant/v3/matches/{region}/{name}/{tag}?mode=competitive&size=10",
                headers=headers
            ) as resp:
                matches_data = await resp.json()
        except aiohttp.ClientError as e:
            await ctx.send(f"Network error: `{e}`")
            return
        matches = (matches_data.get("data") or []) if matches_data.get("status") == 200 else []
        map_stats = {}
        for match in matches:
            map_name = match.get("metadata", {}).get("map", "Unknown")
            all_players = match.get("players", {}).get("all_players", [])
            target = next((p for p in all_players if p.get("puuid") == puuid), None)
            if not target:
                continue
            s = target.get("stats", {})
            team = target.get("team", "").lower()
            won = match.get("teams", {}).get(team, {}).get("has_won", False)
            if map_name not in map_stats:
                map_stats[map_name] = {"games": 0, "wins": 0, "kills": 0, "deaths": 0}
            map_stats[map_name]["games"] += 1
            map_stats[map_name]["wins"] += int(won)
            map_stats[map_name]["kills"] += s.get("kills", 0)
            map_stats[map_name]["deaths"] += s.get("deaths", 0)
        if not map_stats:
            await ctx.send("No recent competitive matches found.")
            return
        sorted_maps = sorted(map_stats.items(), key=lambda x: x[1]["games"], reverse=True)[:5]
        embed = discord.Embed(title=f"Map Stats — {name}#{tag}", color=discord.Color.red())
        for map_name, s in sorted_maps:
            win_pct = round(s["wins"] / s["games"] * 100, 1)
            kd = round(s["kills"] / max(s["deaths"], 1), 2)
            embed.add_field(
                name=map_name,
                value=f"{s['games']}G · {win_pct}% WR · {kd} K/D",
                inline=True,
            )
        eligible = [(m, s) for m, s in map_stats.items() if s["games"] >= 2]
        if eligible:
            best = max(eligible, key=lambda x: x[1]["wins"] / x[1]["games"])
            worst = min(eligible, key=lambda x: x[1]["wins"] / x[1]["games"])
            embed.set_footer(text=f"Best: {best[0]} | Worst: {worst[0]}")
        await ctx.send(embed=embed)

    @commands.command(name="last")
    async def last(self, ctx: commands.Context, player: str = None):
        if not player or "#" not in player:
            await ctx.send("Usage: `!last Name#TAG`")
            return
        name, tag = player.split("#", 1)
        account = await self._resolve_account(name, tag)
        if not account:
            await ctx.send(f"Player **{player}** not found.")
            return
        region = account["region"].lower()
        puuid = account["puuid"]
        headers = {"Authorization": HENRIK_API_KEY}
        try:
            async with self.session.get(
                f"{HENRIK_BASE}/valorant/v3/matches/{region}/{name}/{tag}?mode=competitive&size=1",
                headers=headers
            ) as resp:
                matches_data = await resp.json()
        except aiohttp.ClientError as e:
            await ctx.send(f"Network error: `{e}`")
            return
        matches = (matches_data.get("data") or []) if matches_data.get("status") == 200 else []
        if not matches:
            await ctx.send("No recent competitive matches found.")
            return
        match = matches[0]
        map_name = match.get("metadata", {}).get("map", "?")
        teams = match.get("teams", {})
        all_players = match.get("players", {}).get("all_players", [])
        target = next((p for p in all_players if p.get("puuid") == puuid), None)
        player_team = target.get("team", "").lower() if target else "red"
        enemy_team = "blue" if player_team == "red" else "red"
        player_team_won = teams.get(player_team, {}).get("has_won", False)
        player_rounds = teams.get(player_team, {}).get("rounds_won", 0)
        enemy_rounds = teams.get(enemy_team, {}).get("rounds_won", 0)
        def fmt_player(p):
            s = p.get("stats", {})
            agent = p.get("character", "?")
            k, d, a = s.get("kills", 0), s.get("deaths", 0), s.get("assists", 0)
            score = s.get("score", 0)
            prefix = "→ " if p.get("puuid") == puuid else "   "
            return f"{prefix}{agent:<12} {k}/{d}/{a}  CS:{score}"
        my_team = sorted([p for p in all_players if p.get("team", "").lower() == player_team], key=lambda p: p.get("stats", {}).get("score", 0), reverse=True)
        opp_team = sorted([p for p in all_players if p.get("team", "").lower() == enemy_team], key=lambda p: p.get("stats", {}).get("score", 0), reverse=True)
        color = discord.Color.green() if player_team_won else discord.Color.red()
        result = "W" if player_team_won else "L"
        embed = discord.Embed(
            title=f"{map_name} — {result} {player_rounds}–{enemy_rounds}",
            color=color,
        )
        embed.add_field(name="Your Team", value="```\n" + "\n".join(fmt_player(p) for p in my_team) + "\n```", inline=False)
        embed.add_field(name="Enemy Team", value="```\n" + "\n".join(fmt_player(p) for p in opp_team) + "\n```", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="compare")
    async def compare(self, ctx: commands.Context, player1: str = None, player2: str = None):
        if not player1 or not player2 or "#" not in player1 or "#" not in player2:
            await ctx.send("Usage: `!compare Name1#TAG1 Name2#TAG2`")
            return
        headers = {"Authorization": HENRIK_API_KEY}
        async def get_stats(player):
            n, t = player.split("#", 1)
            account = await self._resolve_account(n, t)
            if not account:
                return None
            region = account["region"].lower()
            puuid = account["puuid"]
            try:
                async with self.session.get(f"{HENRIK_BASE}/valorant/v3/mmr/{region}/pc/{n}/{t}", headers=headers) as resp:
                    mmr_data = await resp.json()
                async with self.session.get(
                    f"{HENRIK_BASE}/valorant/v3/matches/{region}/{n}/{t}?mode=competitive&size=10",
                    headers=headers
                ) as resp:
                    matches_data = await resp.json()
            except aiohttp.ClientError:
                return None
            rank = "Unranked"
            tier_id = 0
            if mmr_data.get("status") == 200:
                current = mmr_data["data"].get("current", {})
                rank = current.get("tier", {}).get("name", "Unranked")
                tier_id = current.get("tier", {}).get("id", 0)
            kills = deaths = hs = shots = wins = games = 0
            matches = (matches_data.get("data") or []) if matches_data.get("status") == 200 else []
            for match in matches:
                all_players = match.get("players", {}).get("all_players", [])
                p = next((x for x in all_players if x.get("puuid") == puuid), None)
                if not p:
                    continue
                s = p.get("stats", {})
                kills += s.get("kills", 0)
                deaths += s.get("deaths", 0)
                hs += s.get("headshots", 0)
                shots += s.get("headshots", 0) + s.get("bodyshots", 0) + s.get("legshots", 0)
                team = p.get("team", "").lower()
                if match.get("teams", {}).get(team, {}).get("has_won", False):
                    wins += 1
                games += 1
            return {
                "name": player,
                "rank": rank,
                "tier_id": tier_id,
                "kd": round(kills / max(deaths, 1), 2),
                "hs_pct": round(hs / max(shots, 1) * 100, 1),
                "win_pct": round(wins / max(games, 1) * 100, 1),
            }
        try:
            s1 = await get_stats(player1)
            s2 = await get_stats(player2)
        except aiohttp.ClientError as e:
            await ctx.send(f"Network error: `{e}`")
            return
        if not s1:
            await ctx.send(f"Player **{player1}** not found.")
            return
        if not s2:
            await ctx.send(f"Player **{player2}** not found.")
            return
        def star(v1, v2, higher_better=True):
            if higher_better:
                return ("★", "") if v1 > v2 else ("", "★") if v2 > v1 else ("", "")
            return ("★", "") if v1 < v2 else ("", "★") if v2 < v1 else ("", "")
        embed = discord.Embed(title=f"Compare: {player1} vs {player2}", color=discord.Color.blurple())
        r1s, r2s = star(s1["tier_id"], s2["tier_id"])
        embed.add_field(name="Rank", value=f"{r1s}{s1['rank']}", inline=True)
        embed.add_field(name="​", value="vs", inline=True)
        embed.add_field(name="Rank", value=f"{r2s}{s2['rank']}", inline=True)
        k1s, k2s = star(s1["kd"], s2["kd"])
        embed.add_field(name="K/D", value=f"{k1s}{s1['kd']}", inline=True)
        embed.add_field(name="​", value="—", inline=True)
        embed.add_field(name="K/D", value=f"{k2s}{s2['kd']}", inline=True)
        h1s, h2s = star(s1["hs_pct"], s2["hs_pct"])
        embed.add_field(name="HS%", value=f"{h1s}{s1['hs_pct']}%", inline=True)
        embed.add_field(name="​", value="—", inline=True)
        embed.add_field(name="HS%", value=f"{h2s}{s2['hs_pct']}%", inline=True)
        w1s, w2s = star(s1["win_pct"], s2["win_pct"])
        embed.add_field(name="Win Rate", value=f"{w1s}{s1['win_pct']}%", inline=True)
        embed.add_field(name="​", value="—", inline=True)
        embed.add_field(name="Win Rate", value=f"{w2s}{s2['win_pct']}%", inline=True)
        embed.set_footer(text=f"{player1} (left)  |  {player2} (right)  |  ★ = better stat")
        await ctx.send(embed=embed)

    @commands.command(name="crosshair")
    async def crosshair(self, ctx: commands.Context, *, code: str = None):
        if not code:
            await ctx.send("Usage: `!crosshair <crosshair-code>`  — copy the code from Valorant Settings → Crosshair → Import")
            return
        headers = {"Authorization": HENRIK_API_KEY}
        try:
            async with self.session.get(
                f"{HENRIK_BASE}/valorant/v1/crosshair/generate",
                params={"id": code},
                headers=headers,
            ) as resp:
                if resp.status != 200 or "image" not in resp.content_type:
                    error_text = "Invalid crosshair code or API error."
                    try:
                        err = await resp.json()
                        error_text = err.get("errors", [{}])[0].get("message", error_text)
                    except Exception:
                        pass
                    await ctx.send(f"Could not render crosshair: {error_text}")
                    return
                image_bytes = await resp.read()
        except aiohttp.ClientError as e:
            await ctx.send(f"Network error: `{e}`")
            return
        embed = discord.Embed(title="Crosshair Preview", color=discord.Color.red())
        embed.set_image(url="attachment://crosshair.png")
        f = discord.File(fp=io.BytesIO(image_bytes), filename="crosshair.png")
        await ctx.send(embed=embed, file=f)


async def setup(bot: commands.Bot):
    await bot.add_cog(Valorant(bot))
