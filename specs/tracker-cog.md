# Plan: Project Progress Tracker Cog

## Task Description
Add a new `cogs/tracker.py` cog to the existing discord.py bot that tracks project progress using SQLite persistence. The cog introduces two new database tables (`projects` and `updates`) managed through the shared `Database` class in `db.py`. It exposes four commands: `!project create <name>` to register a project, `!update <project-name> <message>` to log a progress entry attributed to the calling user, `!log <project-name>` to display the last 5 updates as a Discord embed, and `!projects` to list all projects in the server.

## Objective
Implement `cogs/tracker.py` with full SQLite-backed project tracking, extend `db.py` with tracker-specific tables and query methods, register the cog in `bot.py`, and verify all four commands produce correct Discord embed responses.

## Assumptions
- **Guild scoping**: Projects are scoped by `guild_id` so each Discord server maintains its own independent project list. Evidence: every other DB table (`balances`, `jobs`) uses `(user_id, guild_id)` or `guild_id` as the primary scope key. Flag this if you want a global shared project list across all servers.
- **Database architecture**: Tracker tables and methods extend the shared `db.py` `Database` class rather than opening a separate `aiosqlite` connection inside the cog. Evidence: all five existing cogs call `self.bot.db.*` exclusively; the connection lifecycle is managed centrally in `bot.py` via `bot.db = Database()`. Flag this if you want `tracker.py` to be fully self-contained with its own DB file.
- **Project name parsing**: For `!update <project-name> <message>`, the project name is a single positional token and the remainder is the message. `!project create` accepts multi-word names via `*, name: str`. Flag this if you need multi-word project names in `!update`/`!log`.
- **User attribution**: Updates are attributed using `ctx.author.display_name` (server display name). Consistent with how gambling/jobs cogs format user-facing messages.

## Problem Statement
The bot has no way to track ongoing projects or record structured progress updates. Users who want project coordination must rely on unstructured Discord messages with no history, searchability, or quick-access log.

## Solution Approach
Extend the existing `Database` class in `db.py` with two new tables (`projects` and `updates`) and five new async methods. Create `cogs/tracker.py` following the exact same pattern as existing cogs: `Cog` subclass with `self.bot`, command methods using `@commands.group()` for `!project` subcommands and `@commands.command()` for standalone commands, and `discord.Embed` for all responses. Register the new cog in `bot.py`'s `EXTENSIONS` list. No new dependencies are required — `aiosqlite` is already installed.

## Verified API Patterns

| Library/API | Version Checked | Recommended Pattern | Deprecation Warnings |
|-------------|----------------|--------------------|--------------------|
| aiosqlite | 0.22.1 | `async with self._db.execute(sql, params) as cursor:` with `row_factory = aiosqlite.Row`; use `cursor.lastrowid` for last inserted row ID after INSERT; `await self._db.commit()` after writes | None |
| discord.py | 2.7.1 | `@commands.group(invoke_without_command=True)` for parent command; subcommands via `@<group>.command(name="create")`; `discord.Embed` with `.add_field()` and `.set_footer()` — all confirmed current | None affecting commands extension |

## Relevant Files
- `bot.py` — add `"cogs.tracker"` to the `EXTENSIONS` list
- `db.py` — add `projects` and `updates` table creation to `setup()` and five new async methods
- `cogs/jobs.py` — reference for embed formatting patterns, `@commands.command()` structure, and `datetime`/timezone usage
- `cogs/gambling.py` — reference for `self.bot.db` access pattern

### New Files
- `cogs/tracker.py` — the new cog implementing all four commands

## Implementation Phases

### Phase 1: Foundation
Extend `db.py` with two new tables created in `setup()` and five tracker-specific async methods. This is prerequisite work — no cog command can execute without it.

### Phase 2: Core Implementation
Write `cogs/tracker.py` with all four commands producing embeds. Register the cog in `bot.py`.

### Phase 3: Integration & Polish
Validate syntax, verify cog registration, confirm embed usage throughout, confirm error handling for unknown project names and duplicate creation attempts.

## Team Orchestration

- You operate as the team lead and orchestrate the team to execute the plan.
- You're responsible for deploying the right team members with the right context to execute the plan.
- IMPORTANT: You NEVER operate directly on the codebase. You use `Task` and `Task*` tools to deploy team members to do the building, validating, testing, deploying, and other tasks.
  - This is critical. Your job is to act as a high level director of the team, not a builder.
  - Your role is to validate all work is going well and make sure the team is on track to complete the plan.
  - You'll orchestrate this by using the Task* Tools to manage coordination between the team members.
  - Communication is paramount. You'll use the Task* Tools to communicate with the team members and ensure they're on track to complete the plan.
- Take note of the session id of each team member. This is how you'll reference them.

### Team Members

- Builder
  - Name: builder-tracker
  - Role: Implement all DB extensions in `db.py` and write the complete `cogs/tracker.py` cog, then register it in `bot.py`
  - Agent Type: general-purpose
  - Resume: true

- Validator
  - Name: validator-tracker
  - Role: Verify all acceptance criteria are met — file exists, syntax is clean, cog is registered, all DB methods are present, embeds used throughout, error cases handled
  - Agent Type: general-purpose
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

- IMPORTANT: Execute every step in order, top to bottom. Each task maps directly to a `TaskCreate` call.
- Before you start, run `TaskCreate` to create the initial task list that all team members can see and execute.

### 1. Extend Database Class
- **Task ID**: extend-database
- **Depends On**: none
- **Assigned To**: builder-tracker
- **Agent Type**: general-purpose
- **Parallel**: false
- Add `CREATE TABLE IF NOT EXISTS projects` to `Database.setup()` in `db.py` with schema:
  ```sql
  CREATE TABLE IF NOT EXISTS projects (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      guild_id    INTEGER NOT NULL,
      name        TEXT NOT NULL,
      created_by  TEXT NOT NULL,
      created_at  TEXT NOT NULL,
      UNIQUE(guild_id, name)
  )
  ```
- Add `CREATE TABLE IF NOT EXISTS updates` with schema:
  ```sql
  CREATE TABLE IF NOT EXISTS updates (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      project_id  INTEGER NOT NULL REFERENCES projects(id),
      user        TEXT NOT NULL,
      message     TEXT NOT NULL,
      timestamp   TEXT NOT NULL
  )
  ```
- Add `async def create_project(self, guild_id: int, name: str, created_by: str) -> int | None` — use `INSERT OR IGNORE` and return `cursor.lastrowid` or `None` if row already existed (check by fetching after insert)
- Add `async def get_project(self, guild_id: int, name: str)` — SELECT row by `(guild_id, name)`, return row or `None`
- Add `async def list_projects(self, guild_id: int) -> list` — SELECT all projects for guild, `ORDER BY created_at ASC`
- Add `async def add_update(self, project_id: int, user: str, message: str) -> None` — INSERT into updates, compute timestamp as `datetime.now(timezone.utc).isoformat()`; add `from datetime import datetime, timezone` import to db.py if not present
- Add `async def get_recent_updates(self, project_id: int, limit: int = 5) -> list` — SELECT last N updates `ORDER BY timestamp DESC LIMIT ?`

### 2. Implement Tracker Cog
- **Task ID**: implement-cog
- **Depends On**: extend-database
- **Assigned To**: builder-tracker
- **Agent Type**: general-purpose
- **Parallel**: false
- Create `cogs/tracker.py` with imports: `discord`, `commands`, `datetime`, `timezone`
- Class `Tracker(commands.Cog)` with `__init__(self, bot)` storing `self.bot = bot`
- `@commands.group(name="project", invoke_without_command=True)` — sends a usage hint embed (`discord.Color.blue()`) showing available subcommands when called bare
- `@project.command(name="create")` with `ctx, *, name: str` — calls `self.bot.db.create_project(ctx.guild.id, name, ctx.author.display_name)`, sends green success embed showing project name and creator, or red error embed if `None` returned (duplicate name)
- `@commands.command(name="update")` with `ctx, project_name: str, *, message: str` — calls `get_project`, sends red error embed if not found, otherwise calls `add_update` and sends green success embed with project name and logged message
- `@commands.command(name="log")` with `ctx, *, project_name: str` — calls `get_project` (error embed if not found), calls `get_recent_updates`, builds blue embed titled `"Project Log: {name}"` with each update as `embed.add_field(name=f"{row['user']} — {formatted_timestamp}", value=row['message'], inline=False)`; if no updates exist add a single field saying "No updates yet"
- Timestamp formatting for `!log`: parse ISO string with `datetime.fromisoformat(ts)` and format as `ts.strftime("%Y-%m-%d %H:%M UTC")`
- `@commands.command(name="projects")` — calls `list_projects(ctx.guild.id)`, builds blue embed titled `"Projects"` listing each as `embed.add_field(name=f"{i+1}. {row['name']}", value=f"Created by {row['created_by']} on {row['created_at'][:10]}", inline=False)`; if empty, description = "No projects yet. Use `!project create <name>` to get started."
- `async def setup(bot): await bot.add_cog(Tracker(bot))` at module bottom

### 3. Register Cog in bot.py
- **Task ID**: register-cog
- **Depends On**: implement-cog
- **Assigned To**: builder-tracker
- **Agent Type**: general-purpose
- **Parallel**: false
- Add `"cogs.tracker"` to the `EXTENSIONS` list in `bot.py` (append after `"cogs.jobs"`)

### 4. Validate Implementation
- **Task ID**: validate-all
- **Depends On**: extend-database, implement-cog, register-cog
- **Assigned To**: validator-tracker
- **Agent Type**: general-purpose
- **Parallel**: false
- Run all validation commands listed in the Validation Commands section
- Verify each acceptance criterion is met, reporting any failures with specific details

## Acceptance Criteria
1. `cogs/tracker.py` exists and follows standard cog boilerplate (`Tracker(commands.Cog)`, `async def setup(bot)`)
2. `db.py` contains `CREATE TABLE IF NOT EXISTS projects` and `CREATE TABLE IF NOT EXISTS updates` inside `setup()`
3. `db.py` exposes all five tracker methods: `create_project`, `get_project`, `list_projects`, `add_update`, `get_recent_updates`
4. `!project create <name>` produces a green success embed with project name and creator; duplicate names produce a red error embed
5. `!update <project-name> <message>` produces a green success embed; unknown project name produces a red error embed
6. `!log <project-name>` produces a blue embed with up to 5 most recent updates showing username, message, and formatted timestamp; unknown project name produces a red error embed
7. `!projects` produces a blue embed listing all server projects with name, creator, and creation date; empty list produces a descriptive "no projects yet" message
8. All responses use `discord.Embed` — no bare string `ctx.send()` calls in tracker.py
9. `"cogs.tracker"` appears in `EXTENSIONS` in `bot.py`
10. Both `cogs/tracker.py` and `db.py` pass Python AST syntax check with exit code 0

## Validation Commands
```bash
# Syntax check both files
python -c "import ast; ast.parse(open('cogs/tracker.py').read()); print('tracker.py syntax OK')"
python -c "import ast; ast.parse(open('db.py').read()); print('db.py syntax OK')"

# Verify tables in db.py
python -c "
content = open('db.py').read()
assert 'CREATE TABLE IF NOT EXISTS projects' in content, 'FAIL: Missing projects table'
assert 'CREATE TABLE IF NOT EXISTS updates' in content, 'FAIL: Missing updates table'
assert 'create_project' in content, 'FAIL: Missing create_project method'
assert 'get_project' in content, 'FAIL: Missing get_project method'
assert 'list_projects' in content, 'FAIL: Missing list_projects method'
assert 'add_update' in content, 'FAIL: Missing add_update method'
assert 'get_recent_updates' in content, 'FAIL: Missing get_recent_updates method'
print('db.py method checks passed')
"

# Verify cog structure in tracker.py
python -c "
content = open('cogs/tracker.py').read()
assert 'class Tracker' in content, 'FAIL: Missing Tracker class'
assert 'commands.Cog' in content, 'FAIL: Not a Cog subclass'
assert 'discord.Embed' in content, 'FAIL: Missing embed usage'
assert 'async def setup' in content, 'FAIL: Missing setup function'
assert 'project' in content, 'FAIL: Missing project group'
assert 'create' in content, 'FAIL: Missing create subcommand'
print('tracker.py structure checks passed')
"

# Verify bot.py registration
python -c "
content = open('bot.py').read()
assert 'cogs.tracker' in content, 'FAIL: Cog not registered in EXTENSIONS'
print('bot.py registration OK')
"
```

## Notes
- The `!update` command name does not conflict with any discord.py internals — confirmed safe.
- Project names with spaces: `!project create My Project` works via `*, name: str` but `!update "My Project" msg` won't parse quoted args by default. Single-word project names are the safe baseline; document this in the `!project create` success embed footer.
- Timestamps stored as ISO 8601 strings (`datetime.now(timezone.utc).isoformat()`) — consistent with `last_work` in `db.py`.
- No new pip dependencies required — `aiosqlite` is already installed and in use.
- If `ctx.guild` is `None` (DM context), `ctx.guild.id` will raise `AttributeError`. Add a `if not ctx.guild: return` guard in each command or rely on existing bot configuration that restricts to guild channels.
