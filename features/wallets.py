import json
import os
import discord
from discord import app_commands

# Path to wallets JSON file
WALLETS_FILE = 'features/wallets.json'

# Ensure the wallets file exists
if not os.path.exists(WALLETS_FILE):
    with open(WALLETS_FILE, 'w') as f:
        json.dump({}, f)

# Load wallet data
def load_wallets():
    with open(WALLETS_FILE, 'r') as f:
        return json.load(f)

# Save wallet data
def save_wallets(wallets):
    with open(WALLETS_FILE, 'w') as f:
        json.dump(wallets, f, indent=4)

# Set wallet balance for a user (admin/owner only)
async def set_wallet(interaction: discord.Interaction, user: discord.Member, balance: int):
    if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
        wallets = load_wallets()
        user_id = str(user.id)

        # Add the new balance to the existing balance, if any
        current_balance = wallets.get(user_id, 5000)  # Default to 5000 if user has no wallet yet
        new_balance = current_balance + balance
        wallets[user_id] = new_balance
        save_wallets(wallets)

        await interaction.response.send_message(f"Added {balance} W-Coins to {user.name}'s wallet. New balance: {new_balance} W-Coins.")
    else:
        await interaction.response.send_message("You do not have permission to set wallet balances.", ephemeral=True)

async def check_wallet(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    wallets = load_wallets()
    
    # Initialize with default balance if the user is new
    if user_id not in wallets:
        wallets[user_id] = 5000  # Default balance
        save_wallets(wallets)

    balance = wallets[user_id]
    await interaction.response.send_message(f"Your wallet balance is {balance} W-Coins.")
