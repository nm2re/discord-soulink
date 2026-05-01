import discord
from discord.ext import commands
from discord import app_commands

class HelpCommands(commands.Cog):
    """Help and information commands."""

    def __init__(self, bot):
        self.bot = bot

        self.commands_list = {
            "Run Management": {
                "/create_run": {
                    "description": "Create a new Nuzlocke run",
                    "usage": '/create_run run_name:"Name" game_name:"Game" num_players:2 clauses:"type_restriction,shiny"',
                    "parameters": [
                        ("run_name", "Name for the run (required)"),
                        ("game_name", "Pokemon game being played (required)"),
                        ("num_players", "Number of players 1-4 (required)"),
                        ("clauses", "Comma-separated clauses: duplicate, shiny, gift, species, type_restriction (optional)")
                    ]
                },
                "/join_run": {
                    "description": "Join an existing Nuzlocke run",
                    "usage": "/join_run run_id:1",
                    "parameters": [
                        ("run_id", "The ID of the run to join (required)")
                    ]
                },
                "/list_runs": {
                    "description": "List all active Nuzlocke runs in this server",
                    "usage": "/list_runs",
                    "parameters": []
                },
                "/run_status": {
                    "description": "Get detailed status of a specific run",
                    "usage": "/run_status run_id:1",
                    "parameters": [
                        ("run_id", "The ID of the run to check (required)")
                    ]
                },
                "/end_run": {
                    "description": "Complete/End a Nuzlocke run",
                    "usage": "/end_run run_id:1",
                    "parameters": [
                        ("run_id", "The ID of the run to end (required)")
                    ],
                    "note": "Marks the run as COMPLETED but keeps all data preserved"
                },
                "/delete_run": {
                    "description": "Permanently delete a Nuzlocke run",
                    "usage": '/delete_run run_id:1 confirm:yes',
                    "parameters": [
                        ("run_id", "The ID of the run to delete (required)"),
                        ("confirm", "Type 'yes' to confirm deletion (required for actual deletion)")
                    ],
                    "note": "⚠️ PERMANENT! This deletes all associated data (players, routes, Pokemon, etc.). First run without confirm:yes to see the confirmation prompt."
                }
            },
            "Route Management": {
                # "/add_route": {
                #     "description": "Add a route to a run (optional - routes are auto-created by record_encounter)",
                #     "usage": '/add_route run_id:1 route_number:1 route_name:"Route 1"',
                #     "parameters": [
                #         ("run_id", "The run to add the route to (required)"),
                #         ("route_number", "Route number like 1, 2, 3, etc. (required)"),
                #         ("route_name", "Optional name for the route (optional)")
                #     ],
                #     "note": "ℹ️ Routes are automatically created when you use /record_encounter, so this is optional"
                # },
                "/list_routes": {
                    "description": "List all routes in a run",
                    "usage": "/list_routes run_id:1",
                    "parameters": [
                        ("run_id", "The run ID (required)")
                    ],
                    "note": "📋 Shows all routes in a run with encounter counts"
                },
                "/record_encounter": {
                    "description": "Record a Pokemon encounter and automatically add it to the team and link it with other encounters on the same route",
                    "usage": '/record_encounter run_id:1 route_number:1 player_id:1 pokemon_name:"Pidgeot" pokemon_type:"Flying" level:5',
                    "parameters": [
                        ("run_id", "The run ID (required)"),
                        ("route_number", "Route number (auto-creates route if not exists) (required)"),
                        ("player_id", "Player ID making the encounter (required)"),
                        ("pokemon_name", "Name/species of the Pokemon (required)"),
                        ("pokemon_type", "Primary type of the Pokemon (optional)"),
                        ("level", "Pokemon level, default 1 (optional)")
                    ],
                    "note": "✅ This command automatically: creates the route, records the encounter, adds Pokemon to team, and links it with other encounters on the same route! If 2+ players have encounters on the route, they are instantly soul linked."
                },
                "/view_route": {
                    "description": "View all encounters on a specific route",
                    "usage": "/view_route route_id:1",
                    "parameters": [
                        ("route_id", "The route ID to view (required)")
                    ]
                },
                "/view_encounters": {
                    "description": "View all routes and encounters in a run",
                    "usage": "/view_encounters run_id:1",
                    "parameters": [
                        ("run_id", "The run ID to view (required)")
                    ]
                }
            },
            "Team Management": {
                "/add_pokemon": {
                    "description": "Manually add a Pokemon to a player's team (rarely needed - use /record_encounter instead)",
                    "usage": '/add_pokemon player_id:1 pokemon_name:"Charizard" pokemon_type:"Fire" level:25 is_starter:true',
                    "parameters": [
                        ("player_id", "Your player ID (required)"),
                        ("pokemon_name", "Name of the Pokemon (required)"),
                        ("pokemon_type", "Primary type of the Pokemon (required)"),
                        ("level", "Level of the Pokemon, default 1 (optional)"),
                        ("is_starter", "Is this your starter? true/false, default false (optional)")
                    ],
                    "note": "ℹ️ Most of the time, use /record_encounter instead - it automatically adds Pokemon to your team!"
                },
                "/view_team": {
                    "description": "View a player's complete Pokemon team (active, boxed, fainted, released)",
                    "usage": "/view_team player_id:1",
                    "parameters": [
                        ("player_id", "Player ID to view (required)")
                    ]
                },
                "/faint_pokemon": {
                    "description": "Mark a Pokemon as fainted (dead)",
                    "usage": "/faint_pokemon member_id:1",
                    "parameters": [
                        ("member_id", "Member ID of the Pokemon (required)")
                    ],
                    "note": "⚠️ If Soul Linked, the partner Pokemon also faints!"
                },
                "/box_pokemon": {
                    "description": "Box a Pokemon (temporarily remove from team)",
                    "usage": "/box_pokemon member_id:1",
                    "parameters": [
                        ("member_id", "Member ID of the Pokemon (required)")
                    ],
                    "note": "⚠️ If Soul Linked, the partner Pokemon is also boxed!"
                },
                "/unbox_pokemon": {
                    "description": "Unbox a Pokemon (return to active team)",
                    "usage": "/unbox_pokemon member_id:1",
                    "parameters": [
                        ("member_id", "Member ID of the Pokemon (required)")
                    ],
                    "note": "⚠️ If Soul Linked, the partner Pokemon is also unboxed!"
                },
                "/release_pokemon": {
                    "description": "Release a Pokemon permanently",
                    "usage": "/release_pokemon member_id:1",
                    "parameters": [
                        ("member_id", "Member ID of the Pokemon (required)")
                    ],
                    "note": "⚠️ If Soul Linked, the partner Pokemon is also released!"
                }
            },
            "Soul Link": {
                "/link_pokemon": {
                    "description": "Manually link Pokemon encounters on a route as Soul Link partners",
                    "usage": "/link_pokemon run_id:1 route_number:1",
                    "parameters": [
                        ("run_id", "The run ID (required for route linking)"),
                        ("route_number", "Route number to link, e.g., 1 for Route 1 (required for route linking)")
                    ],
                    "note": "ℹ️ Most of the time you don't need this! Pokemon on the same route are automatically linked when they're recorded with /record_encounter. Use this only for manual linking of specific encounters."
                },
                "/soul_link_status": {
                    "description": "View all Soul Link pairs in a run",
                    "usage": "/soul_link_status run_id:1",
                    "parameters": [
                        ("run_id", "The run ID (required)")
                    ]
                },
                "/check_run_health": {
                    "description": "Check overall health of a run",
                    "usage": "/check_run_health run_id:1",
                    "parameters": [
                        ("run_id", "The run ID (required)")
                    ]
                },
                "/rules_check": {
                    "description": "Check if teams follow Soul Link rules",
                    "usage": '/rules_check run_id:1 clause:"type_restriction"',
                    "parameters": [
                        ("run_id", "The run ID (required)"),
                        ("clause", "Clause to check: type_restriction (optional, default: type_restriction)")
                    ]
                }
            },
            "Info": {
                "/about": {
                    "description": "Show bot information and features",
                    "usage": "/about",
                    "parameters": []
                }
            }
        }

    @app_commands.command(name="help", description="Show all available commands")
    @app_commands.describe(
        command="Optional: Get detailed help for a specific command"
    )
    async def help_command(self, interaction: discord.Interaction, command: str = ""):
        """Show help information for all commands or a specific command."""

        if command:
            # Show help for specific command
            command_name = command if command.startswith("/") else f"/{command}"
            found = False

            for category, cmds in self.commands_list.items():
                if command_name in cmds:
                    cmd_info = cmds[command_name]

                    embed = discord.Embed(
                        title=f"📖 Help for {command_name}",
                        description=cmd_info.get("description", ""),
                        color=discord.Color.blue()
                    )

                    embed.add_field(name="Category", value=category, inline=False)
                    embed.add_field(name="Usage", value=f"`{cmd_info.get('usage', 'N/A')}`", inline=False)

                    if cmd_info.get("parameters"):
                        params_text = ""
                        for param_name, param_desc in cmd_info["parameters"]:
                            params_text += f"**{param_name}**: {param_desc}\n"
                        embed.add_field(name="Parameters", value=params_text, inline=False)

                    if cmd_info.get("note"):
                        embed.add_field(name="Note", value=cmd_info["note"], inline=False)

                    await interaction.response.send_message(embed=embed)
                    found = True
                    break

            if not found:
                embed = discord.Embed(
                    title="❌ Command Not Found",
                    description=f"Command `{command_name}` not found. Use `/help` to see all commands.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show all commands
            await interaction.response.defer()

            embed = discord.Embed(
                title="📚 Complete Command Reference",
                description="All available commands for the Nuzlocke Soul Link Bot",
                color=discord.Color.purple()
            )

            for category, cmds in self.commands_list.items():
                commands_text = ""
                for cmd_name, cmd_info in cmds.items():
                    commands_text += f"**{cmd_name}** - {cmd_info.get('description', 'N/A')}\n"

                embed.add_field(name=category, value=commands_text, inline=False)

            embed.add_field(
                name="💡 Getting More Help",
                value="Use `/help <command_name>` to get detailed information about a specific command.\n\nExample: `/help create_run` or `/help /create_run`",
                inline=False
            )

            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))

