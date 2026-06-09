# Juice Discord Bot

A Discord bot built with discord.py using the Cogs architecture. Currently focused on Valorant stats via Henrik's API, with gambling games planned.

## Project Structure

```
juice/
├── bot.py              — entry point, loads cogs, starts bot
├── .env                — secrets (never commit)
├── .gitignore
├── CLAUDE.md
└── cogs/
    ├── general.py      — !hello
    ├── valorant.py     — Valorant stat commands
    ├── gambling.py     — !balance, !daily
    ├── blackjack.py    — !blackjack
    └── poker.py        — !poker (1v1 vs bot, Texas Hold'em)
```

## Tech Stack

- Python 3.14
- discord.py (commands.Bot with Cogs)
- aiohttp — async HTTP requests to Henrik's API
- python-dotenv — loads .env secrets

## Environment Variables

Stored in `.env`, never hardcoded:

```
DISCORD_TOKEN=...
HENRIK_API_KEY=...
```

## Henrik Valorant API

- Base URL: `https://api.henrikdev.xyz`
- Docs: `https://docs.henrikdev.xyz/valorant/api-reference`
- Auth header: `Authorization: <HENRIK_API_KEY>`
- Endpoints in use:
  - Account: `GET /valorant/v2/account/{name}/{tag}`
  - MMR/Rank: `GET /valorant/v3/mmr/{region}/pc/{name}/{tag}`
  - Match history: `GET /valorant/v3/matches/{region}/{name}/{tag}?mode=competitive&size=10`
- MMR v3 response fields: `data.current.tier.name`, `data.current.rr`

## Commands

| Command | Cog | Status |
|---|---|---|
| `!hello` | general | done |
| `!stats Name#TAG` | valorant | done |
| `!rank Name#TAG` | valorant | placeholder |
| `!history Name#TAG` | valorant | placeholder |
| `!leaderboard` | valorant | placeholder |
| `!agent Name#TAG` | valorant | placeholder |
| `!server [region]` | valorant | done |
| `!rr Name#TAG` | valorant | done |
| `!last Name#TAG` | valorant | done |
| `!compare Name1#TAG1 Name2#TAG2` | valorant | done |
| `!crosshair <code>` | valorant | done |
| `!news` | valorant | done |
| `!map Name#TAG` | valorant | done |
| `!balance` / `!bal` | gambling | done |
| `!daily` | gambling | done |
| `!blackjack <bet>` | blackjack | done |
| `!poker <bet>` | poker | done |

## Adding a New Cog

1. Create `cogs/mycog.py` with a class extending `commands.Cog` and a `setup(bot)` function
2. Add `"cogs.mycog"` to the `EXTENSIONS` list in `bot.py`

## Running the Bot

```
python bot.py
```
.
## Development Notes

- All commands use `commands.Bot` prefix `!`
- Placeholder commands send a "coming soon" message — fill in logic when ready
- `!stats` win rate troll message triggers below 50% win rate
- Match count in embed labels is dynamic based on how many matches the API returns (not hardcoded)
- Always wrap Henrik API calls in `try/except aiohttp.ClientError` to handle network failures gracefully
