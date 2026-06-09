# Juice Bot

A Discord bot with Valorant stats, an economy system, and gambling games.

## Features

### Valorant
Look up player stats via the Henrik Dev API.

| Command | Description |
|---|---|
| `!stats Name#TAG` | Win rate, KDA, and performance across recent matches |
| `!rr Name#TAG` | Current rank and RR |
| `!last Name#TAG` | Stats from the most recent competitive match |
| `!compare Name1#TAG1 Name2#TAG2` | Head-to-head stat comparison |
| `!map Name#TAG` | Best and worst maps |
| `!server [region]` | Server status |
| `!crosshair <code>` | Render a crosshair from its share code |
| `!news` | Latest Valorant news |

### Economy
Earn and spend coins across commands.

| Command | Description |
|---|---|
| `!balance` / `!bal` | Check your coin balance |
| `!daily` | Claim daily coins |

### Jobs
Get a job, work shifts, earn XP, and level up for higher pay.

| Command | Description |
|---|---|
| `!jobs` | List all available jobs |
| `!apply <job>` | Start working a job |
| `!work` | Complete a shift (4-hour cooldown) |
| `!job` | View your current job, level, and XP |
| `!levelup` | Spend XP and coins to level up |
| `!quit` | Quit your current job |

### Gambling
| Command | Description |
|---|---|
| `!blackjack <bet>` | Play blackjack against the dealer |
| `!poker <bet>` | 1v1 Texas Hold'em against the bot |

### Tracker
Track Valorant players and monitor rank changes.

## Setup

1. **Install dependencies**
   ```
   pip install discord.py aiohttp python-dotenv
   ```

2. **Create a `.env` file**
   ```
   DISCORD_TOKEN=your_discord_bot_token
   HENRIK_API_KEY=your_henrik_api_key
   ```

3. **Run the bot**
   ```
   python bot.py
   ```

## Stack

- Python 3.14
- [discord.py](https://discordpy.readthedocs.io/) — bot framework
- [aiohttp](https://docs.aiohttp.org/) — async HTTP
- [python-dotenv](https://pypi.org/project/python-dotenv/) — env vars
- SQLite — economy and tracker persistence
- [Henrik Dev API](https://docs.henrikdev.xyz/valorant/api-reference) — Valorant data
