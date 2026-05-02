import discord
from discord.ext import commands
from discord import app_commands

class HelpCommands(commands.Cog):
    """Help and information commands."""

    def __init__(self, bot):
        self.bot = bot

        # Main commands for quick help
        self.main_commands = {
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
            "/record_encounter": {
                "description": "Record a Pokemon encounter and automatically add it to the team and link it with other encounters on the same route",
                "usage": '/record_encounter run_id:1 route_number:"New Bark Town" player_id:1 pokemon_name:"Pidgeot" pokemon_type:"Flying" level:5',
                "parameters": [
                    ("run_id", "The run ID (required)"),
                    ("route_number", "Route identifier (number or name; auto-creates route if missing) (required)"),
                    ("player_id", "Player ID making the encounter (required)"),
                    ("pokemon_name", "Name/species of the Pokemon (required)"),
                    ("pokemon_type", "Primary type of the Pokemon (optional)"),
                    ("level", "Pokemon level, default 1 (optional)")
                ],
                "note": "✅ This command automatically: creates the route, records the encounter, adds Pokemon to team, and links it with other encounters on the same route! If 2+ players have encounters on the route, they are instantly soul linked."
            },
            "/faint_pokemon": {
                "description": "Mark a Pokemon as fainted (dead)",
                "usage": "/faint_pokemon member_id:1",
                "parameters": [
                    ("member_id", "Member ID of the Pokemon (required)")
                ],
                "note": "⚠️ If Soul Linked, all linked Pokemon also faint!"
            },
            "/box_pokemon": {
                "description": "Box a Pokemon (temporarily remove from team)",
                "usage": "/box_pokemon member_id:1",
                "parameters": [
                    ("member_id", "Member ID of the Pokemon (required)")
                ],
                "note": "⚠️ If Soul Linked, all linked Pokemon are also boxed!"
            },
            "/unbox_pokemon": {
                "description": "Unbox a Pokemon (return to active team)",
                "usage": "/unbox_pokemon member_id:1",
                "parameters": [
                    ("member_id", "Member ID of the Pokemon (required)")
                ],
                "note": "⚠️ If Soul Linked, all linked Pokemon are also unboxed!"
            },
            "/view_team": {
                "description": "View a player's complete Pokemon team (active, boxed, fainted, released)",
                "usage": "/view_team player_id:1",
                "parameters": [
                    ("player_id", "Player ID to view (required)")
                ]
            },
            "/run_status": {
                "description": "Get detailed status of a specific run",
                "usage": "/run_status run_id:1",
                "parameters": [
                    ("run_id", "The ID of the run to check (required)")
                ]
            },
        }

        # Full commands list organized by category
        self.full_commands = {
            "📚 Run Management": {
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

            "📚 Route Management": {
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
                    "usage": '/record_encounter run_id:1 route_number:"New Bark Town" player_id:1 pokemon_name:"Pidgeot" pokemon_type:"Flying" level:5',
                    "parameters": [
                        ("run_id", "The run ID (required)"),
                        ("route_number", "Route identifier (number or name; auto-creates route if missing) (required)"),
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

            "📚 Team Management": {
                "/add_pokemon": {
                    "description": "Manually add a Pokemon to a player's team (useful for gifts/static encounters)",
                    "usage": '/add_pokemon player_id:1 pokemon_name:"Charizard" pokemon_type:"Fire" level:25 is_starter:true route_number:"New Bark Town"',
                    "parameters": [
                        ("player_id", "Your player ID (required)"),
                        ("pokemon_name", "Name of the Pokemon (required)"),
                        ("pokemon_type", "Primary type of the Pokemon (required)"),
                        ("level", "Level of the Pokemon, default 1 (optional)"),
                        ("is_starter", "Is this your starter? true/false, default false (optional)"),
                        ("route_number", "Optional route identifier (number or name) to attach encounter-based soul link behavior")
                    ],
                    "note": "ℹ️ Use this for non-route encounters (gifts, statics, etc.). Then link manually with `/link_pokemon member_id_1:X member_id_2:Y`."
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
                    "note": "⚠️ If Soul Linked, all linked Pokemon also faint!"
                },
                "/box_pokemon": {
                    "description": "Box a Pokemon (temporarily remove from team)",
                    "usage": "/box_pokemon member_id:1",
                    "parameters": [
                        ("member_id", "Member ID of the Pokemon (required)")
                    ],
                    "note": "⚠️ If Soul Linked, all linked Pokemon are also boxed!"
                },
                "/unbox_pokemon": {
                    "description": "Unbox a Pokemon (return to active team)",
                    "usage": "/unbox_pokemon member_id:1",
                    "parameters": [
                        ("member_id", "Member ID of the Pokemon (required)")
                    ],
                    "note": "⚠️ If Soul Linked, all linked Pokemon are also unboxed!"
                },
                "/release_pokemon": {
                    "description": "Release a Pokemon permanently",
                    "usage": "/release_pokemon member_id:1",
                    "parameters": [
                        ("member_id", "Member ID of the Pokemon (required)")
                    ],
                    "note": "⚠️ If Soul Linked, all linked Pokemon are also released!"
                }
            },

            "📚 Soul Link": {
                "/link_pokemon": {
                    "description": "Manually link by route, encounter IDs, or team member IDs",
                    "usage": '/link_pokemon member_id_1:4001 member_id_2:4002',
                    "parameters": [
                        ("run_id", "The run ID (required for route linking)"),
                        ("route_number", "Route identifier to link, e.g., 1 or New Bark Town (for route mode)"),
                        ("encounter_id_1", "First encounter ID (for encounter mode)"),
                        ("encounter_id_2", "Second encounter ID (for encounter mode)"),
                        ("member_id_1", "First team member ID (for manual /add_pokemon mode)"),
                        ("member_id_2", "Second team member ID (for manual /add_pokemon mode)")
                    ],
                    "note": "ℹ️ Route encounters auto-link with /record_encounter. Use member_id mode for gifts/statics added through /add_pokemon."
                },
                "/soul_link_status": {
                    "description": "View all Soul Link groups in a run",
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

            "📚 Logging & Info": {
                "/run_log": {
                    "description": "View the activity log for a run",
                    "usage": "/run_log run_id:1 limit:15",
                    "parameters": [
                        ("run_id", "The run ID to view logs for (required)"),
                        ("limit", "Number of recent events to show (default: 15, max: 50)")
                    ],
                    "note": "📋 Shows a clean formatted log of all events in the run organized by timestamp"
                },
                "/export_run_log": {
                    "description": "Export run activity log as a downloadable text file",
                    "usage": "/export_run_log run_id:1",
                    "parameters": [
                        ("run_id", "The run ID to export logs for (required)")
                    ],
                    "note": "📥 Downloads a clean, formatted text file with the complete run history"
                }
            }
        }

    @app_commands.command(name="help", description="Show main Soul Link commands")
    @app_commands.describe(
        command="Optional: Get detailed help for a specific command"
    )
    async def help_command(self, interaction: discord.Interaction, command: str = ""):
        """Show help for main Soul Link commands."""

        if command:
            # Show help for specific command
            command_name = command if command.startswith("/") else f"/{command}"

            if command_name in self.main_commands:
                cmd_info = self.main_commands[command_name]
                embed = discord.Embed(
                    title=f"📖 Help for {command_name}",
                    description=cmd_info.get("description", ""),
                    color=discord.Color.blue()
                )

                embed.add_field(name="Usage", value=f"`{cmd_info.get('usage', 'N/A')}`", inline=False)

                if cmd_info.get("parameters"):
                    params_text = ""
                    for param_name, param_desc in cmd_info["parameters"]:
                        params_text += f"**{param_name}**: {param_desc}\n"
                    embed.add_field(name="Parameters", value=params_text, inline=False)

                if cmd_info.get("note"):
                    embed.add_field(name="Note", value=cmd_info["note"], inline=False)

                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Command Not Found",
                    description=f"Command `{command_name}` not found in main commands. Try `/help_full {command_name}` for complete command list.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show main commands
            await interaction.response.defer()

            embed = discord.Embed(
                title="🌟 Main Soul Link Commands",
                description="Essential commands to get started with Soul Link challenges",
                color=discord.Color.purple()
            )

            commands_text = ""
            for cmd_name, cmd_info in self.main_commands.items():
                commands_text += f"**{cmd_name}** - {cmd_info.get('description', 'N/A')}\n"

            embed.add_field(name="Available Commands", value=commands_text, inline=False)

            embed.add_field(
                name="💡 Getting More Help",
                value="Use `/help <command_name>` to get detailed information about a specific command.\n\nExample: `/help create_run` or `/help /create_run`\n\nFor ALL commands, use `/help_full`",
                inline=False
            )

            await interaction.followup.send(embed=embed)

    @app_commands.command(name="help_full", description="Show ALL available commands with full details")
    @app_commands.describe(
        command="Optional: Get detailed help for a specific command"
    )
    async def help_full_command(self, interaction: discord.Interaction, command: str = ""):
        """Show help for all commands organized by category."""

        if command:
            # Show help for specific command
            command_name = command if command.startswith("/") else f"/{command}"
            found = False
            found_category = None

            # Search for command in all categories
            for category, cmds in self.full_commands.items():
                if isinstance(cmds, dict) and command_name in cmds:
                    cmd_info = cmds[command_name]
                    found_category = category
                    found = True
                    break

            if found and found_category:
                cmd_info = self.full_commands[found_category][command_name]
                embed = discord.Embed(
                    title=f"📖 Help for {command_name}",
                    description=cmd_info.get("description", ""),
                    color=discord.Color.blue()
                )

                embed.add_field(name="Category", value=found_category, inline=False)
                embed.add_field(name="Usage", value=f"`{cmd_info.get('usage', 'N/A')}`", inline=False)

                if cmd_info.get("parameters"):
                    params_text = ""
                    for param_name, param_desc in cmd_info["parameters"]:
                        params_text += f"**{param_name}**: {param_desc}\n"
                    embed.add_field(name="Parameters", value=params_text, inline=False)

                if cmd_info.get("note"):
                    embed.add_field(name="Note", value=cmd_info["note"], inline=False)

                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Command Not Found",
                    description=f"Command `{command_name}` not found. Use `/help_full` to see all commands.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show all commands
            await interaction.response.defer()

            embed = discord.Embed(
                title="📚 Complete Command Reference",
                description="All available commands for the Nuzlocke Soul Link Bot, organized by category",
                color=discord.Color.purple()
            )

            for category, cmds in self.full_commands.items():
                if isinstance(cmds, dict):
                    commands_text = ""
                    for cmd_name, cmd_info in cmds.items():
                        commands_text += f"**{cmd_name}** - {cmd_info.get('description', 'N/A')}\n"

                    embed.add_field(name=category, value=commands_text, inline=False)

            embed.add_field(
                name="💡 Getting More Help",
                value="Use `/help_full <command_name>` to get detailed information about a specific command.\n\nExample: `/help_full soul_link_status`\n\nFor quick reference of main commands, use `/help`",
                inline=False
            )

            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))

