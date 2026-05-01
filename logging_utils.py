import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = "run_logs"
Path(LOGS_DIR).mkdir(exist_ok=True)


async def log_event(run_id: int, event_type: str, description: str, details: Optional[Dict[str, Any]] = None):
    """
    Log an event for a specific run.

    Args:
        run_id: The run ID
        event_type: Type of event (e.g., "RUN_CREATED", "ENCOUNTER_RECORDED", "POKEMON_FAINTED", etc.)
        description: Human-readable description of the event
        details: Optional dict with additional event details
    """
    log_file = os.path.join(LOGS_DIR, f"run_{run_id}.json")

    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "description": description,
        "details": details or {}
    }

    # Read existing logs
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except (json.JSONDecodeError, IOError):
            logs = []

    # Append new event
    logs.append(event)

    # Write back to file
    try:
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    except IOError as e:
        print(f"Error writing to log file: {e}")


async def get_run_logs(run_id: int) -> list:
    """Get all logs for a specific run."""
    log_file = os.path.join(LOGS_DIR, f"run_{run_id}.json")

    if not os.path.exists(log_file):
        return []

    try:
        with open(log_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


async def export_run_logs(run_id: int) -> str:
    """Export run logs as a formatted text file."""
    logs = await get_run_logs(run_id)

    if not logs:
        return "No logs found for this run."

    # Build formatted output
    output = f"{'='*80}\n"
    output += f"RUN {run_id} - ACTIVITY LOG\n"
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

    return output


async def format_run_logs_for_embed(run_id: int, limit: int = 10) -> tuple[str, int]:
    """
    Format run logs for Discord embed display.
    Returns (formatted_log_text, total_event_count)
    """
    logs = await get_run_logs(run_id)

    if not logs:
        return "No events logged yet.", 0

    # Get the most recent events
    recent_logs = logs[-limit:] if len(logs) > limit else logs

    log_text = ""
    for log in recent_logs:
        timestamp = log.get('timestamp', 'N/A')
        # Parse timestamp to make it more readable
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%m/%d %H:%M")
        except:
            time_str = timestamp

        event_type = log.get('event_type', 'UNKNOWN')
        description = log.get('description', 'No description')

        # Format event type nicely (convert from ALL_CAPS to Title Case)
        event_label = event_type.replace('_', ' ').title()

        log_text += f"**{event_label}** ({time_str})\n"
        log_text += f"└─ {description}\n"

    if len(logs) > limit:
        log_text += f"\n*... and {len(logs) - limit} more events*"

    return log_text, len(logs)


async def get_run_log_file_path(run_id: int) -> str:
    """Get the file path for a run's log file."""
    return os.path.join(LOGS_DIR, f"run_{run_id}.json")

