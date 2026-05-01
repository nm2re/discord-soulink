import discord
from discord.ext import commands
from discord import app_commands
from utils import create_embed
from logging_utils import format_run_logs_for_embed, get_run_logs
import database as db_utils


class RunLogs(commands.Cog):
    """Commands for viewing run logs and activity."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="run_log", description="View the activity log for a run")
    @app_commands.describe(
        run_id="The run ID to view logs for",
        limit="Number of recent events to show (default: 15, max: 50)"
    )
    async def run_log(self, interaction: discord.Interaction, run_id: int, limit: int = 15):
        """View recent activity in a run."""
        try:
            await interaction.response.defer()

            # Validate limit
            if limit < 1 or limit > 50:
                embed = create_embed("❌ Error", "Limit must be between 1 and 50", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get run info
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get all logs
            logs = await get_run_logs(run_id)

            if not logs:
                embed = create_embed(
                    "📋 Run Activity Log",
                    f"Run: {run[3]} ({run[4]})\nNo events logged yet.",
                    discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                return

            # Get recent events
            recent_logs = logs[-limit:] if len(logs) > limit else logs

            log_text = ""
            for log in recent_logs:
                timestamp = log.get('timestamp', 'N/A')
                # Parse timestamp to make it more readable
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%m/%d %H:%M:%S")
                except:
                    time_str = timestamp

                event_type = log.get('event_type', 'UNKNOWN')
                description = log.get('description', 'No description')

                # Format event type nicely
                event_label = event_type.replace('_', ' ').title()

                log_text += f"**{event_label}** ({time_str})\n"
                log_text += f"└─ {description}\n\n"

            embed = create_embed(
                "📋 Run Activity Log",
                f"Run: **{run[3]}** ({run[4]})",
                discord.Color.blue()
            )

            # Split into multiple fields if too long
            if len(log_text) > 1024:
                # Split the log into chunks
                chunks = []
                current_chunk = ""
                for line in log_text.split('\n'):
                    if len(current_chunk) + len(line) + 1 > 1024:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = line + "\n"
                    else:
                        current_chunk += line + "\n"
                if current_chunk:
                    chunks.append(current_chunk)

                for i, chunk in enumerate(chunks):
                    embed.add_field(
                        name=f"Events (Part {i+1}/{len(chunks)})",
                        value=chunk or "No events",
                        inline=False
                    )
            else:
                embed.add_field(
                    name=f"Recent Events ({min(limit, len(logs))} of {len(logs)})",
                    value=log_text or "No events",
                    inline=False
                )

            # Add summary
            event_counts = {}
            for log in logs:
                event_type = log.get('event_type', 'UNKNOWN')
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

            summary_text = ""
            for event_type, count in sorted(event_counts.items()):
                event_label = event_type.replace('_', ' ').lower()
                summary_text += f"• {event_label}: {count}\n"

            embed.add_field(
                name="📊 Event Summary",
                value=summary_text or "No summary",
                inline=False
            )

            if len(logs) > limit:
                embed.add_field(
                    name="ℹ️ Info",
                    value=f"Showing {limit} of {len(logs)} total events. Use `limit` parameter to see more.",
                    inline=False
                )

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="export_run_log", description="Export run activity log as a text file")
    @app_commands.describe(
        run_id="The run ID to export logs for"
    )
    async def export_run_log(self, interaction: discord.Interaction, run_id: int):
        """Export run activity log as a downloadable text file."""
        try:
            await interaction.response.defer()

            # Get run info
            run = await db_utils.get_run(run_id)
            if not run:
                embed = create_embed("❌ Error", f"Run with ID {run_id} not found", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get all logs
            logs = await get_run_logs(run_id)

            if not logs:
                embed = create_embed("❌ Error", "No events to export for this run", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Build formatted output
            output = f"{'='*80}\n"
            output += f"RUN {run_id} - ACTIVITY LOG\n"
            output += f"Run: {run[3]} ({run[4]})\n"
            output += f"{'='*80}\n\n"

            for log in logs:
                timestamp = log.get('timestamp', 'N/A')
                event_type = log.get('event_type', 'UNKNOWN')
                description = log.get('description', 'No description')
                details = log.get('details', {})

                output += f"[{timestamp}] {event_type}\n"
                output += f"  {description}\n"

                if details:
                    output += "  Details:\n"
                    for key, value in details.items():
                        output += f"    - {key}: {value}\n"

                output += "\n"

            # Save to temporary file and send
            temp_filename = f"run_{run_id}_log.txt"
            with open(temp_filename, 'w') as f:
                f.write(output)

            embed = create_embed(
                "📥 Run Log Exported",
                f"Activity log for Run {run_id} ({run[3]})",
                discord.Color.green()
            )
            embed.add_field(
                name="📊 Statistics",
                value=f"Total Events: {len(logs)}\nFile: {temp_filename}",
                inline=False
            )

            await interaction.followup.send(
                embed=embed,
                file=discord.File(temp_filename, filename=f"run_{run_id}_activity_log.txt")
            )

            # Clean up temp file
            import os
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

        except Exception as e:
            embed = create_embed("❌ Error", str(e), discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(RunLogs(bot))

