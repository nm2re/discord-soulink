import discord
from discord.ext import commands
import asyncio
import os
from config import DISCORD_BOT_TOKEN, BOT_PREFIX, BOT_DESCRIPTION
from database import init_db

# Set up bot intents
intents = discord.Intents.default()
# intents.message_content = True  # Only needed if reading message content from prefix commands

# Create bot
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=commands.DefaultHelpCommand())

@bot.event
async def on_ready():
    """Called when bot is ready."""
    print(f"✅ Bot logged in as {bot.user}")
    print(f"📊 Connected to {len(bot.guilds)} guild(s)")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} application command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.command(name="about", help="Show bot information")
async def about(ctx):
    """Display bot information."""
    embed = discord.Embed(
        title="🎮 Nuzlocke Soul Link Bot",
        description=BOT_DESCRIPTION,
        color=discord.Color.purple()
    )
    embed.add_field(
        name="📚 Features",
        value="""
        • Manage 1-4 player Nuzlocke runs
        • Track routes and encounters
        • Soul Link Pokemon pairing
        • Team management (faints, releases, boxes)
        • Optional clauses support
        """,
        inline=False
    )
    embed.add_field(
        name="📖 Getting Started",
        value=f"Use `{BOT_PREFIX}help` to see all commands",
        inline=False
    )
    await ctx.send(embed=embed)

async def load_cogs():
    """Load all cogs from the cogs directory."""
    cogs_dir = "cogs"
    if not os.path.exists(cogs_dir):
        os.makedirs(cogs_dir)
        print(f"📁 Created {cogs_dir} directory. Please add cog files.")
        return

    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Loaded cog: {filename}")
            except Exception as e:
                print(f"❌ Failed to load cog {filename}: {e}")

async def main():
    """Initialize bot and start."""
    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Load cogs
    await load_cogs()

    # Start bot
    if not DISCORD_BOT_TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN not set in .env file")
        return

    async with bot:
        await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot shutting down...")

