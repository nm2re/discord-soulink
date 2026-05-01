import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from config import DATABASE_PATH, POKEMON_TYPES
from utils import create_embed
import database as db_utils

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
        is_starter="Is this your starter?"
    )
    async def add_pokemon(self, interaction: discord.Interaction, player_id: int, pokemon_name: str,
                         pokemon_type: str, level: int = 1, is_starter: bool = False):
        """Add a Pokemon to a player's team."""
        try:
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

            # Add Pokemon to team
            member_id = await db_utils.add_team_member(
                player_id,
                pokemon_name,
                pokemon_type,
                level,
                is_starter
            )

            embed = create_embed(
                "✅ Pokemon Added",
                f"**{pokemon_name}** (Level {level}, Type: {pokemon_type}){'- Starter!' if is_starter else ''}",
                discord.Color.green()
            )
            embed.add_field(name="Member ID", value=member_id, inline=False)

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

            # Faint Pokemon
            await db_utils.faints_pokemon(member_id)

            # Update death count for current player
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute(
                    "UPDATE run_players SET deaths = deaths + 1 WHERE player_id = ?",
                    (member[1],)
                )
                await db.commit()

            embed = create_embed(
                "💀 Pokemon Fainted",
                f"**{member[2]}** has fainted",
                discord.Color.orange()
            )

            # Check if linked and update linked player's death count
            linked_pokemon_name = None
            if member[10]:  # linked_member_id is at index 10
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    # Get linked Pokemon info
                    async with db.execute(
                        "SELECT * FROM team_members WHERE member_id = ?",
                        (member[10],)
                    ) as cursor:
                        linked_member = await cursor.fetchone()
                    
                    if linked_member:
                        linked_pokemon_name = linked_member[2]  # pokemon_name
                        # Update linked player's death count
                        await db.execute(
                            "UPDATE run_players SET deaths = deaths + 1 WHERE player_id = ?",
                            (linked_member[1],)  # linked member's player_id
                        )
                        await db.commit()
                
                if linked_pokemon_name:
                    embed.add_field(
                        name="⚠️ Soul Link",
                        value=f"Linked Pokemon **{linked_pokemon_name}** has also fainted!",
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

             # Box Pokemon
            await db_utils.box_pokemon(member_id)

            embed = create_embed(
                "📦 Pokemon Boxed",
                f"**{member[2]}** has been boxed",
                discord.Color.green()
            )

            # Check if linked and show linked Pokemon name
            if member[10]:  # linked_member_id is at index 10
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        "SELECT pokemon_name FROM team_members WHERE member_id = ?",
                        (member[10],)
                    ) as cursor:
                        linked_result = await cursor.fetchone()
                        if linked_result:
                            linked_pokemon_name = linked_result[0]
                            embed.add_field(
                                name="⚠️ Soul Link",
                                value=f"Linked Pokemon **{linked_pokemon_name}** has also been boxed!",
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

              # Release Pokemon
            await db_utils.release_pokemon(member_id)

            embed = create_embed(
                "🚀 Pokemon Released",
                f"**{member[2]}** has been released",
                discord.Color.purple()
            )

            # Check if linked and show linked Pokemon name
            if member[10]:  # linked_member_id is at index 10
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        "SELECT pokemon_name FROM team_members WHERE member_id = ?",
                        (member[10],)
                    ) as cursor:
                        linked_result = await cursor.fetchone()
                        if linked_result:
                            linked_pokemon_name = linked_result[0]
                            embed.add_field(
                                name="⚠️ Soul Link",
                                value=f"Linked Pokemon **{linked_pokemon_name}** has also been released!",
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

            embed = create_embed(
                "📦 Pokemon Unboxed",
                f"**{member[2]}** has been unboxed and returned to your team",
                discord.Color.blue()
            )

            # Check if linked and show linked Pokemon name
            if member[10]:  # linked_member_id is at index 10
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    async with db.execute(
                        "SELECT pokemon_name FROM team_members WHERE member_id = ?",
                        (member[10],)
                    ) as cursor:
                        linked_result = await cursor.fetchone()
                        if linked_result:
                            linked_pokemon_name = linked_result[0]
                            embed.add_field(
                                name="⚠️ Soul Link",
                                value=f"Linked Pokemon **{linked_pokemon_name}** has also been unboxed!",
                                inline=False
                            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TeamManagement(bot))

