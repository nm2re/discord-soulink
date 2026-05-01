import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Token
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

# Database
DATABASE_PATH = "nuzlocke_data.db"

# Bot Configuration
BOT_PREFIX = "!"
BOT_DESCRIPTION = "A bot for managing Nuzlocke Soul Link challenges with support for 1-4 players"

# Game Constraints
MIN_PLAYERS = 2
MAX_PLAYERS = 4

# Nuzlocke Clauses (optional rules)
AVAILABLE_CLAUSES = {
    "duplicate": "Duplicate Clause - Can skip duplicates when catching",
    "shiny": "Shiny Clause - Can catch any shiny encountered",
    "gift": "Gift Clause - Gifts count as encounters on their route",
    "species": "Species Clause - Can only have one Pokémon of each species",
    "type_restriction": "Type Restriction - No shared primary types between teams",
    "nuzlocke": "Classic Nuzlocke - No clauses, just the 3 basic rules",
}

# Pokemon Types (for type restriction clause)
POKEMON_TYPES = [
    "Normal", "Fire", "Water", "Grass", "Electric", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost",
    "Dragon", "Dark", "Steel", "Fairy"
]

