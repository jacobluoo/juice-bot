# Plan: Valorant New Commands (API-Driven Expansion)

## Task Description
Design and implement seven new Valorant commands that leverage Henrik's API endpoints not yet used by the bot. These go beyond filling in the four stubs (covered by `valorant-commands-expansion.md`) — these are entirely new commands surfacing data the bot doesn't expose at all today: server health, RR trend history, per-map stats, a full match scoreboard, side-by-side player comparison, crosshair rendering, and Valorant news headlines.

Each command follows the established pattern in `cogs/valorant.py`: parse args → async GET to Henrik's API via `self.session` → parse JSON (or bytes) → send a `discord.Embed` (or file attachment). One command (`!crosshair`) introduces a new pattern: fetching a PNG and sending it as a `discord.File`.

## Objective
Add seven new working Valorant commands to `cogs/valorant.py` that each leverage a distinct Henrik API endpoint, updating `CLAUDE.md` to document them, resulting in a substantially richer Valorant feature set.

## Assumptions
- **`!rr` vs `!rank` overlap**: `!rank` (from the stub expansion plan) shows current rank + RR + peak + act progression. `!rr` in this plan is specifically the raw RR change history — a sparkline of `+18 -20 +22 ...` over the last 10 games, plus a net total. They answer different questions ("where am I ranked?" vs "how is my RR trending?"). Flag if you want them merged.
- **`!last` scope**: Shows one complete match scoreboard (all players, both teams). If you instead want just the queried player's performance in their last game (like a shorter `!history` entry), flag this.
- **`!compare` argument format**: `!compare Name1#TAG1 Name2#TAG2` — two space-separated `Name#TAG` tokens. The command signature is `async def compare(self, ctx, player1: str, player2: str)`. This requires players to not have spaces in their names/tags, which is true for Valorant accounts.
- **`!crosshair` code format**: Accepts the in-game crosshair profile code string (e.g. `0;s;1;P;...`). Henrik's endpoint `GET /valorant/v1/crosshair/generate?id={code}` handles decoding it. The bot sends the resulting PNG inline.
- **`!news` region**: Defaults to `en-us` locale. Not parameterized. Flag if you want other locales.
- **`_resolve_account` helper**: Assumes the helper was added by the `valorant-commands-expansion` plan. If that plan hasn't run yet, this plan's builder must add it first (check for presence, add if absent).
- **No personal store commands**: Henrik's API does not expose individual player stores without OAuth token injection — not in scope.

## Problem Statement
The bot's Valorant feature set is limited to stats/rank from the existing `!stats` command and four stubs. Henrik's API exposes at least a dozen additional endpoints — server status, RR history, crosshair rendering, news, leaderboard data, and more — none of which the bot currently surfaces. Players using the bot have no way to check if servers are down, see their RR trend, render a crosshair, or get a full match scoreboard without leaving Discord.

## Solution Approach
All seven commands are added to the existing `Valorant` cog in `cogs/valorant.py`. They share the cog's `aiohttp.ClientSession` and auth headers. Six commands return `discord.Embed` objects following existing conventions. One command (`!crosshair`) introduces a binary image fetch pattern: `await resp.read()` returns PNG bytes which are wrapped in `io.BytesIO` and sent as `discord.File`, with the embed using `set_image(url="attachment://crosshair.png")` to render inline.

No new files, no DB changes, no new dependencies.

---

## Commands Being Added

### `!server [region]`
- **Endpoint**: `GET /valorant/v1/status/{region}` (default region: `na`)
- **Valid regions**: `na`, `eu`, `ap`, `kr`, `latam`, `br`
- **Response shape**: `data.maintenances[]` and `data.incidents[]`, each with `titles[{"content", "locale"}]`, `maintenance_status`/`incident_severity`, `updated_at`
- **Embed**: Green if both arrays empty ("All systems operational"). Otherwise list active items by severity.

### `!rr Name#TAG`
- **Endpoint**: `GET /valorant/v1/mmr-history/{region}/{name}/{tag}`
- **Response shape**: `data[]` array (newest-first), each entry has `mmr_change_to_last_game` (int, signed), `currenttierpatched` (rank name), `map.name`, `date`
- **Embed**: Shows last 10 games as `+18  -20  +22  ...`, net total, and current RR from a parallel MMR v3 call.

### `!last Name#TAG`
- **Endpoint**: `GET /valorant/v3/matches/{region}/{name}/{tag}?mode=competitive&size=1`
- **Response shape**: Same match structure used by `!stats` — `metadata.map`, `teams.red/blue.rounds_won`, `teams.red/blue.has_won`, `players.all_players[].character`, `.stats.kills/deaths/assists/score`, `.team`
- **Embed**: Map, final round score, full two-team scoreboard sorted by combat score desc. Queried player row marked with `→`.

### `!compare Name1#TAG1 Name2#TAG2`
- **Endpoints**: Account + last 10 competitive matches for each player (4 total requests)
- **Fields compared**: Rank, K/D, HS%, Win Rate, Avg combat score
- **Embed**: Two columns via inline fields — one column per player. "Winner" symbol (★) on whichever player leads each stat.

### `!crosshair <code>`
- **Endpoint**: `GET /valorant/v1/crosshair/generate?id={code}` — returns raw PNG bytes (Content-Type: image/png), NOT JSON
- **Pattern**: `image_bytes = await resp.read()` → `discord.File(fp=io.BytesIO(image_bytes), filename="crosshair.png")` → `embed.set_image(url="attachment://crosshair.png")` → `await ctx.send(embed=embed, file=f)`
- **Embed**: Minimal — title "Crosshair Preview" + the inline image.

### `!news`
- **Endpoint**: `GET /valorant/v1/website/en-us`
- **Response shape**: `data[]` array, each entry has `title`, `category`, `date` (string `YYYY/MM/DD`), `url`, `banner_url`
- **Embed**: Last 5 articles, each as a field: title (linked), category tag, date.

### `!map Name#TAG`
- **Endpoint**: Same matches endpoint as `!stats` — `size=10`
- **Aggregation**: Group by `metadata.map`. Per map: games played, wins, kills, deaths.
- **Embed**: Top 5 maps by games played. Shows win% and K/D per map. Footer highlights best map (highest win%) and worst map (lowest win%).

---

## Verified API Patterns

| Library/API | Version Checked | Recommended Pattern | Deprecation Warnings |
|-------------|----------------|--------------------|--------------------|
| discord.py — `discord.File` + `ctx.send` | 2.x (Aug 2025) | `discord.File(fp=io.BytesIO(image_bytes), filename="crosshair.png")` then `await ctx.send(embed=embed, file=f)`. Use `embed.set_image(url="attachment://crosshair.png")` to render inline — filename in URL must exactly match `filename` param. | `fp` must be file-like (`io.BytesIO`); raw `bytes` not accepted directly. None in 2.x. |
| aiohttp — binary response | 3.x (Aug 2025) | `await resp.read()` reads entire body as `bytes`. Use this for PNG payloads. `resp.content.read()` (StreamReader) also works but is lower-level. | None. Note: buffers full body in memory — acceptable for crosshair PNGs. |
| Henrik Valorant API — status | v1 | `GET /valorant/v1/status/{region}` with `Authorization` header. Maintenances in `data.maintenances`, incidents in `data.incidents`. | None known. |
| Henrik Valorant API — mmr-history | v1 | `GET /valorant/v1/mmr-history/{region}/{name}/{tag}` with `Authorization` header. `data[].mmr_change_to_last_game` is signed int. Newest entry first. | v1 only — no v2/v3 variant exists for this endpoint. |
| Henrik Valorant API — crosshair | v1 | `GET /valorant/v1/crosshair/generate?id={code}` with `Authorization` header. Response is raw PNG bytes, not JSON. Check `resp.content_type` — on invalid code the API may return a JSON error instead of PNG. | None known. |
| Henrik Valorant API — website news | v1 | `GET /valorant/v1/website/en-us` with `Authorization` header. `data[].url` is the full article URL. | None known. |

> Context7 MCP unavailable during research. Patterns verified from training knowledge (cutoff Aug 2025) and cross-referenced with existing codebase patterns in `cogs/valorant.py`. Manual verification against henrikdev.xyz docs recommended before builder execution.

## Relevant Files

- `cogs/valorant.py` — all new commands added here. Introduces `import io` at the top (needed for `io.BytesIO` in `!crosshair`).
- `CLAUDE.md` — command table updated to document all 7 new commands.

### New Files
None.

## Implementation Phases

### Phase 1: Foundation
Verify `_resolve_account(name, tag)` helper exists in the cog (added by the expansion plan). Add it if absent. Add `import io` to the imports block. These are prerequisites for Phase 2.

### Phase 2: Core Implementation
Implement all seven commands in this order (each is independent once the helper exists):

1. `!server` — simplest, no player lookup, good warm-up
2. `!news` — stateless, no player lookup, validates the session works for a new endpoint
3. `!rr` — uses `_resolve_account`, introduces the mmr-history endpoint
4. `!map` — uses existing match endpoint with new aggregation logic
5. `!last` — uses match endpoint with scoreboard rendering (more complex embed layout)
6. `!compare` — uses `_resolve_account` twice, parallel-ish fetch pattern
7. `!crosshair` — introduces the binary file attachment pattern (save for last to isolate the new pattern)

### Phase 3: Integration & Polish
- Confirm all new commands wrap API calls in `try/except aiohttp.ClientError`
- Confirm `!crosshair` handles the case where Henrik returns a JSON error (invalid code) instead of PNG bytes — check `resp.content_type` before calling `resp.read()`, or check the status code
- Update `CLAUDE.md` command table with all 7 new entries
- Confirm no existing `!stats`, `!rank`, `!history`, `!agent`, `!leaderboard` behavior was changed

## Team Orchestration

You operate as the team lead and orchestrate the team to execute the plan. You NEVER operate directly on the codebase — use `Task` and `Task*` tools to deploy team members.

### Team Members

- Builder
  - Name: valorant-new-builder
  - Role: Implement all seven new commands in `cogs/valorant.py` and update `CLAUDE.md`
  - Agent Type: builder
  - Resume: true

- Validator
  - Name: valorant-new-validator
  - Role: Read the finished `cogs/valorant.py` and verify all seven commands exist, use correct patterns, and meet acceptance criteria. Read-only — no code changes.
  - Agent Type: validator
  - Resume: false

### Pipeline Determinism Map

| Node | Determinism | Inputs | Output | Can Change? |
|------|------------|--------|--------|-------------|
| Context7 lookup | NON-DETERMINISTIC | API/library names | Current docs/patterns | External state varies |
| Plan creation | NON-DETERMINISTIC | Prompt + codebase + Context7 findings + judgment | Plan document | Already was non-deterministic |
| Builder | DETERMINISTIC | Plan document only | Code changes | **NO — must stay deterministic** |
| Validator | DETERMINISTIC | Code + plan acceptance criteria | Pass/Fail | **NO — must stay deterministic** |
| verify-changes subagent 3 | NON-DETERMINISTIC (advisory) | Finished code | Currency report | Advisory only, does not gate |

## Step by Step Tasks

### 1. Verify/Add `_resolve_account` Helper and `import io`
- **Task ID**: foundation-setup
- **Depends On**: none
- **Assigned To**: valorant-new-builder
- **Agent Type**: builder
- **Parallel**: false
- Read `cogs/valorant.py` in full
- If `_resolve_account` method is NOT present on the `Valorant` cog, add it: `async def _resolve_account(self, name: str, tag: str) -> dict | None` — calls `GET /valorant/v2/account/{name}/{tag}`, returns `account_data["data"]` on status 200, else `None`
- If `import io` is NOT in the imports block, add it
- Mark task complete

### 2. Implement `!server`
- **Task ID**: impl-server
- **Depends On**: foundation-setup
- **Assigned To**: valorant-new-builder
- **Agent Type**: builder
- **Parallel**: false
- Add `async def server(self, ctx, region: str = "na")` command
- Validate region against `{"na", "eu", "ap", "kr", "latam", "br"}` — send usage error if invalid
- Call `GET {HENRIK_BASE}/valorant/v1/status/{region}` with auth header
- Parse `data.maintenances` and `data.incidents`; for each entry get English title from `titles` array (find item where `"locale"` is `"en_US"` or fall back to first item)
- If both arrays are empty: green embed "✅ All systems operational"
- If incidents: orange embed, list each with severity and title
- If maintenances: yellow embed, list each with status and title
- Wrap in `try/except aiohttp.ClientError`

### 3. Implement `!news`
- **Task ID**: impl-news
- **Depends On**: impl-server
- **Assigned To**: valorant-new-builder
- **Agent Type**: builder
- **Parallel**: false
- Add `async def news(self, ctx)` command (no arguments)
- Call `GET {HENRIK_BASE}/valorant/v1/website/en-us` with auth header
- Parse `data` array — take first 5 entries (already newest-first from the API)
- Build embed: title "Valorant News", color `discord.Color.red()`
- For each article: one inline=False field with `name=f"[{article['category'].title()}] {article['title']}"` and `value=f"{article['date']} — {article['url']}"`
- Wrap in `try/except aiohttp.ClientError`

### 4. Implement `!rr`
- **Task ID**: impl-rr
- **Depends On**: impl-news
- **Assigned To**: valorant-new-builder
- **Agent Type**: builder
- **Parallel**: false
- Add `async def rr(self, ctx, player: str = None)` command
- Validate `player` and `"#"` presence — send usage on failure
- Use `_resolve_account` to get `region`; send "player not found" if `None`
- Make two parallel-ish (sequential is fine) calls:
  - `GET /valorant/v1/mmr-history/{region}/{name}/{tag}` → RR change history
  - `GET /valorant/v3/mmr/{region}/pc/{name}/{tag}` → current RR
- From history `data` (newest-first), take first 10 entries; build a space-separated string: `+18  -20  +22 ...` (prefix `+` if positive, `-` if negative, use `f"+{v}"` for positive)
- Calculate net = sum of those 10 changes
- Embed: title `RR History — {name}#{tag}`, fields: "Last 10 Changes" (the sparkline string), "Net" (`+{net}` or `{net}`), "Current RR" (from MMR v3 `data.current.rr`)
- Wrap in `try/except aiohttp.ClientError`

### 5. Implement `!map`
- **Task ID**: impl-map
- **Depends On**: impl-rr
- **Assigned To**: valorant-new-builder
- **Agent Type**: builder
- **Parallel**: false
- Add `async def map_stats(self, ctx, player: str = None)` command (name `map_stats` to avoid shadowing the built-in `map`; Discord command name stays `"map"` via `@commands.command(name="map")`)
- Use `_resolve_account` for region + puuid
- Fetch last 10 competitive matches (same URL pattern as `!stats`)
- Aggregate into `dict[map_name, {games, wins, kills, deaths}]`
- Sort by games desc, take top 5
- For each: compute `win_pct`, `kd = round(kills/max(deaths,1), 2)`
- Embed: title `Map Stats — {name}#{tag}`, one inline=True field per map showing games/win%/K/D
- Footer: "Best: {highest win% map} | Worst: {lowest win% map (min 2 games)}"
- Wrap in `try/except aiohttp.ClientError`

### 6. Implement `!last`
- **Task ID**: impl-last
- **Depends On**: impl-map
- **Assigned To**: valorant-new-builder
- **Agent Type**: builder
- **Parallel**: false
- Add `async def last(self, ctx, player: str = None)` command
- Use `_resolve_account` for region + puuid
- Fetch `GET /valorant/v3/matches/{region}/{name}/{tag}?mode=competitive&size=1`
- Parse match[0]: map name, `teams.red.rounds_won`, `teams.blue.rounds_won`, which team won
- Determine queried player's team from `players.all_players` (match by puuid)
- Build scoreboard: two groups (player's team first, then enemy team). Within each group, sort by `stats.score` desc.
- Each player line: `→ Agent  K/D/A  CS` (arrow prefix only for queried player)
- Embed color: green if win, red if loss
- Embed title: `{map} — W {r_won}-{r_lost}` or `{map} — L {r_lost}-{r_won}` from the queried player's perspective
- Two fields: "Your Team" and "Enemy Team", each a code block with the player lines
- Wrap in `try/except aiohttp.ClientError`

### 7. Implement `!compare`
- **Task ID**: impl-compare
- **Depends On**: impl-last
- **Assigned To**: valorant-new-builder
- **Agent Type**: builder
- **Parallel**: false
- Add `async def compare(self, ctx, player1: str = None, player2: str = None)` command
- Validate both args present and contain `"#"` — send usage error otherwise
- For each player: `_resolve_account` → get puuid + region, then fetch last 10 competitive matches
- Aggregate per player: rank (from MMR v3), K/D, HS%, win rate
- Build embed with two-column layout using inline fields:
  - Row pattern: `[stat label]` (inline=False) then `[p1 value]` (inline=True) then `[p2 value]` (inline=True)
  - Stats: Rank, K/D, HS%, Win Rate
  - Append `★` to the better value in each stat row (higher K/D, HS%, win rate wins; rank comparison is trickier — omit ★ for rank or just display both)
- Wrap all API calls in `try/except aiohttp.ClientError`

### 8. Implement `!crosshair`
- **Task ID**: impl-crosshair
- **Depends On**: impl-compare
- **Assigned To**: valorant-new-builder
- **Agent Type**: builder
- **Parallel**: false
- Add `async def crosshair(self, ctx, *, code: str = None)` command (note `*` so the code can contain spaces if needed)
- Validate `code` is not None — send usage on failure
- Call `GET {HENRIK_BASE}/valorant/v1/crosshair/generate?id={code}` with auth header
- Check `resp.status` — if not 200, check if response is JSON (error message) and relay the error, e.g. "Invalid crosshair code"
- If status 200: `image_bytes = await resp.read()`
- Build embed: `title="Crosshair Preview"`, `color=discord.Color.red()`, `set_image(url="attachment://crosshair.png")`
- `f = discord.File(fp=io.BytesIO(image_bytes), filename="crosshair.png")`
- `await ctx.send(embed=embed, file=f)`
- Wrap outer block in `try/except aiohttp.ClientError`

### 9. Update CLAUDE.md
- **Task ID**: update-claude-md
- **Depends On**: impl-crosshair
- **Assigned To**: valorant-new-builder
- **Agent Type**: builder
- **Parallel**: false
- Add 7 new rows to the command table in `CLAUDE.md`:

| Command | Cog | Status |
|---|---|---|
| `!server [region]` | valorant | done |
| `!rr Name#TAG` | valorant | done |
| `!last Name#TAG` | valorant | done |
| `!compare Name1#TAG1 Name2#TAG2` | valorant | done |
| `!crosshair <code>` | valorant | done |
| `!news` | valorant | done |
| `!map Name#TAG` | valorant | done |

### 10. Validate All Changes
- **Task ID**: validate-all
- **Depends On**: update-claude-md
- **Assigned To**: valorant-new-validator
- **Agent Type**: validator
- **Parallel**: false
- Read `cogs/valorant.py` in full — verify all 7 commands exist as methods on the `Valorant` cog
- Verify `import io` is present
- Verify `_resolve_account` helper exists
- Verify `!crosshair` uses `io.BytesIO` and `discord.File` pattern, NOT `await resp.json()`
- Verify `!server` validates the region input
- Verify `!compare` accepts two player arguments
- Verify all 7 commands have `try/except aiohttp.ClientError` blocks
- Verify no existing commands (`!stats`, `!rank`, `!history`, `!agent`, `!leaderboard`) were modified
- Verify CLAUDE.md has 7 new rows
- Run: `python -m py_compile cogs/valorant.py` — must exit 0
- Run: `grep -c "coming soon" cogs/valorant.py` — must return 0 (no new stubs added)

## Acceptance Criteria

1. `!server` returns an embed. `!server eu` works. `!server xyz` sends an error, not a traceback.
2. `!news` returns an embed with 5 or fewer recent Valorant article titles and URLs.
3. `!rr Name#TAG` returns an embed showing a line of signed RR changes (+/−) and a net total.
4. `!map Name#TAG` returns an embed showing per-map win rate and K/D, sorted by games played.
5. `!last Name#TAG` returns an embed with the full scoreboard of the most recent competitive match, showing both teams' players with K/D/A and combat score.
6. `!compare Name1#TAG1 Name2#TAG2` returns a side-by-side embed comparing K/D, HS%, and win rate for both players.
7. `!crosshair <code>` returns a Discord message with an inline PNG image attachment showing the rendered crosshair. An invalid code sends an error message, not a traceback.
8. All 7 commands handle API errors gracefully — `aiohttp.ClientError` produces a user-facing message, not an uncaught exception.
9. No existing Valorant command behavior (`!stats`, `!rank`, `!history`, `!agent`, `!leaderboard`) is changed.
10. `import io` is present in the file and `_resolve_account` helper is present on the cog.
11. `python -m py_compile cogs/valorant.py` exits cleanly.
12. CLAUDE.md command table has 7 new entries all marked `done`.

## Validation Commands

```bash
# Syntax check
python -m py_compile cogs/valorant.py && echo "PASS: no syntax errors"

# No accidental stubs
grep -n "coming soon" cogs/valorant.py
# Expected: 0 matches

# All 7 commands registered
grep -n "@commands.command" cogs/valorant.py
# Expected: see server, news, rr, map, last, compare, crosshair (plus existing ones)

# Binary file pattern present
grep -n "io.BytesIO" cogs/valorant.py
# Expected: at least 1 match (crosshair command)

# Helper present
grep -n "_resolve_account" cogs/valorant.py
# Expected: definition + multiple call sites

# CLAUDE.md updated
grep -E "server|!rr|!last|!compare|!crosshair|!news|!map" CLAUDE.md
# Expected: all 7 new commands appear
```

## Notes

- **Ordering of the expansion plans**: This plan assumes `valorant-commands-expansion.md` has been executed first (it adds `_resolve_account`). If running this plan standalone, the builder must add that helper in Task 1.
- **`!crosshair` invalid code handling**: Henrik's endpoint may return a JSON `{"status": 400, "errors": [...]}` for an invalid code instead of PNG bytes. The builder must check `resp.status` before calling `resp.read()` and handle this gracefully.
- **`!last` scoreboard width**: Discord embed field values have a 1024-char limit. A 10-player match scoreboard with moderate-length agent names and K/D/A should fit, but if it approaches the limit, truncate to top 5 per team with a "..." footer note.
- **`!compare` rank comparison**: Rank tiers are integers (0–27 in Henrik's API). The builder can compare `data.current.tier.id` numerically to determine who ranks higher, rather than trying to string-compare rank names.
- **`!map` command name collision**: Python's built-in `map` function can't be overwritten, so the method must be named something other than `map` (e.g., `map_stats`). The Discord command name is set via `@commands.command(name="map")` and is unaffected.
- **Rate limits**: Seven new commands each making 1–4 API requests. The free Henrik tier allows ~30 req/min. Under normal Discord server usage this is fine, but `!compare` (4 requests) could contribute to rate limit issues if spammed. No throttling is in scope for this plan.
