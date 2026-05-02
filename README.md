# Nuzlocke Soul Link Bot

A comprehensive Discord bot for managing **Soul Link Nuzlocke challenges** with support for 2-4 players. Automatically links Pokemon encounters on the same route, tracks team health, enforces Soul Link rules, and logs all run activities.

## 🎮 Features

### Core Features
✅ **Multi-player Support** - Play with 2-4 players in co-op Nuzlocke runs  
✅ **Automatic Soul Linking** - Pokemon encountered on the same route are instantly linked  
✅ **Team Management** - Add, track, faint, box, unbox, and release Pokemon  
✅ **Route/Encounter Tracking** - Record all Pokemon encounters organized by route  
✅ **Activity Logging** - Complete activity history of every run with export functionality  
✅ **Run Health Monitoring** - Check team status and death counts in real-time  
✅ **Data Preservation** - All run data is preserved even after run completion  


### Soul Link Mechanics
- When 2+ players catch Pokemon on the **same route**, they are **automatically linked**
- If one linked Pokemon **faints**, all partners **faint too**
- If one linked Pokemon is **boxed/released**, all partners are **boxed/released too**
- Supports **2-4 player linking** on a single route
- Optional **type restriction clause** - no two players can have the same type

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- discord.py library
- aiosqlite library
- A Discord bot token

### Setup

1. **Clone/Download the project**
```bash
cd discord-soulink
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Create .env file**
```env
DISCORD_BOT_TOKEN=your_bot_token_here
```

4. **Run the bot**
```bash
python main.py
```

The bot will automatically initialize the database and sync commands.

## 📊 ID System

Each ID type uses a different range for easy identification at a glance:

| ID Type | Range | Example | Usage |
|---------|-------|---------|-------|
| **run_id** | 1, 2, 3... | `/run_status run_id:1` | Identifies which run |
| **player_id** | 1000+ | `/view_team player_id:1000` | Identifies players in runs |
| **route_id** | 2000+ | `/view_route route_id:2000` | Identifies routes within runs |
| **encounter_id** | 3000+ | `/link_pokemon encounter_id_1:3000 encounter_id_2:3001` | Individual Pokemon encounters |
| **member_id** | 4000+ | `/faint_pokemon member_id:4000` | Team member Pokemon |
| **pair_id** | 5000+ | Soul Link pair IDs | Internal linking pairs |

### Example ID Usage
```
Run 1 (run_id: 1)
├── Player Alice (player_id: 1000)
│   ├── Route 1 (route_id: 2000)
│   │   ├── Encounter Pidgeot (encounter_id: 3000)
│   │   └── Team Member Pidgeot (member_id: 4000)
├── Player Bob (player_id: 1001)
│   ├── Route 1 (route_id: 2000)
│   │   ├── Encounter Bulbasaur (encounter_id: 3001)
│   │   └── Team Member Bulbasaur (member_id: 4001)
└── Soul Link Pair (pair_id: 5000) → links 3000 & 3001
```

### ID Reset on Complete Cleanup
When you delete ALL runs from the database, **all IDs reset** to their starting values:
- run_id resets to 1
- player_id resets to 1000
- route_id resets to 2000
- encounter_id resets to 3000
- member_id resets to 4000
- pair_id resets to 5000

This gives you a "fresh start" when starting over completely.

## 📋 Commands

### Quick Start Commands (use `/help`)
```
/create_run - Create a new Nuzlocke run
/join_run - Join an existing run
/record_encounter - Catch and auto-link Pokemon
/faint_pokemon - Mark Pokemon as fainted
/box_pokemon - Box a Pokemon temporarily
/unbox_pokemon - Return boxed Pokemon to team
/view_team - View your complete team
/run_status - Check run status
/run_log - View activity log
```

### All Commands (use `/help_full`)
**Run Management:**
- `/create_run` - Create run with optional clauses
- `/join_run` - Join existing run
- `/list_runs` - List all active runs on server
- `/run_status` - Get detailed run status
- `/end_run` - Complete a run (soft delete)
- `/delete_run` - Permanently delete a run

**Route Management:**
- `/list_routes` - List all routes in a run
- `/record_encounter` - Record Pokemon catch & auto-link
- `/view_route` - View encounters on specific route
- `/view_encounters` - View all routes and encounters

**Team Management:**
- `/add_pokemon` - Manually add Pokemon to team
- `/view_team` - View complete team with all statuses
- `/faint_pokemon` - Mark Pokemon as fainted
- `/box_pokemon` - Box Pokemon (temp removal)
- `/unbox_pokemon` - Unbox Pokemon (return to team)
- `/release_pokemon` - Permanently release Pokemon

**Soul Link:**
- `/link_pokemon` - Manually link encounters by route or ID
- `/soul_link_status` - View all linked pairs
- `/check_run_health` - Check team health for all players
- `/rules_check` - Check Soul Link rule violations

**Logging & Info:**
- `/run_log` - View recent activity log
- `/export_run_log` - Download complete run log as text file
- `/help` - Quick command reference
- `/help_full` - Complete command reference

## 🔗 Auto-Linking System

### How It Works

When you use `/record_encounter`, the bot automatically:

1. **Creates the route** (if it doesn't exist)
2. **Records the encounter** for that player
3. **Adds the Pokemon to your team**
4. **Automatically links** with other encounters on the same route

**Example Flow:**
```
Player 1: /record_encounter run_id:1 route_number:1 player_id:1000 pokemon_name:"Pidgeot"
→ Route 1 created, Pidgeot caught, added to team, waiting for others...

Player 2: /record_encounter run_id:1 route_number:1 player_id:1001 pokemon_name:"Bulbasaur"
→ Route 1 exists, Bulbasaur caught, added to team
→ ✅ AUTO-LINKED: Pidgeot ↔ Bulbasaur (now Soul Link partners!)
```

### Manual Linking (Optional)

If auto-linking doesn't apply to your situation, you can manually link encounters:

```
/link_pokemon run_id:1 route_number:1
(Links all encounters on that route)

OR

/link_pokemon encounter_id_1:3000 encounter_id_2:3001
(Links specific encounters)
```

## 📝 Logging System

Every action in your run is automatically logged for complete history tracking.

### Logged Events
✅ Run created  
✅ Players joined  
✅ Pokemon caught (encounters recorded)  
✅ Pokemon linked as Soul Link partners  
✅ Pokemon fainted/boxed/unboxed/released  
✅ Run completed/deleted  

### View Logs

**In Discord:**
```
/run_log run_id:1
→ Shows last 15 events (customizable with limit:X)

/run_log run_id:1 limit:50
→ Shows last 50 events
```

**Export as File:**
```
/export_run_log run_id:1
→ Downloads complete run history as formatted text file
```

### Log File Location
Logs are stored locally: `run_logs/run_[RUN_ID].json`
- JSON format for structured data
- Preserved even after run deletion
- Can be manually re-accessed

**Example Log Entry:**
```json
{
  "timestamp": "2026-05-02T14:35:45.123456",
  "event_type": "ENCOUNTER_RECORDED",
  "description": "Player Alice caught Pidgeot on Route 1",
  "details": {
    "player": "Alice",
    "pokemon": "Pidgeot",
    "type": "Flying",
    "level": 5,
    "route": 1,
    "encounter_id": 3000
  }
}
```

## 🗑️ Data Management

### Soft Delete (End Run)
```
/end_run run_id:1
```
- Marks run as COMPLETED
- All data is **preserved**
- Run no longer appears in active list
- Can view completed runs with logs

### Hard Delete (Permanently Remove)
```
/delete_run run_id:1 confirm:yes
```

**What Gets Deleted:**
- ✅ Run record
- ✅ All players in run
- ✅ All routes in run
- ✅ All encounters
- ✅ All team members (Pokemon)
- ✅ All Soul Link pairs

**What's Preserved:**
- ✅ Run log file (`run_logs/run_1.json`)
- You can still view the complete activity log after deletion!

**ID Reset:**
If you delete **ALL runs**, IDs reset to starting values:
- Next run will be run_id: 1 (instead of 3)
- Players will start at player_id: 1000 (instead of 1002)
- Routes will start at route_id: 2000 (instead of 2002)
- And so on for all ID types

## 🎯 Soul Link Rules (BETA)

### Type Restriction Clause
When creating a run with `clauses:"type_restriction"`:
- No two players can have the same PRIMARY type active
- Example violation: Player A has Pidgeot (Flying), Player B has Charizard (Flying) ❌

### Check for Violations
```
/rules_check run_id:1 clause:type_restriction
```
Returns:
- ✅ "No type violations found!" - Safe to continue
- ⚠️ "Violations Found" - Lists which types are shared

### Soul Link Equality
- All linked Pokemon must faint together
- All linked Pokemon must be boxed/released together
- This maintains fairness across all players

## 📊 Clauses

Available clauses when creating a run:

| Clause | Description |
|--------|-------------|
| `duplicate` | Skip duplicate Pokemon encounters |
| `shiny` | Can catch any shiny Pokemon encountered |
| `gift` | Gift Pokemon count as route encounters |
| `species` | Only one Pokemon of each species per team |
| `type_restriction` | No shared primary types between teams |
| `nuzlocke` | Classic 3 rules (no clauses, no dupes, all faints) |

**Usage:**
```
/create_run run_name:"My Run" game_name:"Pokemon Red" num_players:2 clauses:"type_restriction,duplicate"
```

## 📈 Monitoring Your Run

### Check Team Status
```
/view_team player_id:1000
```
Shows:
- ✅ Active Pokemon (on team)
- 📦 Boxed Pokemon (temporary removal)
- 💀 Fainted Pokemon (deaths)
- 🚀 Released Pokemon

### Check Overall Health
```
/check_run_health run_id:1
```
Shows for each player:
- Active Pokemon count
- Fainted Pokemon count
- Total deaths
- Team wiped status

### View Activity
```
/run_log run_id:1
```
Shows recent events with timestamps and details

## 🛠️ Technical Details

### Database
- **Type:** SQLite3
- **Foreign Key Constraints:** Enabled (CASCADE DELETE)
- **Tables:** 6 (runs, run_players, routes, encounters, soul_link_pairs, team_members)
- **Automatic Initialization:** On first startup

### Storage
- **Database:** `nuzlocke_data.db`
- **Logs:** `run_logs/` directory (JSON format)
- **Configuration:** `config.py` with clauses and Pokemon types

### Architecture
- **Async/Await:** Full async support with aiosqlite
- **Discord.py:** App commands and embeds
- **Error Handling:** Comprehensive try/catch with user-friendly messages



## 📚 Example Workflow

**Setting up a 2-player Soul Link:**

```
1. /create_run run_name:"Soul Link Adventure" game_name:"Pokemon Emerald" num_players:2 clauses:"type_restriction"
   → Creates Run 1

2. /join_run run_id:1
   → Player 1 joins (player_id: 1000)

3. /join_run run_id:1
   → Player 2 joins (player_id: 1001)

4. /record_encounter run_id:1 route_number:1 player_id:1000 pokemon_name:"Taillow" pokemon_type:"Normal"
   → Route 1 created, Taillow caught, added to team (member_id: 4000)

5. /record_encounter run_id:1 route_number:1 player_id:1001 pokemon_name:"Poochyena" pokemon_type:"Dark"
   → Poochyena caught, added to team (member_id: 4001)
   → ✅ AUTO-LINKED: Taillow ↔ Poochyena

6. /run_log run_id:1
   → See complete activity history

7. /check_run_health run_id:1
   → Both players have 1 active Pokemon

8. /faint_pokemon member_id:4000
   → Taillow faints, Poochyena automatically faints too!

9. /export_run_log run_id:1
   → Download complete run history for records
```

## 🔄 Updates & Changes

### Recent Updates
- ✅ Automatic Soul Linking on same route encounters
- ✅ Unbox Pokemon command
- ✅ Complete activity logging system with export functionality
- ✅ Full database cleanup on run deletion (no orphaned data)
- ✅ ID differentiation system (1000+, 2000+, 3000+, 4000+, 5000+ ranges)
- ✅ ID reset on complete cleanup
- ✅ Foreign key constraint enforcement
- ✅ Split help into `/help` (main) and `/help_full` (all)
- ✅ View team shows all statuses (active, boxed, fainted, released)

### Data Integrity
- Foreign key constraints enabled
- CASCADE DELETE for all related records
- Activity logs preserved indefinitely
- Complete audit trail of all events

## 📄 License

This project is a personal Nuzlocke Soul Link tracker for Discord.

---
**Happy Soul Linking! 🎮✨**
