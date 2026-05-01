import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from config import DATABASE_PATH, MAX_PLAYERS, MIN_PLAYERS, AVAILABLE_CLAUSES
from utils import create_embed
import database as db_utils

class RunManagement(commands.Cog):
    """Commands for creating and managing Nuzlocke runs."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create_run", description="Create a new Nuzlocke run")
    @app_commands.describe(
        run_name="Name for this run",
        game_name="Pokemon game being played",
        num_players="Number of players (1-4)",
        clauses="Comma-separated clauses to enable"
    )
    async def create_run(self, interaction: discord.Interaction, run_name: str, game_name: str,
                         num_players: int, clauses: str = ""):
        """Create a new Nuzlocke run."""
        # Validate guild context
        if not interaction.guild or not interaction.channel:
            embed = create_embed("❌ Error", "This command can only be used in a server, not in DMs", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if num_players < MIN_PLAYERS or num_players > MAX_PLAYERS:
            embed = create_embed("❌ Error", f"Number of players must be between {MIN_PLAYERS} and {MAX_PLAYERS}", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Parse clauses
            clause_list = [c.strip().lower() for c in clauses.split(",") if c.strip()] if clauses else []

            # Validate clauses
            for clause in clause_list:
                if clause not in AVAILABLE_CLAUSES:
                    embed = create_embed("❌ Invalid Clause", f"Unknown clause: {clause}\nAvailable: {', '.join(AVAILABLE_CLAUSES.keys())}", discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

            # Create run
            run_id = await db_utils.create_run(
                interaction.guild.id,
                interaction.channel.id,
                run_name,
                game_name,
                num_players,
                clause_list
            )

            embed = create_embed(
                "✅ Run Created",
                f"**Name:** {run_name}\n**Game:** {game_name}\n**Players:** {num_players}\n**Clauses:** {', '.join(clause_list) if clause_list else 'None'}",
                discord.Color.green()
            )
            embed.add_field(name="Run ID", value=run_id, inline=False)
            embed.add_field(name="Next Steps", value=f"Use `/join_run` to add players to this run", inline=False)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="list_runs", description="List all active runs in this server")
    async def list_runs(self, interaction: discord.Interaction):
        """List all active Nuzlocke runs."""
        # Validate guild context
        if not interaction.guild:
            embed = create_embed("❌ Error", "This command can only be used in a server, not in DMs", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Defer early since we need to query the database
            await interaction.response.defer()

            async with aiosqlite.connect(DATABASE_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM runs WHERE guild_id = ? AND status = 'ACTIVE' ORDER BY created_at DESC",
                    (interaction.guild.id,)
                ) as cursor:
                    runs = await cursor.fetchall()

            if not runs:
                embed = create_embed("📋 Active Runs", "No active runs found", discord.Color.blue())
                await interaction.followup.send(embed=embed)
                return

            embed = create_embed("📋 Active Runs", color=discord.Color.blue())

            for run in runs:
                # Get player count
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        "SELECT COUNT(*) FROM run_players WHERE run_id = ?",
                        (run['run_id'],)
                    ) as cursor:
                        player_count = (await cursor.fetchone())[0]

                clauses = run['clauses'] if run['clauses'] else "None"
                embed.add_field(
                    name=f"**{run['run_name']}** (ID: {run['run_id']})",
                    value=f"Game: {run['game_name']}\nPlayers: {player_count}/{run['num_players']}\nClauses: {clauses}",
                    inline=False
                )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="join_run", description="Join an existing Nuzlocke run")
    @app_commands.describe(
        run_id="The ID of the run to join"
    )
    async def join_run(self, interaction: discord.Interaction, run_id: int):
        """Join an existing Nuzlocke run."""
        # Validate guild context
        if not interaction.guild:
            embed = create_embed("❌ Error", "This command can only be used in a server, not in DMs", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Check if run exists and get details
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if run[1] != interaction.guild.id:  # guild_id is at index 1
                embed = create_embed("❌ Error", "This run is from a different server", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check if player already in run
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM run_players WHERE run_id = ? AND user_id = ?",
                    (run_id, interaction.user.id)
                ) as cursor:
                    if await cursor.fetchone():
                        embed = create_embed("❌ Error", "You're already in this run", discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return

                # Check player count
                async with db.execute(
                    "SELECT COUNT(*) FROM run_players WHERE run_id = ?",
                    (run_id,)
                ) as cursor:
                    player_count = (await cursor.fetchone())[0]

            if player_count >= run[5]:  # num_players is at index 5
                embed = create_embed("❌ Error", f"This run is full ({player_count}/{run[5]} players)", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Add player to run
            player_id = await db_utils.add_player_to_run(
                run_id,
                interaction.user.id,
                interaction.user.name,
                player_count + 1
            )

            embed = create_embed(
                "✅ Joined Run",
                f"You've joined **{run[3]}** (Player {player_count + 1}/{run[5]})",
                discord.Color.green()
            )
            embed.add_field(name="Player ID", value=player_id, inline=False)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="run_status", description="Get detailed status of a run")
    @app_commands.describe(
        run_id="The ID of the run"
    )
    async def run_status(self, interaction: discord.Interaction, run_id: int):
        """Get detailed status of a Nuzlocke run."""
        try:
            await interaction.response.defer()

            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            players = await db_utils.get_players_in_run(run_id)
            routes = await db_utils.get_routes_in_run(run_id)

            embed = create_embed(
                f"📊 {run[3]} - {run[4]}",
                f"**Status:** {run[6]}\n**Clauses:** {run[7] if run[7] else 'None'}",
                discord.Color.blue()
            )

            # Players info
            player_info = ""
            for player in players:
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        "SELECT COUNT(*) FROM team_members WHERE player_id = ? AND status = 'ACTIVE'",
                        (player['player_id'],)
                    ) as cursor:
                        active_count = (await cursor.fetchone())[0]

                player_info += f"• {player['discord_name']} - Team: {active_count}, Deaths: {player['deaths']}\n"

            embed.add_field(name="Players", value=player_info if player_info else "No players yet", inline=False)
            embed.add_field(name="Routes", value=f"Total: {len(routes)}", inline=False)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="end_run", description="Complete/End a Nuzlocke run")
    @app_commands.describe(
        run_id="The ID of the run to end"
    )
    async def end_run(self, interaction: discord.Interaction, run_id: int):
        """Complete/End a Nuzlocke run (marks as COMPLETED but keeps data)."""
        try:
            # Check if run exists
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check if run belongs to this guild
            if not interaction.guild or run[1] != interaction.guild.id:
                embed = create_embed("❌ Error", "This run is from a different server", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # End the run
            await db_utils.end_run(run_id)

            embed = create_embed(
                "✅ Run Completed",
                f"**{run[3]}** ({run[4]}) has been marked as completed",
                discord.Color.green()
            )
            embed.add_field(
                name="ℹ️ Note",
                value="The run data is preserved. Use `/delete_run` if you want to permanently remove it.",
                inline=False
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delete_run", description="Permanently delete a Nuzlocke run")
    @app_commands.describe(
        run_id="The ID of the run to delete",
        confirm="Type 'yes' to confirm deletion"
    )
    async def delete_run(self, interaction: discord.Interaction, run_id: int, confirm: str = ""):
        """Permanently delete a Nuzlocke run and all related data."""
        try:
            # Check if run exists
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check if run belongs to this guild
            if not interaction.guild or run[1] != interaction.guild.id:
                embed = create_embed("❌ Error", "This run is from a different server", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check confirmation
            if confirm.lower() != "yes":
                embed = create_embed(
                    "⚠️ Delete Run - Confirmation Required",
                    f"**This will permanently delete the run: {run[3]}**\n\nAll associated data (players, routes, Pokemon, etc.) will be removed and cannot be recovered.",
                    discord.Color.orange()
                )
                embed.add_field(
                    name="To confirm deletion, run:",
                    value=f"`/delete_run run_id:{run_id} confirm:yes`",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Delete the run
            await db_utils.delete_run(run_id)

            embed = create_embed(
                "🗑️ Run Deleted",
                f"**{run[3]}** has been permanently deleted along with all associated data.",
                discord.Color.red()
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(RunManagement(bot))

