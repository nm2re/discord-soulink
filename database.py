import aiosqlite
import json
from config import DATABASE_PATH
from typing import Optional, List

async def init_db():
    """Initialize the database with all required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Enable foreign key constraints (required for CASCADE DELETE to work in SQLite)
        await db.execute("PRAGMA foreign_keys = ON")

        # Nuzlocke Runs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                run_name TEXT NOT NULL,
                game_name TEXT NOT NULL,
                num_players INTEGER NOT NULL CHECK(num_players BETWEEN 1 AND 4),
                status TEXT DEFAULT 'ACTIVE',
                clauses TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, run_name)
            )
        """)

        # Run Players table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS run_players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                discord_name TEXT NOT NULL,
                team_slot INTEGER NOT NULL,
                deaths INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                UNIQUE(run_id, user_id)
            )
        """)

        # Routes table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                route_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                route_number INTEGER NOT NULL,
                route_name TEXT,
                status TEXT DEFAULT 'AVAILABLE',
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                UNIQUE(run_id, route_number)
            )
        """)

        # Encounters table (tracks caught Pokemon for each player on each route)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS encounters (
                encounter_id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                pokemon_name TEXT,
                pokemon_type TEXT,
                status TEXT DEFAULT 'ACTIVE',
                caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES run_players(player_id) ON DELETE CASCADE,
                UNIQUE(route_id, player_id)
            )
        """)

        # Soul Link Pairs table (links encounters between players)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS soul_link_pairs (
                pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
                encounter_id_1 INTEGER NOT NULL,
                encounter_id_2 INTEGER NOT NULL,
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (encounter_id_1) REFERENCES encounters(encounter_id) ON DELETE CASCADE,
                FOREIGN KEY (encounter_id_2) REFERENCES encounters(encounter_id) ON DELETE CASCADE,
                UNIQUE(encounter_id_1, encounter_id_2)
            )
        """)

        # Team Members table (all Pokemon on a player's team)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                pokemon_name TEXT NOT NULL,
                pokemon_type TEXT,
                level INTEGER DEFAULT 1,
                status TEXT DEFAULT 'ACTIVE',
                is_encountered INTEGER DEFAULT 0,
                is_starter INTEGER DEFAULT 0,
                route_encountered INTEGER,
                linked_member_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES run_players(player_id) ON DELETE CASCADE
            )
        """)

        await db.commit()

        # Set up ID sequences with different starting values for easy differentiation
        # This helps identify what type of ID it is at a glance
        # Run IDs: 1, 2, 3...
        # Player IDs: 1000, 1001, 1002... (P prefix range)
        # Route IDs: 2000, 2001, 2002... (R prefix range)
        # Encounter IDs: 3000, 3001, 3002... (E prefix range)
        # Team Member IDs: 4000, 4001, 4002... (T prefix range)
        # Soul Link Pair IDs: 5000, 5001, 5002... (S prefix range)

        # Initialize sequences if they don't exist
        await db.execute("""
            INSERT OR IGNORE INTO sqlite_sequence (name, seq) 
            VALUES ('runs', 0)
        """)
        await db.execute("""
            INSERT OR IGNORE INTO sqlite_sequence (name, seq) 
            VALUES ('run_players', 999)
        """)
        await db.execute("""
            INSERT OR IGNORE INTO sqlite_sequence (name, seq) 
            VALUES ('routes', 1999)
        """)
        await db.execute("""
            INSERT OR IGNORE INTO sqlite_sequence (name, seq) 
            VALUES ('encounters', 2999)
        """)
        await db.execute("""
            INSERT OR IGNORE INTO sqlite_sequence (name, seq) 
            VALUES ('team_members', 3999)
        """)
        await db.execute("""
            INSERT OR IGNORE INTO sqlite_sequence (name, seq) 
            VALUES ('soul_link_pairs', 4999)
        """)

        await db.commit()


async def get_run(run_id: int):
    """Fetch a specific run."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)) as cursor:
            row = await cursor.fetchone()
            return row


async def get_run_by_name(guild_id: int, run_name: str):
    """Fetch a run by guild and name."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT * FROM runs WHERE guild_id = ? AND run_name = ?",
            (guild_id, run_name)
        ) as cursor:
            row = await cursor.fetchone()
            return row


async def get_runs_by_guild(guild_id: int, status: str = "ACTIVE"):
    """Fetch all active runs in a guild."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM runs WHERE guild_id = ? AND status = ? ORDER BY created_at DESC",
            (guild_id, status)
        ) as cursor:
            return await cursor.fetchall()


async def get_players_in_run(run_id: int):
    """Fetch all players in a run."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM run_players WHERE run_id = ? ORDER BY team_slot",
            (run_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_routes_in_run(run_id: int):
    """Fetch all routes in a run."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM routes WHERE run_id = ? ORDER BY route_number",
            (run_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_encounters_for_route(route_id: int):
    """Fetch all encounters on a route."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT e.*, p.discord_name FROM encounters e
               JOIN run_players p ON e.player_id = p.player_id
               WHERE e.route_id = ?""",
            (route_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_player_team(player_id: int):
    """Fetch a player's current team."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM team_members WHERE player_id = ? AND status = 'ACTIVE' ORDER BY member_id",
            (player_id,)
        ) as cursor:
            return await cursor.fetchall()


# CREATE/INSERT FUNCTIONS

async def create_run(guild_id: int, channel_id: int, run_name: str, game_name: str,
                     num_players: int, clauses: List[str] = None):
    """Create a new Nuzlocke run."""
    if num_players < 1 or num_players > 4:
        raise ValueError("Number of players must be between 1 and 4")

    clauses_str = ",".join(clauses) if clauses else ""

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO runs (guild_id, channel_id, run_name, game_name, num_players, clauses)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (guild_id, channel_id, run_name, game_name, num_players, clauses_str)
        )
        await db.commit()

        # Get the created run ID
        async with db.execute(
            "SELECT last_insert_rowid() as run_id"
        ) as cursor:
            result = await cursor.fetchone()
            return result[0]


async def add_player_to_run(run_id: int, user_id: int, discord_name: str, team_slot: int):
    """Add a player to a run."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                """INSERT INTO run_players (run_id, user_id, discord_name, team_slot)
                   VALUES (?, ?, ?, ?)""",
                (run_id, user_id, discord_name, team_slot)
            )
            await db.commit()

            async with db.execute(
                "SELECT last_insert_rowid() as player_id"
            ) as cursor:
                result = await cursor.fetchone()
                return result[0]
        except aiosqlite.IntegrityError:
            raise ValueError(f"Player already in this run")


async def add_route_to_run(run_id: int, route_number: int, route_name: str = ""):
    """Add a route to a run."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO routes (run_id, route_number, route_name)
               VALUES (?, ?, ?)""",
            (run_id, route_number, route_name)
        )
        await db.commit()

        async with db.execute(
            "SELECT last_insert_rowid() as route_id"
        ) as cursor:
            result = await cursor.fetchone()
            return result[0]


async def add_encounter(route_id: int, player_id: int, pokemon_name: str, pokemon_type: str = ""):
    """Record a Pokemon encounter on a route."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check if player already has encounter on this route
        async with db.execute(
            "SELECT encounter_id FROM encounters WHERE route_id = ? AND player_id = ?",
            (route_id, player_id)
        ) as cursor:
            if await cursor.fetchone():
                raise ValueError("Player already has an encounter on this route")

        await db.execute(
            """INSERT INTO encounters (route_id, player_id, pokemon_name, pokemon_type)
               VALUES (?, ?, ?, ?)""",
            (route_id, player_id, pokemon_name, pokemon_type)
        )
        await db.commit()

        async with db.execute(
            "SELECT last_insert_rowid() as encounter_id"
        ) as cursor:
            result = await cursor.fetchone()
            return result[0]


async def link_pokemon_pair(encounter_id_1: int, encounter_id_2: int):
    """Link two Pokemon encounters as Soul Link partners."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check if already linked (in either direction)
        async with db.execute(
            """SELECT pair_id FROM soul_link_pairs 
               WHERE (encounter_id_1 = ? AND encounter_id_2 = ?) 
               OR (encounter_id_1 = ? AND encounter_id_2 = ?)""",
            (encounter_id_1, encounter_id_2, encounter_id_2, encounter_id_1)
        ) as cursor:
            if await cursor.fetchone():
                # Already linked, skip
                return
        
        # Not linked yet, create the link
        await db.execute(
            """INSERT INTO soul_link_pairs (encounter_id_1, encounter_id_2)
               VALUES (?, ?)""",
            (encounter_id_1, encounter_id_2)
        )
        await db.commit()


async def add_team_member(player_id: int, pokemon_name: str, pokemon_type: str = "",
                           level: int = 1, is_starter: bool = False,
                           route_encountered: Optional[int] = None):
     """Add a Pokemon to a player's team."""
     async with aiosqlite.connect(DATABASE_PATH) as db:
         await db.execute(
             """INSERT INTO team_members (player_id, pokemon_name, pokemon_type, level, 
                                         is_starter, route_encountered, is_encountered)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
             (player_id, pokemon_name, pokemon_type, level, 1 if is_starter else 0,
              route_encountered, 1 if route_encountered else 0)
         )
         await db.commit()

         async with db.execute(
             "SELECT last_insert_rowid() as member_id"
         ) as cursor:
             result = await cursor.fetchone()
             member_id = result[0]

         # If this Pokemon came from a linked encounter, find and link the partner team members
         if route_encountered:
             # Get the route_id for this route number and run
             async with db.execute(
                 """SELECT route_id FROM routes WHERE route_number = ? 
                    AND run_id = (SELECT run_id FROM run_players WHERE player_id = ?)""",
                 (route_encountered, player_id)
             ) as cursor:
                 route_result = await cursor.fetchone()
                 if route_result:
                     route_id = route_result[0]

                     # Get the encounter for THIS player on this route
                     async with db.execute(
                         "SELECT encounter_id FROM encounters WHERE route_id = ? AND player_id = ?",
                         (route_id, player_id)
                     ) as cursor:
                         my_encounter = await cursor.fetchone()

                     if my_encounter:
                         my_enc_id = my_encounter[0]

                         # Find all encounters linked to THIS encounter (2, 3, or 4 players)
                         async with db.execute(
                             """SELECT DISTINCT encounter_id FROM (
                                 SELECT encounter_id_1 as encounter_id FROM soul_link_pairs WHERE encounter_id_2 = ?
                                 UNION
                                 SELECT encounter_id_2 as encounter_id FROM soul_link_pairs WHERE encounter_id_1 = ?
                                 UNION
                                 SELECT ? as encounter_id
                             )""",
                             (my_enc_id, my_enc_id, my_enc_id)
                         ) as cursor:
                             linked_encounters = await cursor.fetchall()

                         # Get all team members from the linked encounters (excluding this player)
                         linked_member_ids = []
                         for (enc_id,) in linked_encounters:
                             async with db.execute(
                                 """SELECT tm.member_id FROM team_members tm
                                    JOIN encounters e ON e.encounter_id = ?
                                    WHERE tm.player_id = e.player_id AND tm.status = 'ACTIVE'
                                    AND tm.player_id != ? AND tm.pokemon_name = e.pokemon_name""",
                                 (enc_id, player_id)
                             ) as cursor:
                                 result = await cursor.fetchone()
                                 if result:
                                     linked_member_ids.append(result[0])

                         # Link this team member to all linked partners
                         for linked_id in linked_member_ids:
                             await db.execute(
                                 "UPDATE team_members SET linked_member_id = ? WHERE member_id = ?",
                                 (linked_id, member_id)
                             )

             await db.commit()

         return member_id


async def faints_pokemon(member_id: int):
     """Mark a Pokemon as fainted."""
     # Use the all_linked version to handle 2-4 player modes
     await faint_all_linked_pokemon(member_id)


async def box_pokemon(member_id: int):
     """Mark a Pokemon as boxed."""
     # Use the all_linked version to handle 2-4 player modes
     await box_all_linked_pokemon(member_id)


async def unbox_pokemon(member_id: int):
     """Unbox a Pokemon (return to ACTIVE)."""
     async with aiosqlite.connect(DATABASE_PATH) as db:
         # Get the member and their route
         async with db.execute(
             "SELECT member_id, route_encountered FROM team_members WHERE member_id = ?",
             (member_id,)
         ) as cursor:
             row = await cursor.fetchone()
             if not row:
                 return

         # Unbox the member
         await db.execute(
             "UPDATE team_members SET status = 'ACTIVE' WHERE member_id = ?",
             (member_id,)
         )
         await db.commit()

         # For 2-player mode: Get linked_member_id (if any)
         async with db.execute(
             "SELECT linked_member_id FROM team_members WHERE member_id = ? AND linked_member_id IS NOT NULL",
             (member_id,)
         ) as cursor:
             linked_row = await cursor.fetchone()
             if linked_row and linked_row[0]:
                 await db.execute(
                     "UPDATE team_members SET status = 'ACTIVE' WHERE member_id = ?",
                     (linked_row[0],)
                 )
                 await db.commit()

         # For 3+ player mode: Get all linked encounters via soul_link_pairs
         route_encountered = row[1]
         if route_encountered:
             async with db.execute(
                 """SELECT route_id FROM routes WHERE route_number = ? 
                    AND run_id IN (SELECT run_id FROM run_players WHERE player_id IN 
                                   (SELECT player_id FROM team_members WHERE member_id = ?))""",
                 (route_encountered, member_id)
             ) as cursor:
                 route_result = await cursor.fetchone()
                 if route_result:
                     route_id = route_result[0]

                     # Get all encounters on this route
                     async with db.execute(
                         "SELECT encounter_id FROM encounters WHERE route_id = ?",
                         (route_id,)
                     ) as cursor:
                         encounters = await cursor.fetchall()

                     # Get all team members from these encounters
                     for (enc_id,) in encounters:
                         async with db.execute(
                             """SELECT tm.member_id FROM team_members tm
                                JOIN encounters e ON e.encounter_id = ?
                                WHERE tm.player_id = e.player_id AND tm.status != 'ACTIVE'""",
                             (enc_id,)
                         ) as cursor:
                             members = await cursor.fetchall()
                             for (linked_member_id,) in members:
                                 if linked_member_id != member_id:
                                     await db.execute(
                                         "UPDATE team_members SET status = 'ACTIVE' WHERE member_id = ?",
                                         (linked_member_id,)
                                     )
                     await db.commit()


async def release_pokemon(member_id: int):
     """Mark a Pokemon as released."""
     # Use the all_linked version to handle 2-4 player modes
     await release_all_linked_pokemon(member_id)


# RUN COMPLETION/DELETION FUNCTIONS

async def end_run(run_id: int):
    """Mark a run as completed (soft delete)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE runs SET status = 'COMPLETED' WHERE run_id = ?",
            (run_id,)
        )
        await db.commit()


async def delete_run(run_id: int):
    """Permanently delete a run and all related data (hard delete)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Enable foreign key enforcement
        await db.execute("PRAGMA foreign_keys = ON")

        # Get all route IDs for this run first
        async with db.execute(
            "SELECT route_id FROM routes WHERE run_id = ?",
            (run_id,)
        ) as cursor:
            routes = await cursor.fetchall()
            route_ids = [r[0] for r in routes]

        # Delete soul link pairs for all encounters in these routes
        for route_id in route_ids:
            await db.execute(
                """DELETE FROM soul_link_pairs 
                   WHERE encounter_id_1 IN (SELECT encounter_id FROM encounters WHERE route_id = ?)
                   OR encounter_id_2 IN (SELECT encounter_id FROM encounters WHERE route_id = ?)""",
                (route_id, route_id)
            )

        # Delete all encounters for these routes
        for route_id in route_ids:
            await db.execute(
                "DELETE FROM encounters WHERE route_id = ?",
                (route_id,)
            )

        # Delete all routes for this run
        await db.execute(
            "DELETE FROM routes WHERE run_id = ?",
            (run_id,)
        )

        # Get all player IDs for this run
        async with db.execute(
            "SELECT player_id FROM run_players WHERE run_id = ?",
            (run_id,)
        ) as cursor:
            players = await cursor.fetchall()
            player_ids = [p[0] for p in players]

        # Delete all team members for these players
        for player_id in player_ids:
            await db.execute(
                "DELETE FROM team_members WHERE player_id = ?",
                (player_id,)
            )

        # Delete all players for this run
        await db.execute(
            "DELETE FROM run_players WHERE run_id = ?",
            (run_id,)
        )

        # Finally, delete the run itself
        await db.execute(
            "DELETE FROM runs WHERE run_id = ?",
            (run_id,)
        )

        await db.commit()

        # Check if there are any runs left in the database
        async with db.execute(
            "SELECT COUNT(*) FROM runs"
        ) as cursor:
            run_count = (await cursor.fetchone())[0]

        # If no runs left, reset all auto-increment sequences to their starting values
        if run_count == 0:
            # Reset sequences to their starting values:
            # run_id: 0, player_id: 999, route_id: 1999, encounter_id: 2999,
            # team_members: 3999, soul_link_pairs: 4999
            await db.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'runs'")
            await db.execute("UPDATE sqlite_sequence SET seq = 999 WHERE name = 'run_players'")
            await db.execute("UPDATE sqlite_sequence SET seq = 1999 WHERE name = 'routes'")
            await db.execute("UPDATE sqlite_sequence SET seq = 2999 WHERE name = 'encounters'")
            await db.execute("UPDATE sqlite_sequence SET seq = 3999 WHERE name = 'team_members'")
            await db.execute("UPDATE sqlite_sequence SET seq = 4999 WHERE name = 'soul_link_pairs'")

            await db.commit()


# SOUL LINK/LINKING FUNCTIONS

async def get_linked_encounter_ids(encounter_id: int):
    """Get all encounter IDs linked to the given encounter (returns all linked encounters including self)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            """SELECT DISTINCT encounter_id FROM (
                SELECT encounter_id_1 as encounter_id FROM soul_link_pairs WHERE encounter_id_2 = ?
                UNION
                SELECT encounter_id_2 as encounter_id FROM soul_link_pairs WHERE encounter_id_1 = ?
                UNION
                SELECT ? as encounter_id
            )""",
            (encounter_id, encounter_id, encounter_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_team_members_from_encounter(encounter_id: int):
    """Get all team members that came from a specific encounter."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT DISTINCT tm.* FROM team_members tm
               JOIN encounters e ON e.pokemon_name = tm.pokemon_name
               WHERE e.encounter_id = ?""",
            (encounter_id,)
        ) as cursor:
            return await cursor.fetchall()


async def faint_all_linked_pokemon(member_id: int):
     """Faint a Pokemon and all its Soul Link partners."""
     async with aiosqlite.connect(DATABASE_PATH) as db:
         # Get the member to faint and their route_encountered
         async with db.execute(
             "SELECT member_id, route_encountered FROM team_members WHERE member_id = ?",
             (member_id,)
         ) as cursor:
             row = await cursor.fetchone()
             if not row:
                 return

         # Faint the member
         await db.execute(
             "UPDATE team_members SET status = 'FAINTED' WHERE member_id = ?",
             (member_id,)
         )
         await db.commit()

         # For 2-player mode: Get linked_member_id (if any)
         async with db.execute(
             "SELECT linked_member_id FROM team_members WHERE member_id = ? AND linked_member_id IS NOT NULL",
             (member_id,)
         ) as cursor:
             linked_row = await cursor.fetchone()
             if linked_row and linked_row[0]:
                 await db.execute(
                     "UPDATE team_members SET status = 'FAINTED' WHERE member_id = ?",
                     (linked_row[0],)
                 )
                 await db.commit()

         # For 3+ player mode: Get all linked encounters via soul_link_pairs
         route_encountered = row[1]
         if route_encountered:
             async with db.execute(
                 """SELECT route_id FROM routes WHERE route_number = ? 
                    AND run_id IN (SELECT run_id FROM run_players WHERE player_id IN 
                                   (SELECT player_id FROM team_members WHERE member_id = ?))""",
                 (route_encountered, member_id)
             ) as cursor:
                 route_result = await cursor.fetchone()
                 if route_result:
                     route_id = route_result[0]

                     # Get all encounters on this route
                     async with db.execute(
                         "SELECT encounter_id FROM encounters WHERE route_id = ?",
                         (route_id,)
                     ) as cursor:
                         encounters = await cursor.fetchall()

                     # Get all team members from these encounters
                     for (enc_id,) in encounters:
                         async with db.execute(
                             """SELECT tm.member_id FROM team_members tm
                                JOIN encounters e ON e.encounter_id = ?
                                WHERE tm.player_id = e.player_id AND tm.status != 'FAINTED'""",
                             (enc_id,)
                         ) as cursor:
                             members = await cursor.fetchall()
                             for (linked_member_id,) in members:
                                 if linked_member_id != member_id:
                                     await db.execute(
                                         "UPDATE team_members SET status = 'FAINTED' WHERE member_id = ?",
                                         (linked_member_id,)
                                     )
                     await db.commit()


async def box_all_linked_pokemon(member_id: int):
     """Box a Pokemon and all its Soul Link partners."""
     async with aiosqlite.connect(DATABASE_PATH) as db:
         # Get the member and their route
         async with db.execute(
             "SELECT member_id, route_encountered FROM team_members WHERE member_id = ?",
             (member_id,)
         ) as cursor:
             row = await cursor.fetchone()
             if not row:
                 return

         # Box the member
         await db.execute(
             "UPDATE team_members SET status = 'BOXED' WHERE member_id = ?",
             (member_id,)
         )
         await db.commit()

         # For 2-player mode: Get linked_member_id (if any)
         async with db.execute(
             "SELECT linked_member_id FROM team_members WHERE member_id = ? AND linked_member_id IS NOT NULL",
             (member_id,)
         ) as cursor:
             linked_row = await cursor.fetchone()
             if linked_row and linked_row[0]:
                 await db.execute(
                     "UPDATE team_members SET status = 'BOXED' WHERE member_id = ?",
                     (linked_row[0],)
                 )
                 await db.commit()

         # For 3+ player mode: Get all linked encounters via soul_link_pairs
         route_encountered = row[1]
         if route_encountered:
             async with db.execute(
                 """SELECT route_id FROM routes WHERE route_number = ? 
                    AND run_id IN (SELECT run_id FROM run_players WHERE player_id IN 
                                   (SELECT player_id FROM team_members WHERE member_id = ?))""",
                 (route_encountered, member_id)
             ) as cursor:
                 route_result = await cursor.fetchone()
                 if route_result:
                     route_id = route_result[0]

                     # Get all encounters on this route
                     async with db.execute(
                         "SELECT encounter_id FROM encounters WHERE route_id = ?",
                         (route_id,)
                     ) as cursor:
                         encounters = await cursor.fetchall()

                     # Get all team members from these encounters
                     for (enc_id,) in encounters:
                         async with db.execute(
                             """SELECT tm.member_id FROM team_members tm
                                JOIN encounters e ON e.encounter_id = ?
                                WHERE tm.player_id = e.player_id AND tm.status != 'BOXED'""",
                             (enc_id,)
                         ) as cursor:
                             members = await cursor.fetchall()
                             for (linked_member_id,) in members:
                                 if linked_member_id != member_id:
                                     await db.execute(
                                         "UPDATE team_members SET status = 'BOXED' WHERE member_id = ?",
                                         (linked_member_id,)
                                     )
                     await db.commit()


async def release_all_linked_pokemon(member_id: int):
     """Release a Pokemon and all its Soul Link partners."""
     async with aiosqlite.connect(DATABASE_PATH) as db:
         # Get the member and their route
         async with db.execute(
             "SELECT member_id, route_encountered FROM team_members WHERE member_id = ?",
             (member_id,)
         ) as cursor:
             row = await cursor.fetchone()
             if not row:
                 return

         # Release the member
         await db.execute(
             "UPDATE team_members SET status = 'RELEASED' WHERE member_id = ?",
             (member_id,)
         )
         await db.commit()

         # For 2-player mode: Get linked_member_id (if any)
         async with db.execute(
             "SELECT linked_member_id FROM team_members WHERE member_id = ? AND linked_member_id IS NOT NULL",
             (member_id,)
         ) as cursor:
             linked_row = await cursor.fetchone()
             if linked_row and linked_row[0]:
                 await db.execute(
                     "UPDATE team_members SET status = 'RELEASED' WHERE member_id = ?",
                     (linked_row[0],)
                 )
                 await db.commit()

         # For 3+ player mode: Get all linked encounters via soul_link_pairs
         route_encountered = row[1]
         if route_encountered:
             async with db.execute(
                 """SELECT route_id FROM routes WHERE route_number = ? 
                    AND run_id IN (SELECT run_id FROM run_players WHERE player_id IN 
                                   (SELECT player_id FROM team_members WHERE member_id = ?))""",
                 (route_encountered, member_id)
             ) as cursor:
                 route_result = await cursor.fetchone()
                 if route_result:
                     route_id = route_result[0]

                     # Get all encounters on this route
                     async with db.execute(
                         "SELECT encounter_id FROM encounters WHERE route_id = ?",
                         (route_id,)
                     ) as cursor:
                         encounters = await cursor.fetchall()

                     # Get all team members from these encounters
                     for (enc_id,) in encounters:
                         async with db.execute(
                             """SELECT tm.member_id FROM team_members tm
                                JOIN encounters e ON e.encounter_id = ?
                                WHERE tm.player_id = e.player_id AND tm.status != 'RELEASED'""",
                             (enc_id,)
                         ) as cursor:
                             members = await cursor.fetchall()
                             for (linked_member_id,) in members:
                                 if linked_member_id != member_id:
                                     await db.execute(
                                         "UPDATE team_members SET status = 'RELEASED' WHERE member_id = ?",
                                         (linked_member_id,)
                                     )
                     await db.commit()


async def get_route_id(run_id: int, route_number: int):
    """Get route_id from run_id and route_number."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT route_id FROM routes WHERE run_id = ? AND route_number = ?",
            (run_id, route_number)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None


async def auto_link_route_encounters(route_id: int):
    """Automatically link all encounters on a route (2-4 players).
    Returns tuple of (success, message, linked_count)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT encounter_id, pokemon_name FROM encounters WHERE route_id = ? ORDER BY player_id",
            (route_id,)
        ) as cursor:
            encounters = await cursor.fetchall()
    
    # Need at least 2 encounters to link
    if len(encounters) < 2:
        return False, "Need at least 2 encounters to auto-link", 0
    
    # Check if already linked
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            """SELECT COUNT(*) FROM soul_link_pairs slp
               WHERE slp.encounter_id_1 IN (SELECT encounter_id FROM encounters WHERE route_id = ?)
               OR slp.encounter_id_2 IN (SELECT encounter_id FROM encounters WHERE route_id = ?)""",
            (route_id, route_id)
        ) as cursor:
            existing_links = (await cursor.fetchone())[0]
    
    if existing_links > 0:
        # Already linked, return info
        return True, f"Route encounters already linked", 0
    
    # Link all encounters together
    linked_count = 0
    for i in range(len(encounters)):
        for j in range(i + 1, len(encounters)):
            await link_pokemon_pair(encounters[i]['encounter_id'], encounters[j]['encounter_id'])
            linked_count += 1
    
    return True, f"Auto-linked {len(encounters)} Pokemon on this route", linked_count

