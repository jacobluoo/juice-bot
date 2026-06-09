# Plan: Valorant Commands Expansion

## Task Description
Implement the four placeholder Valorant commands currently stubbed out in `cogs/valorant.py`: `!rank`, `!history`, `!leaderboard`, and `!agent`. Each currently sends a "coming soon" message. This plan replaces them with full implementations backed by Henrik's Valorant API, following the same patterns already established in the working `!stats` command.

## Objective
Replace all four "coming soon" Valorant command stubs with working implementations that fetch live data from Henrik's API, parse the responses, and present results as polished Discord embeds — consistent in style with `!stats`.

## Assumptions
- **`!leaderboard` scope**: No server-side player registry exists and none is planned. `!leaderboard` will show the global ranked ladder from Henrik's `/valorant/v1/leaderboard/{region}` endpoint, with an optional `region` argument defaulting to `na`. If you actually want a "who in this Discord server ranks highest" feature, flag this — it would require adding a player registration system.
- **`!rank` vs `!stats` differentiation**: `!stats` already shows current rank + RR inline. `!rank` will be a deeper rank-focused view that also shows peak rank (if available from MMR v3 `data.peak`) and a compact per-act progression summary. If MMR v3 does not surface peak/act data, it gracefully omits those fields.
- **Match sample size**: `!history` and `!agent` will fetch the last 10 competitive matches (same as `!stats`) to stay within API rate limits and keep response time fast.
- **Error handling pattern**: All commands follow the existing `try/except aiohttp.ClientError` pattern from `!stats`. No new error-handling abstractions are needed.

## Problem Statement
Four Valorant commands visible in the help list are non-functional stubs. Users who type `!rank`, `!history`, `!leaderboard`, or `!agent` get a "coming soon" wall, reducing the bot's usefulness and making the command list feel incomplete.

## Solution Approach
All four commands follow the same three-step pattern already proven in `!stats`:
1. Parse the `Name#TAG` argument, split on `#`
2. Make one or more async GET requests to Henrik's API using the shared `aiohttp.ClientSession` on `self.session`
3. Parse the JSON response and send a `discord.Embed`

The implementation lives entirely in `cogs/valorant.py` — no new files, no schema changes, no new dependencies.

## Verified API Patterns

| Library/API | Version Checked | Recommended Pattern | Deprecation Warnings |
|-------------|----------------|--------------------|--------------------|
| Henrik Valorant API | v2/v3 (per CLAUDE.md) | Auth via `Authorization` header, not query param. Account lookup via `/valorant/v2/account/{name}/{tag}` to get `puuid` + `region` before calling match/MMR endpoints | `v1` leaderboard endpoint — may require region slug like `na`, `eu`, `ap`, `kr` |
| aiohttp | already pinned in project | `async with self.session.get(url, headers=headers) as resp:` + `await resp.json()` | none |
| discord.py | already pinned | `discord.Embed` with `add_field` | none |

> Note: Context7 does not index Henrik's private API docs. Patterns verified against the existing `!stats` implementation in `cogs/valorant.py` and the CLAUDE.md endpoint reference.

## Relevant Files

- `cogs/valorant.py` — the only file that changes; contains all four stubs to replace
- `CLAUDE.md` — documents the Henrik API base URL, auth header pattern, and the three endpoints already in use

No new files needed.

## Implementation Phases

### Phase 1: Foundation
The shared infrastructure (session, headers, account resolution helper) already exists in `!stats`. Before implementing individual commands, extract a small private helper `_resolve_account(name, tag)` that returns `(puuid, region)` or raises/returns `None` on failure — this avoids copy-pasting the account lookup block into every command.

### Phase 2: Core Implementation
Implement each command in this order (each is independent):

1. **`!rank Name#TAG`** — Calls account + MMR v3. Embed shows: current tier + RR, peak rank (from `data.peak.tier.name` if present), and the `data.by_season` array (last 3 acts) formatted as a compact table. Gracefully omits peak/act fields if the API doesn't return them.

2. **`!history Name#TAG`** — Calls account + last 10 competitive matches. Embed lists each match on its own line: `W/L · Map · Agent · K/D/A · Rounds (X-Y)`. Shows aggregate W/L record in the title.

3. **`!agent Name#TAG`** — Calls account + last 10 matches. Aggregates stats by `character`. Embed shows top 5 agents sorted by games played: agent name, games, win rate, avg K/D/A.

4. **`!leaderboard [region]`** — Calls `/valorant/v1/leaderboard/{region}`. Embed shows top 10 players: rank position, `gameName#tagLine`, tier name, RR, wins. Region defaults to `na`; accepted values: `na`, `eu`, `ap`, `kr`, `latam`, `br`.

### Phase 3: Integration & Polish
- Ensure all four commands use the extracted `_resolve_account` helper (DRY).
- Confirm timeout/error handling mirrors `!stats` exactly.
- Update `CLAUDE.md` command table to change all four statuses from `placeholder` to `done`.

## Team Orchestration

You operate as the team lead and orchestrate the team to execute the plan. You NEVER operate directly on the codebase — you use `Task` and `Task*` tools to deploy team members.

### Team Members

- Builder
  - Name: valorant-builder
  - Role: Implement all four Valorant command stubs in `cogs/valorant.py`
  - Agent Type: general-purpose
  - Resume: true

- Validator
  - Name: valorant-validator
  - Role: Read the finished code, verify it matches acceptance criteria, check for regressions
  - Agent Type: general-purpose
  - Resume: false

### Pipeline Determinism Map

| Node | Determinism | Inputs | Output | Can Change? |
|------|------------|--------|--------|-------------|
| Context7 lookup | NON-DETERMINISTIC | API/library names | Current docs/patterns | External state varies |
| Plan creation | NON-DETERMINISTIC | Prompt + codebase + judgment | Plan document | Already was non-deterministic |
| Builder | DETERMINISTIC | Plan document only | Code changes | **NO — must stay deterministic** |
| Validator | DETERMINISTIC | Code + acceptance criteria | Pass/Fail | **NO — must stay deterministic** |

## Step by Step Tasks

### 1. Extract Account-Resolution Helper
- **Task ID**: extract-account-helper
- **Depends On**: none
- **Assigned To**: valorant-builder
- **Agent Type**: general-purpose
- **Parallel**: false
- Add a private async method `_resolve_account(self, name: str, tag: str) -> dict | None` to the `Valorant` cog in `cogs/valorant.py`
- It should call `GET /valorant/v2/account/{name}/{tag}`, check `status == 200`, and return the `data` dict (which contains `puuid`, `region`, etc.) or `None` on failure
- Do NOT refactor the existing `!stats` command — leave it unchanged for safety

### 2. Implement `!rank`
- **Task ID**: implement-rank
- **Depends On**: extract-account-helper
- **Assigned To**: valorant-builder
- **Agent Type**: general-purpose
- **Parallel**: false
- Replace the `!rank` stub with a full implementation
- Use `_resolve_account` then call `GET /valorant/v3/mmr/{region}/pc/{name}/{tag}`
- Parse `data.current.tier.name`, `data.current.rr`
- If `data.peak` exists, show peak rank name
- If `data.by_season` exists, show last 3 acts (act name, final rank) as compact field lines
- Send a `discord.Embed` with `color=discord.Color.red()`
- Wrap in `try/except aiohttp.ClientError` matching the `!stats` pattern

### 3. Implement `!history`
- **Task ID**: implement-history
- **Depends On**: extract-account-helper
- **Assigned To**: valorant-builder
- **Agent Type**: general-purpose
- **Parallel**: false
- Replace the `!history` stub
- Use `_resolve_account` then call `GET /valorant/v3/matches/{region}/{name}/{tag}?mode=competitive&size=10`
- For each match, find the player by `puuid`, read: `character`, `stats.kills/deaths/assists`, team win status, `metadata.map`
- Also read rounds: `teams.{team}.rounds_won` and the opposing team's rounds for score display
- Embed title: `Match History — {name}#{tag} ({W}W/{L}L)`
- One line per match: `W/L · Map · Agent · K/D/A · Rounds X–Y`

### 4. Implement `!agent`
- **Task ID**: implement-agent
- **Depends On**: extract-account-helper
- **Assigned To**: valorant-builder
- **Agent Type**: general-purpose
- **Parallel**: false
- Replace the `!agent` stub
- Fetch last 10 matches via same endpoint as `!history`
- Aggregate by `character`: count games, wins, kills, deaths, assists
- Sort agents by games played descending, show top 5
- For each agent: name, games played, win%, avg K/D/A (rounded to 1 decimal)
- Use `discord.Embed` with a field per agent (inline layout for compact display)

### 5. Implement `!leaderboard`
- **Task ID**: implement-leaderboard
- **Depends On**: none
- **Assigned To**: valorant-builder
- **Agent Type**: general-purpose
- **Parallel**: true
- Replace the `!leaderboard` stub. Signature: `async def leaderboard(self, ctx, region: str = "na")`
- Validate `region` against the allowed set: `{"na", "eu", "ap", "kr", "latam", "br"}` — send usage message if invalid
- Call `GET {HENRIK_BASE}/valorant/v1/leaderboard/{region}` with auth header
- Parse the response `data` array; take first 10 entries
- Each entry has `leaderboardRank`, `gameName`, `tagLine`, `rankedRating`, `numberOfWins`, `competitiveTier` (integer tier ID — map to name using the existing tier name from MMR data, or just display RR and wins if tier name resolution is complex)
- Embed title: `Valorant Leaderboard — {region.upper()}`
- Wrap in `try/except aiohttp.ClientError`

### 6. Update CLAUDE.md
- **Task ID**: update-docs
- **Depends On**: implement-rank, implement-history, implement-agent, implement-leaderboard
- **Assigned To**: valorant-builder
- **Agent Type**: general-purpose
- **Parallel**: false
- Update the command table in `CLAUDE.md`: change `!rank`, `!history`, `!leaderboard`, `!agent` status from `placeholder` to `done`

### 7. Validate All Changes
- **Task ID**: validate-all
- **Depends On**: update-docs
- **Assigned To**: valorant-validator
- **Agent Type**: general-purpose
- **Parallel**: false
- Read `cogs/valorant.py` in full and verify:
  - All four stubs are replaced with real implementations
  - `_resolve_account` helper exists and is used by at least `!rank`, `!history`, `!agent`
  - All four commands wrap API calls in `try/except aiohttp.ClientError`
  - No existing `!stats` logic was modified
  - `!leaderboard` validates region input
  - `!history` shows agent name per match
  - `!agent` aggregates and shows per-agent stats
- Confirm CLAUDE.md command table is updated
- Report any acceptance criteria failures

## Acceptance Criteria

1. `!rank Name#TAG` returns a Discord embed with at minimum: current rank name and RR. Does not send "coming soon".
2. `!history Name#TAG` returns an embed listing individual matches with map, agent, K/D/A, and W/L. Does not send "coming soon".
3. `!agent Name#TAG` returns an embed showing per-agent aggregated stats (games, win rate, avg KDA) for the player's last matches. Does not send "coming soon".
4. `!leaderboard` (no args) returns an embed listing top 10 players for `na` by default. `!leaderboard eu` works for the `eu` region.
5. Invalid region (e.g., `!leaderboard xyz`) sends an informative error message, not a traceback.
6. All four commands handle API errors gracefully (network failure → user-facing error message, not uncaught exception).
7. Existing `!stats` command behavior is unchanged.
8. `_resolve_account` private helper is present and reused — no copy-pasted account-resolution blocks across commands.
9. CLAUDE.md command table shows all four commands as `done`.

## Validation Commands

```bash
# Static check — no syntax errors
python -m py_compile cogs/valorant.py

# Confirm stubs are gone
grep -n "coming soon" cogs/valorant.py
# Expected: no matches

# Confirm helper exists
grep -n "_resolve_account" cogs/valorant.py
# Expected: definition line + at least 3 call sites

# Confirm leaderboard region guard exists
grep -n "leaderboard" cogs/valorant.py
# Expected: function def + region validation logic visible

# Confirm CLAUDE.md updated
grep "placeholder" CLAUDE.md
# Expected: no matches for rank/history/leaderboard/agent rows
```

## Notes

- **Henrik API rate limits**: The free tier allows ~30 req/min. Each command that takes `Name#TAG` makes 2 requests (account + MMR/matches). This is fine for a small Discord server but could become an issue under load. No rate-limit handling is in scope for this plan.
- **Tier integer → name mapping for leaderboard**: Henrik's leaderboard endpoint returns `competitiveTier` as an integer (0–27). If resolving to a name string proves complex (requires a separate tiers endpoint), the leaderboard embed can skip the tier name and show RR + wins only — the rank position is the primary value anyway.
- **`!stats` not refactored**: The existing `!stats` command is left as-is even though it duplicates the account-resolution logic. The helper is added for the four new commands only. Refactoring `!stats` to use it is a safe follow-up once the new commands are validated.
- **aiosqlite / db.py**: No database changes. These commands are stateless.
