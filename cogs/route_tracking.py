import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from config import DATABASE_PATH
from utils import create_embed
import database as db_utils
import logging_utils

class RouteTracking(commands.Cog):
    """Commands for tracking routes and encounters."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_route", description="Add a route to a run")
    @app_commands.describe(
        run_id="The run to add the route to",
        route_number="Route number (e.g., 1 for Route 1)",
        route_name="Optional name for the route"
    )
    async def add_route(self, interaction: discord.Interaction, run_id: int, route_number: int, route_name: str = ""):
        """Add a route to a Nuzlocke run."""
        try:
            # Check if run exists
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check if route already exists
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM routes WHERE run_id = ? AND route_number = ?",
                    (run_id, route_number)
                ) as cursor:
                    if await cursor.fetchone():
                        embed = create_embed("❌ Error", f"Route {route_number} already exists in this run", discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return

            # Add route
            route_id = await db_utils.add_route_to_run(run_id, route_number, route_name)

            embed = create_embed(
                "✅ Route Added",
                f"**Route {route_number}** {f'({route_name})' if route_name else ''}",
                discord.Color.green()
            )
            embed.add_field(name="Route ID", value=route_id, inline=False)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="list_routes", description="List all routes in a run")
    @app_commands.describe(
        run_id="The run ID"
    )
    async def list_routes(self, interaction: discord.Interaction, run_id: int):
        """List all routes in a Nuzlocke run."""
        try:
            await interaction.response.defer()

            # Get run
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get routes
            routes = await db_utils.get_routes_in_run(run_id)

            if not routes:
                embed = create_embed(
                    f"📋 {run[3]} - Routes",
                    "No routes found",
                    discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                return

            embed = create_embed(
                f"📋 {run[3]} - Routes",
                f"Total routes: {len(routes)}",
                discord.Color.blue()
            )

            for route in routes:
                # Get encounter count for this route
                encounters = await db_utils.get_encounters_for_route(route['route_id'])

                route_info = f"Route ID: {route['route_id']}\n"
                route_info += f"Encounters: {len(encounters)}\n"
                route_info += f"Status: {route['status']}"

                # Build route name
                route_display_name = f"Route {route['route_number']}"
                if route['route_name']:
                    route_display_name += f" ({route['route_name']})"

                embed.add_field(
                    name=route_display_name,
                    value=route_info,
                    inline=False
                )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="record_encounter", description="Record a Pokemon encounter and automatically add it to team")
    @app_commands.describe(
        run_id="The run ID",
        route_number="Route number (e.g., 1 for Route 1)",
        player_id="Player ID making the encounter",
        pokemon_name="Name/species of the Pokemon",
        pokemon_type="Primary type of the Pokemon",
        level="Pokemon level (default 1)"
    )
    async def record_encounter(self, interaction: discord.Interaction, run_id: int, route_number: int,
                              player_id: int, pokemon_name: str, pokemon_type: str = "", level: int = 1):
        """Record a Pokemon encounter and automatically add it to the team and create the route."""
        try:
            await interaction.response.defer()

            # Get run and verify it exists
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Verify player exists
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM run_players WHERE player_id = ? AND run_id = ?",
                    (player_id, run_id)
                ) as cursor:
                    player = await cursor.fetchone()

            if not player:
                embed = create_embed("❌ Error", f"Player with ID {player_id} not found in this run", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get or create the route automatically
            route_id = None
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT route_id FROM routes WHERE run_id = ? AND route_number = ?",
                    (run_id, route_number)
                ) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        route_id = result[0]

            # If route doesn't exist, create it
            if not route_id:
                route_id = await db_utils.add_route_to_run(run_id, route_number, "")

            # Record the encounter
            encounter_id = await db_utils.add_encounter(route_id, player_id, pokemon_name, pokemon_type)

            # Automatically add Pokemon to team with route_encountered set
            member_id = await db_utils.add_team_member(
                player_id,
                pokemon_name,
                pokemon_type,
                level=level,
                is_starter=False,
                route_encountered=route_number
            )

            # Log encounter
            await logging_utils.log_event(
                run_id,
                "ENCOUNTER_RECORDED",
                f"{player[3]} caught {pokemon_name} on Route {route_number}",
                {
                    "player": player[3],
                    "pokemon": pokemon_name,
                    "type": pokemon_type,
                    "level": level,
                    "route": route_number,
                    "encounter_id": encounter_id
                }
            )

            # Try to auto-link all encounters on this route
            auto_link_success, auto_link_msg, linked_count = await db_utils.auto_link_route_encounters(route_id)

            embed = create_embed(
                "✅ Encounter Recorded & Added to Team",
                f"**{pokemon_name}** ({pokemon_type}) on Route {route_number}",
                discord.Color.green()
            )
            embed.add_field(name="Player", value=f"{player[3]}", inline=True)
            embed.add_field(name="Level", value=level, inline=True)
            embed.add_field(name="Encounter ID", value=encounter_id, inline=False)
            embed.add_field(name="Team Member ID", value=member_id, inline=False)

            # Add Soul Link info to embed
            if auto_link_success and linked_count > 0:
                embed.add_field(name="🔗 Soul Link Status", value=f"✅ {auto_link_msg}", inline=False)
            elif auto_link_success and linked_count == 0:
                embed.add_field(name="🔗 Soul Link Status", value=f"⏳ {auto_link_msg}\nWaiting for other players to record encounters on this route", inline=False)
            else:
                embed.add_field(name="Next Steps", value="All players can record their Route encounters, then link them with `/link_pokemon route_id:X`", inline=False)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="view_route", description="View all encounters on a route by route_number")
    @app_commands.describe(
        run_id="The run ID",
        route_number="Route number (e.g., 1 for Route 1)"
    )
    async def view_route(self, interaction: discord.Interaction, run_id: int, route_number: int):
        """View encounters on a route."""
        try:
            await interaction.response.defer()

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

            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM routes WHERE route_id = ?",
                    (route_id,)
                ) as cursor:
                    route = await cursor.fetchone()

            if not route:
                embed = create_embed("❌ Error", f"Route with ID {route_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            encounters = await db_utils.get_encounters_for_route(route_id)

            embed = create_embed(
                f"🗺️ Route {route[2]} {f'({route[3]})' if route[3] else ''}",
                f"Status: {route[4]}",
                discord.Color.blue()
            )

            if not encounters:
                embed.add_field(name="Encounters", value="No encounters recorded yet", inline=False)
            else:
                encounter_info = ""
                for enc in encounters:
                    status_icon = "✅" if enc[5] == "ACTIVE" else "❌"
                    encounter_info += f"{status_icon} [{enc['discord_name']}] **{enc[3]}** ({enc[4]})\n"
                embed.add_field(name=f"Encounters ({len(encounters)})", value=encounter_info, inline=False)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="view_encounters", description="View all routes and encounters in a run")
    @app_commands.describe(
        run_id="The run ID to view"
    )
    async def view_encounters(self, interaction: discord.Interaction, run_id: int):
        """View all routes and encounters in a run."""
        try:
            await interaction.response.defer()

            # Get run
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get routes
            routes = await db_utils.get_routes_in_run(run_id)

            embed = create_embed(
                f"📊 {run[2]} - Encounter Summary",
                f"Game: {run[3]} | Routes: {len(routes)}",
                discord.Color.blue()
            )

            if not routes:
                embed.add_field(name="Routes", value="No routes added yet", inline=False)
                await interaction.followup.send(embed=embed)
                return

            for route in routes:
                encounters = await db_utils.get_encounters_for_route(route[0])

                if not encounters:
                    route_text = "No encounters yet"
                else:
                    route_text = ""
                    for enc in encounters:
                        route_text += f"• {enc['discord_name']}: **{enc[3]}** ({enc[4]})\n"

                embed.add_field(
                    name=f"Route {route[2]} {f'({route[3]})' if route[3] else ''} ({len(encounters)} encounters)",
                    value=route_text if route_text else "No encounters yet",
                    inline=False
                )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RouteTracking(bot))

