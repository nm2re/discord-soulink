import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from config import DATABASE_PATH, POKEMON_TYPES
from utils import create_embed
import database as db_utils
import logging_utils

class TeamManagement(commands.Cog):
    """Commands for managing Pokemon teams."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_pokemon", description="Add a Pokemon to your team")
    @app_commands.describe(
        player_id="Your player ID",
        pokemon_name="Name of the Pokemon",
        pokemon_type="Primary type of the Pokemon",
        level="Level of the Pokemon",
        is_starter="Is this your starter?",
        route_number="Optional route identifier (e.g., 1 or New Bark Town) for encounter-based soul linking"
    )
    async def add_pokemon(self, interaction: discord.Interaction, player_id: int, pokemon_name: str,
                         pokemon_type: str, level: int = 1, is_starter: bool = False,
                         route_number: str = None):
        """Add a Pokemon to a player's team."""
        try:
            if route_number is not None:
                route_number = route_number.strip().lower()

            # Validate type
            if pokemon_type not in POKEMON_TYPES:
                embed = create_embed("❌ Invalid Type", f"Unknown type: {pokemon_type}\nValid types: {', '.join(POKEMON_TYPES)}", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Verify player exists and belongs to user
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM run_players WHERE player_id = ?",
                    (player_id,)
                ) as cursor:
                    player = await cursor.fetchone()

            if not player:
                embed = create_embed("❌ Error", f"Player with ID {player_id} not found", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if player[2] != interaction.user.id:  # user_id is at index 2
                embed = create_embed("❌ Error", "This player doesn't belong to you", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # If a route identifier is provided, make sure this player has an encounter on it.
            # This enables proper multi-player soul link propagation for manually added Pokemon.
            if route_number is not None:
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        """SELECT e.encounter_id
                           FROM encounters e
                           JOIN routes r ON e.route_id = r.route_id
                           WHERE e.player_id = ? AND r.run_id = ? AND LOWER(r.route_number) = LOWER(?)""",
                        (player_id, player[1], route_number)
                    ) as cursor:
                        encounter = await cursor.fetchone()

                if not encounter:
                    embed = create_embed(
                        "❌ Missing Encounter",
                        f"No encounter found for player {player_id} on route {route_number}. "
                        "Record the encounter first with `/record_encounter`, then retry.",
                        discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

            # Add Pokemon to team
            member_id = await db_utils.add_team_member(
                player_id,
                pokemon_name,
                pokemon_type,
                level,
                is_starter,
                route_number
            )

            embed = create_embed(
                "✅ Pokemon Added",
                f"**{pokemon_name}** (Level {level}, Type: {pokemon_type}){' - Starter!' if is_starter else ''}",
                discord.Color.green()
            )
            embed.add_field(name="Member ID", value=member_id, inline=False)
            if route_number is not None:
                embed.add_field(
                    name="🔗 Soul Link Route",
                    value=f"Linked to route {route_number} encounter group (if linked encounters exist).",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="view_team", description="View a player's current team")
    @app_commands.describe(
        player_id="Player ID to view"
    )
    async def view_team(self, interaction: discord.Interaction, player_id: int):
        """View a player's team."""
        try:
            await interaction.response.defer()

            # Get player info
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM run_players WHERE player_id = ?",
                    (player_id,)
                ) as cursor:
                    player = await cursor.fetchone()

            if not player:
                embed = create_embed("❌ Error", f"Player with ID {player_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get team
            async with aiosqlite.connect(DATABASE_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM team_members WHERE player_id = ? ORDER BY status DESC, member_id",
                    (player_id,)
                ) as cursor:
                    team = await cursor.fetchall()

            embed = create_embed(
                f"🎮 {player[3]}'s Team",
                f"Deaths: {player[5]} | Status: {player[6]}",
                discord.Color.blue()
            )

            if not team:
                embed.add_field(name="Team", value="No Pokemon yet", inline=False)
                await interaction.followup.send(embed=embed)
                return

            # Separate Pokemon by status
            active_pokemon = []
            boxed_pokemon = []
            fainted_pokemon = []
            released_pokemon = []

            for mon in team:
                if mon['status'] == 'ACTIVE':
                    active_pokemon.append(mon)
                elif mon['status'] == 'BOXED':
                    boxed_pokemon.append(mon)
                elif mon['status'] == 'FAINTED':
                    fainted_pokemon.append(mon)
                elif mon['status'] == 'RELEASED':
                    released_pokemon.append(mon)

            # Build team info
            team_info = ""

            # Active Pokemon
            if active_pokemon:
                team_info += "**✅ Active Team:**\n"
                for mon in active_pokemon:
                    team_info += f"✅ **{mon['pokemon_name']}** (Lvl {mon['level']}, {mon['pokemon_type']}) - ID: {mon['member_id']}\n"

            # Boxed Pokemon
            if boxed_pokemon:
                team_info += "\n**📦 Boxed:**\n"
                for mon in boxed_pokemon:
                    team_info += f"📦 **{mon['pokemon_name']}** (Lvl {mon['level']}, {mon['pokemon_type']}) - ID: {mon['member_id']}\n"

            # Fainted Pokemon
            if fainted_pokemon:
                team_info += "\n**💀 Fainted:**\n"
                for mon in fainted_pokemon:
                    team_info += f"💀 **{mon['pokemon_name']}** (Lvl {mon['level']}, {mon['pokemon_type']}) - ID: {mon['member_id']}\n"

            # Released Pokemon
            if released_pokemon:
                team_info += "\n**🚀 Released:**\n"
                for mon in released_pokemon:
                    team_info += f"🚀 **{mon['pokemon_name']}** (Lvl {mon['level']}, {mon['pokemon_type']}) - ID: {mon['member_id']}\n"

            embed.add_field(name=f"All Pokemon ({len(active_pokemon)} active)", value=team_info, inline=False)
            embed.add_field(
                name="📝 How to Manage Pokemon",
                value="Use the Member ID (shown after each Pokemon) with:\n`/faint_pokemon member_id:X`\n`/box_pokemon member_id:X`\n`/unbox_pokemon member_id:X`\n`/release_pokemon member_id:X`",
                inline=False
            )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="faint_pokemon", description="Mark a Pokemon as fainted")
    @app_commands.describe(
        member_id="Member ID of the Pokemon"
    )
    async def faint_pokemon(self, interaction: discord.Interaction, member_id: int):
        """Mark a Pokemon as fainted."""
        try:
            await interaction.response.defer()

            # Get member info
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM team_members WHERE member_id = ?",
                    (member_id,)
                ) as cursor:
                    member = await cursor.fetchone()

                if not member:
                    embed = create_embed("❌ Error", f"Pokemon with ID {member_id} not found", discord.Color.red())
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                # Verify ownership
                async with db.execute(
                    "SELECT user_id FROM run_players WHERE player_id = ?",
                    (member[1],)
                ) as cursor:
                    player = await cursor.fetchone()

                if player[0] != interaction.user.id:
                    embed = create_embed("❌ Error", "This Pokemon doesn't belong to you", discord.Color.red())
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

            # Get all linked Pokemon before fainting (to track them for the response)
            linked_pokemon_info = ""
            route_encountered = member[8]  # route_encountered is at index 8

            if route_encountered:
                # Get all Pokemon on the same route from other players (3+ player mode)
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        """SELECT DISTINCT tm.member_id, tm.pokemon_name, rp.player_id FROM team_members tm
                           JOIN encounters e ON e.pokemon_name = tm.pokemon_name
                           JOIN routes r ON e.route_id = r.route_id
                           WHERE LOWER(r.route_number) = LOWER(?) AND r.run_id = (SELECT run_id FROM run_players WHERE player_id = ?)
                           AND tm.player_id != ? AND tm.status != 'FAINTED'""",
                        (route_encountered, member[1], member[1])
                    ) as cursor:
                        linked_members = await cursor.fetchall()

                    for linked_mon in linked_members:
                        linked_pokemon_info += f"• **{linked_mon['pokemon_name']}**\n"

            # Also check for old 2-player style linked_member_id (for backward compatibility)
            if member[10]:  # linked_member_id is at index 10
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        "SELECT * FROM team_members WHERE member_id = ?",
                        (member[10],)
                    ) as cursor:
                        linked_member = await cursor.fetchone()
                    
                    if linked_member and linked_member[6] != 'FAINTED':
                        if f"• **{linked_member[2]}**\n" not in linked_pokemon_info:
                            linked_pokemon_info += f"• **{linked_member[2]}**\n"

            # Faint Pokemon (and all linked ones)
            await db_utils.faints_pokemon(member_id)

            # Update death count for current player
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute(
                    "UPDATE run_players SET deaths = deaths + 1 WHERE player_id = ?",
                    (member[1],)
                )

                # Update death counts for all linked players
                if route_encountered:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        """SELECT DISTINCT rp.player_id FROM team_members tm
                           JOIN encounters e ON e.pokemon_name = tm.pokemon_name
                           JOIN routes r ON e.route_id = r.route_id
                           JOIN run_players rp ON rp.player_id = tm.player_id
                           WHERE LOWER(r.route_number) = LOWER(?) AND r.run_id = (SELECT run_id FROM run_players WHERE player_id = ?)
                           AND tm.player_id != ?""",
                        (route_encountered, member[1], member[1])
                    ) as cursor:
                        linked_players = await cursor.fetchall()

                    for linked_player in linked_players:
                        await db.execute(
                            "UPDATE run_players SET deaths = deaths + 1 WHERE player_id = ?",
                            (linked_player['player_id'],)
                        )

                # Handle 2-player mode backward compatibility
                if member[10]:
                    async with db.execute(
                        "SELECT player_id FROM team_members WHERE member_id = ?",
                        (member[10],)
                    ) as cursor:
                        linked_result = await cursor.fetchone()
                        if linked_result:
                            await db.execute(
                                "UPDATE run_players SET deaths = deaths + 1 WHERE player_id = ?",
                                (linked_result[0],)
                            )

                await db.commit()

            # Get run_id for logging
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT run_id FROM run_players WHERE player_id = ?",
                    (member[1],)
                ) as cursor:
                    run_result = await cursor.fetchone()
                    run_id = run_result[0] if run_result else None

            # Log faint
            if run_id:
                await logging_utils.log_event(
                    run_id,
                    "POKEMON_FAINTED",
                    f"{member[2]} fainted",
                    {"pokemon": member[2], "player_id": member[1]}
                )

            embed = create_embed(
                "💀 Pokemon Fainted",
                f"**{member[2]}** has fainted",
                discord.Color.orange()
            )

            if linked_pokemon_info:
                embed.add_field(
                    name="⚠️ Soul Link",
                    value=f"Linked Pokemon also fainted:\n{linked_pokemon_info.strip()}",
                    inline=False
                )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="box_pokemon", description="Box a Pokemon")
    @app_commands.describe(
        member_id="Member ID of the Pokemon"
    )
    async def box_pokemon(self, interaction: discord.Interaction, member_id: int):
        """Box a Pokemon."""
        try:
            # Get member info
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM team_members WHERE member_id = ?",
                    (member_id,)
                ) as cursor:
                    member = await cursor.fetchone()

                if not member:
                    embed = create_embed("❌ Error", f"Pokemon with ID {member_id} not found", discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Verify ownership
                async with db.execute(
                    "SELECT user_id FROM run_players WHERE player_id = ?",
                    (member[1],)
                ) as cursor:
                    player = await cursor.fetchone()

                if player[0] != interaction.user.id:
                    embed = create_embed("❌ Error", "This Pokemon doesn't belong to you", discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

            # Get all linked Pokemon before boxing (to track them for the response)
            linked_pokemon_info = ""
            route_encountered = member[8]  # route_encountered is at index 8

            if route_encountered:
                # Get all Pokemon on the same route from other players (3+ player mode)
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        """SELECT DISTINCT tm.member_id, tm.pokemon_name FROM team_members tm
                           JOIN encounters e ON e.pokemon_name = tm.pokemon_name
                           JOIN routes r ON e.route_id = r.route_id
                           WHERE LOWER(r.route_number) = LOWER(?) AND r.run_id = (SELECT run_id FROM run_players WHERE player_id = ?)
                           AND tm.player_id != ? AND tm.status != 'BOXED'""",
                        (route_encountered, member[1], member[1])
                    ) as cursor:
                        linked_members = await cursor.fetchall()

                    for linked_mon in linked_members:
                        linked_pokemon_info += f"• **{linked_mon['pokemon_name']}**\n"

            # Also check for old 2-player style linked_member_id (for backward compatibility)
            if member[10]:  # linked_member_id is at index 10
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        "SELECT pokemon_name FROM team_members WHERE member_id = ?",
                        (member[10],)
                    ) as cursor:
                        linked_result = await cursor.fetchone()
                        if linked_result and f"• **{linked_result[0]}**\n" not in linked_pokemon_info:
                            linked_pokemon_info += f"• **{linked_result[0]}**\n"

            # Box Pokemon (and all linked ones)
            await db_utils.box_pokemon(member_id)

            # Get run_id for logging
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT run_id FROM run_players WHERE player_id = ?",
                    (member[1],)
                ) as cursor:
                    run_result = await cursor.fetchone()
                    run_id = run_result[0] if run_result else None

            # Log box
            if run_id:
                await logging_utils.log_event(
                    run_id,
                    "POKEMON_BOXED",
                    f"{member[2]} was boxed",
                    {"pokemon": member[2], "player_id": member[1]}
                )

            embed = create_embed(
                "📦 Pokemon Boxed",
                f"**{member[2]}** has been boxed",
                discord.Color.green()
            )

            if linked_pokemon_info:
                embed.add_field(
                    name="⚠️ Soul Link",
                    value=f"Linked Pokemon also boxed:\n{linked_pokemon_info.strip()}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="release_pokemon", description="Release a Pokemon")
    @app_commands.describe(
        member_id="Member ID of the Pokemon"
    )
    async def release_pokemon(self, interaction: discord.Interaction, member_id: int):
        """Release a Pokemon."""
        try:
            # Get member info
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM team_members WHERE member_id = ?",
                    (member_id,)
                ) as cursor:
                    member = await cursor.fetchone()

                if not member:
                    embed = create_embed("❌ Error", f"Pokemon with ID {member_id} not found", discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Verify ownership
                async with db.execute(
                    "SELECT user_id FROM run_players WHERE player_id = ?",
                    (member[1],)
                ) as cursor:
                    player = await cursor.fetchone()

                if player[0] != interaction.user.id:
                    embed = create_embed("❌ Error", "This Pokemon doesn't belong to you", discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

            # Get all linked Pokemon before releasing (to track them for the response)
            linked_pokemon_info = ""
            route_encountered = member[8]  # route_encountered is at index 8

            if route_encountered:
                # Get all Pokemon on the same route from other players (3+ player mode)
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        """SELECT DISTINCT tm.member_id, tm.pokemon_name FROM team_members tm
                           JOIN encounters e ON e.pokemon_name = tm.pokemon_name
                           JOIN routes r ON e.route_id = r.route_id
                           WHERE LOWER(r.route_number) = LOWER(?) AND r.run_id = (SELECT run_id FROM run_players WHERE player_id = ?)
                           AND tm.player_id != ? AND tm.status != 'RELEASED'""",
                        (route_encountered, member[1], member[1])
                    ) as cursor:
                        linked_members = await cursor.fetchall()

                    for linked_mon in linked_members:
                        linked_pokemon_info += f"• **{linked_mon['pokemon_name']}**\n"

            # Also check for old 2-player style linked_member_id (for backward compatibility)
            if member[10]:  # linked_member_id is at index 10
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        "SELECT pokemon_name FROM team_members WHERE member_id = ?",
                        (member[10],)
                    ) as cursor:
                        linked_result = await cursor.fetchone()
                        if linked_result and f"• **{linked_result[0]}**\n" not in linked_pokemon_info:
                            linked_pokemon_info += f"• **{linked_result[0]}**\n"

            # Release Pokemon (and all linked ones)
            await db_utils.release_pokemon(member_id)

            # Get run_id for logging
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT run_id FROM run_players WHERE player_id = ?",
                    (member[1],)
                ) as cursor:
                    run_result = await cursor.fetchone()
                    run_id = run_result[0] if run_result else None

            # Log release
            if run_id:
                await logging_utils.log_event(
                    run_id,
                    "POKEMON_RELEASED",
                    f"{member[2]} was released",
                    {"pokemon": member[2], "player_id": member[1]}
                )

            embed = create_embed(
                "🚀 Pokemon Released",
                f"**{member[2]}** has been released",
                discord.Color.purple()
            )

            if linked_pokemon_info:
                embed.add_field(
                    name="⚠️ Soul Link",
                    value=f"Linked Pokemon also released:\n{linked_pokemon_info.strip()}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unbox_pokemon", description="Unbox a Pokemon")
    @app_commands.describe(
        member_id="Member ID of the Pokemon"
    )
    async def unbox_pokemon(self, interaction: discord.Interaction, member_id: int):
        """Unbox a Pokemon (return to team)."""
        try:
            # Get member info
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT * FROM team_members WHERE member_id = ?",
                    (member_id,)
                ) as cursor:
                    member = await cursor.fetchone()

                if not member:
                    embed = create_embed("❌ Error", f"Pokemon with ID {member_id} not found", discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Verify ownership
                async with db.execute(
                    "SELECT user_id FROM run_players WHERE player_id = ?",
                    (member[1],)
                ) as cursor:
                    player = await cursor.fetchone()

                if player[0] != interaction.user.id:
                    embed = create_embed("❌ Error", "This Pokemon doesn't belong to you", discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

            # Unbox Pokemon
            await db_utils.unbox_pokemon(member_id)

            # Get run_id for logging
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT run_id FROM run_players WHERE player_id = ?",
                    (member[1],)
                ) as cursor:
                    run_result = await cursor.fetchone()
                    run_id = run_result[0] if run_result else None

            # Log unbox
            if run_id:
                await logging_utils.log_event(
                    run_id,
                    "POKEMON_UNBOXED",
                    f"{member[2]} was unboxed",
                    {"pokemon": member[2], "player_id": member[1]}
                )

            embed = create_embed(
                "📦 Pokemon Unboxed",
                f"**{member[2]}** has been unboxed and returned to your team",
                discord.Color.blue()
            )

            # Check for linked Pokemon (both 2-player and 3+ player modes)
            route_encountered = member[8]  # route_encountered is at index 8
            linked_pokemon_info = ""

            if route_encountered:
                # Get all Pokemon on the same route from other players
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        """SELECT DISTINCT tm.member_id, tm.pokemon_name FROM team_members tm
                           JOIN encounters e ON e.pokemon_name = tm.pokemon_name
                           JOIN routes r ON e.route_id = r.route_id
                           WHERE LOWER(r.route_number) = LOWER(?) AND r.run_id = (SELECT run_id FROM run_players WHERE player_id = ?)
                           AND tm.player_id != ? AND tm.status = 'BOXED'""",
                        (route_encountered, member[1], member[1])
                    ) as cursor:
                        linked_members = await cursor.fetchall()

                # Unbox all linked Pokemon
                for linked_mon in linked_members:
                    await db_utils.unbox_pokemon(linked_mon['member_id'])
                    linked_pokemon_info += f"• **{linked_mon['pokemon_name']}**\n"

            # Also check for old 2-player style linked_member_id (for backward compatibility)
            if member[10]:  # linked_member_id is at index 10
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        "SELECT pokemon_name FROM team_members WHERE member_id = ?",
                        (member[10],)
                    ) as cursor:
                        linked_result = await cursor.fetchone()
                        if linked_result and f"• **{linked_result[0]}**\n" not in linked_pokemon_info:
                            linked_pokemon_info += f"• **{linked_result[0]}**\n"

            if linked_pokemon_info:
                embed.add_field(
                    name="⚠️ Soul Link",
                    value=f"Linked Pokemon also unboxed:\n{linked_pokemon_info.strip()}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TeamManagement(bot))

