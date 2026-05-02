import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from config import DATABASE_PATH
from utils import create_embed
import database as db_utils
import logging_utils

class SoulLink(commands.Cog):
    """Commands for Soul Link specific features."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="link_pokemon", description="Link Pokemon encounters as Soul Link partners (by route_number or manually)")
    @app_commands.describe(
        run_id="The run ID (required for route_number linking)",
        route_number="Route number to link (e.g., 1 for Route 1) - use this OR encounter_ids",
        encounter_id_1="First encounter ID (optional - use with other encounter_ids instead of route)",
        encounter_id_2="Second encounter ID (optional)",
        encounter_id_3="Third encounter ID for 3-player (optional)",
        encounter_id_4="Fourth encounter ID for 4-player (optional)"
    )
    async def link_pokemon(self, interaction: discord.Interaction, run_id: int = None, route_number: int = None,
                          encounter_id_1: int = None, encounter_id_2: int = None,
                          encounter_id_3: int = None, encounter_id_4: int = None):
        """Link Pokemon encounters as Soul Link partners (supports 2-4 players)."""
        try:
            await interaction.response.defer()

            # Determine which mode is being used
            if run_id is not None and route_number is not None:
                # MODE 1: Link by run_id and route_number
                await self._link_by_route_number(interaction, run_id, route_number)
            elif encounter_id_1 is not None and encounter_id_2 is not None:
                # MODE 2: Link specific encounters
                encounter_ids = [encounter_id_1, encounter_id_2]
                if encounter_id_3 is not None:
                    encounter_ids.append(encounter_id_3)
                if encounter_id_4 is not None:
                    encounter_ids.append(encounter_id_4)

                await self._link_by_encounters(interaction, encounter_ids)
            else:
                embed = create_embed(
                    "❌ Error",
                    "Please provide EITHER:\n• `run_id:X route_number:Y` to link all encounters on a route\nOR\n• `encounter_id_1:X encounter_id_2:Y` (and optionally encounter_id_3, encounter_id_4)",
                    discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def _link_by_route_number(self, interaction: discord.Interaction, run_id: int, route_number: int):
        """Link all encounters on a specific route by route_number."""
        # Get the route_id from run_id and route_number
        route_id = None
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT route_id FROM routes WHERE run_id = ? AND route_number = ?",
                (run_id, route_number)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    route_id = result[0]

        if not route_id:
            embed = create_embed("❌ Error", f"Route {route_number} not found in run {run_id}", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Now use the existing link_by_route logic but pass route_id
        await self._link_by_route(interaction, route_id, run_id)

    async def _link_by_route(self, interaction: discord.Interaction, route_id: int, run_id: int = None):
        """Link all encounters on a specific route."""
        # Get run_id from route if not provided
        if not run_id:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT run_id FROM routes WHERE route_id = ?",
                    (route_id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    run_id = result[0] if result else None
        
        # Get all encounters on this route along with route info
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT e.*, r.route_number FROM encounters e
                   JOIN routes r ON e.route_id = r.route_id
                   WHERE e.route_id = ? ORDER BY e.player_id""",
                (route_id,)
            ) as cursor:
                encounters = await cursor.fetchall()

        if not encounters:
            embed = create_embed("❌ Error", f"No encounters found on route {route_id}", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if len(encounters) < 2:
            embed = create_embed("❌ Error", "Need at least 2 encounters to link", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if len(encounters) > 4:
            embed = create_embed("❌ Error", "Cannot link more than 4 encounters on one route", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

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
            embed = create_embed(
                "⚠️ Already Linked",
                f"The encounters on Route {encounters[0]['route_number']} are already linked!",
                discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Link all encounters to each other (create pairs for all combinations)
        encounter_ids = [e['encounter_id'] for e in encounters]
        pokemon_names = [e['pokemon_name'] for e in encounters]
        await self._link_encounters_together(encounter_ids)

        # Log the soul link
        await logging_utils.log_event(
            run_id,
            "POKEMON_LINKED",
            f"{len(encounters)} Pokemon linked on Route {encounters[0]['route_number']}",
            {
                "route": encounters[0]['route_number'],
                "pokemon_count": len(encounters),
                "pokemon": ", ".join(pokemon_names)
            }
        )

        # Get player info for all encounters
        player_info = ""
        for enc in encounters:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT discord_name FROM run_players WHERE player_id = ?",
                    (enc['player_id'],)
                ) as cursor:
                    player_name = (await cursor.fetchone())[0]

            player_info += f"📍 {player_name}: **{enc['pokemon_name']}** ({enc['pokemon_type']})\n"

        embed = create_embed(
            "🔗 Pokemon Linked",
            f"All {len(encounters)} Pokemon on Route {encounters[0]['route_number']} are now linked",
            discord.Color.purple()
        )
        embed.add_field(name="Linked Pokemon", value=player_info, inline=False)
        embed.add_field(
            name="⚠️ Soul Link Rules Now Active",
            value="If one Pokemon faints, ALL linked partners faint too.\nIf one is boxed/released, ALL partners are too.",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    async def _link_by_encounters(self, interaction: discord.Interaction, encounter_ids: list):
        """Link specific encounters provided by user."""
        if len(encounter_ids) < 2 or len(encounter_ids) > 4:
            embed = create_embed("❌ Error", "Please provide 2-4 encounter IDs", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Verify all encounters exist
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            for enc_id in encounter_ids:
                async with db.execute(
                    "SELECT * FROM encounters WHERE encounter_id = ?",
                    (enc_id,)
                ) as cursor:
                    if not await cursor.fetchone():
                        embed = create_embed("❌ Error", f"Encounter {enc_id} not found", discord.Color.red())
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return

        # Check if already linked
        async with aiosqlite.connect(DATABASE_PATH) as db:
            for enc_id in encounter_ids:
                async with db.execute(
                    """SELECT COUNT(*) FROM soul_link_pairs 
                       WHERE encounter_id_1 = ? OR encounter_id_2 = ?""",
                    (enc_id, enc_id)
                ) as cursor:
                    if (await cursor.fetchone())[0] > 0:
                        embed = create_embed(
                            "⚠️ Already Linked",
                            f"One or more of these encounters are already linked!",
                            discord.Color.orange()
                        )
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return

        # Link them together
        await self._link_encounters_together(encounter_ids)

        # Get encounter details
        encounter_info = ""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            for enc_id in encounter_ids:
                async with db.execute(
                    """SELECT e.*, p.discord_name FROM encounters e
                       JOIN run_players p ON e.player_id = p.player_id
                       WHERE e.encounter_id = ?""",
                    (enc_id,)
                ) as cursor:
                    enc = await cursor.fetchone()
                    encounter_info += f"📍 {enc['discord_name']}: **{enc['pokemon_name']}** ({enc['pokemon_type']})\n"

        embed = create_embed(
            "🔗 Pokemon Linked",
            f"All {len(encounter_ids)} Pokemon are now linked together",
            discord.Color.purple()
        )
        embed.add_field(name="Linked Pokemon", value=encounter_info, inline=False)
        embed.add_field(
            name="⚠️ Soul Link Rules Now Active",
            value="If one Pokemon faints, ALL linked partners faint too.\nIf one is boxed/released, ALL partners are too.",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    async def _link_encounters_together(self, encounter_ids: list):
        """Helper to link all encounters in the list to each other."""
        for i in range(len(encounter_ids)):
            for j in range(i + 1, len(encounter_ids)):
                await db_utils.link_pokemon_pair(encounter_ids[i], encounter_ids[j])


    @app_commands.command(name="soul_link_status", description="View Soul Link pairs in a run")
    @app_commands.describe(
        run_id="The run ID"
    )
    async def soul_link_status(self, interaction: discord.Interaction, run_id: int):
        """View all Soul Link pairs in a run (groups 3+ player links together)."""
        try:
            await interaction.response.defer()

            # Get run
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get all routes and their encounters to group linked Pokemon
            async with aiosqlite.connect(DATABASE_PATH) as db:
                db.row_factory = aiosqlite.Row

                # Get all routes
                async with db.execute(
                    "SELECT * FROM routes WHERE run_id = ? ORDER BY route_number",
                    (run_id,)
                ) as cursor:
                    routes = await cursor.fetchall()

            # Build info for each route showing linked Pokemon groups
            route_groups = {}  # route_number -> list of linked Pokemon

            for route in routes:
                # Get all encounters on this route
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        """SELECT e.encounter_id, e.pokemon_name, e.pokemon_type, rp.discord_name
                           FROM encounters e
                           JOIN run_players rp ON e.player_id = rp.player_id
                           WHERE e.route_id = ?
                           ORDER BY rp.discord_name""",
                        (route['route_id'],)
                    ) as cursor:
                        encounters = await cursor.fetchall()

                if encounters:
                    route_groups[route['route_number']] = encounters

            embed = create_embed(
                f"🔗 {run[2]} - Soul Link Groups",
                f"Total linked routes: {len(route_groups)}",
                discord.Color.purple()
            )

            if not route_groups:
                embed.add_field(name="Soul Links", value="No Soul Link groups yet", inline=False)
            else:
                for route_num in sorted(route_groups.keys()):
                    encounters = route_groups[route_num]
                    pokemon_info = ""
                    for enc in encounters:
                        status = "✅"
                        pokemon_info += f"{status} {enc['discord_name']}: **{enc['pokemon_name']}** ({enc['pokemon_type']})\n"

                    link_text = f"**{len(encounters)} Pokemon Linked**" if len(encounters) > 2 else f"**Pair**"
                    embed.add_field(
                        name=f"Route {route_num} - {link_text}",
                        value=pokemon_info.strip(),
                        inline=False
                    )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="check_run_health", description="Check overall health of a 2-player Soul Link run")
    @app_commands.describe(
        run_id="The run ID"
    )
    async def check_run_health(self, interaction: discord.Interaction, run_id: int):
        """Check health of a 2-player Soul Link run."""
        try:
            await interaction.response.defer()

            # Get run
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            if run[5] < 2:  # num_players
                embed = create_embed("❌ Error", "This command is for 2+ player runs", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get players and teams
            players = await db_utils.get_players_in_run(run_id)

            embed = create_embed(
                f"💚 {run[2]} - Run Health",
                f"Status: {run[6]}",
                discord.Color.green()
            )

            for player in players:
                team = await db_utils.get_player_team(player['player_id'])
                active_count = len([m for m in team if m['status'] == 'ACTIVE'])
                fainted_count = len([m for m in team if m['status'] == 'FAINTED'])

                health_bar = ""
                if active_count == 0:
                    health_bar = "💀 Team Wiped!"
                else:
                    health_bar = f"✅ {active_count} active | 💀 {fainted_count} fainted"

                embed.add_field(
                    name=f"{player['discord_name']} (Deaths: {player['deaths']})",
                    value=health_bar,
                    inline=False
                )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="rules_check", description="Check if teams follow Soul Link rules")
    @app_commands.describe(
        run_id="The run ID",
        clause="Which clause to check (type_restriction)"
    )
    async def rules_check(self, interaction: discord.Interaction, run_id: int, clause: str = "type_restriction"):
        """Check if teams follow selected Soul Link rules."""
        try:
            await interaction.response.defer()

            # Get run
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            if clause == "type_restriction":
                violations = []

                # Get all active Pokemon in run
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        """SELECT tm.pokemon_name, tm.pokemon_type, rp.discord_name, rp.player_id
                           FROM team_members tm
                           JOIN run_players rp ON tm.player_id = rp.player_id
                           WHERE rp.run_id = ? AND tm.status = 'ACTIVE'
                           ORDER BY tm.pokemon_type""",
                        (run_id,)
                    ) as cursor:
                        all_pokemon = await cursor.fetchall()

                # Check for duplicate types across teams
                players = await db_utils.get_players_in_run(run_id)

                for p1_idx, player1 in enumerate(players):
                    for p2_idx, player2 in enumerate(players):
                        if p1_idx >= p2_idx:
                            continue

                        player1_types = {}
                        player2_types = {}

                        for mon in all_pokemon:
                            if mon['player_id'] == player1['player_id']:
                                player1_types[mon['pokemon_type']] = mon['pokemon_name']
                            elif mon['player_id'] == player2['player_id']:
                                player2_types[mon['pokemon_type']] = mon['pokemon_name']

                        shared = set(player1_types.keys()) & set(player2_types.keys())
                        if shared:
                            for type_ in shared:
                                violations.append(f"Type **{type_}** shared: {player1['discord_name']} has {player1_types[type_]}, {player2['discord_name']} has {player2_types[type_]}")

                embed = create_embed(
                    f"📋 {run[2]} - Type Restriction Check",
                    color=discord.Color.green() if not violations else discord.Color.red()
                )

                if not violations:
                    embed.add_field(name="✅ Result", value="No type violations found!", inline=False)
                else:
                    violations_text = "\n".join(violations)
                    embed.add_field(name="⚠️ Violations Found", value=violations_text, inline=False)

                await interaction.followup.send(embed=embed)
            else:
                embed = create_embed("❌ Error", f"Unknown clause: {clause}", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SoulLink(bot))

