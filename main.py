import discord
import os
import json
import random
import re
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from fuzzywuzzy import process
from features.wallets import set_wallet, check_wallet
from features.blackjack import blackjack
from myserver import server_on

# Define constants for Blackjack bet limits
MIN_BET = 50
MAX_BET = 10000

# Load environment variables from .env file
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Load responses from JSON file
with open('responses.json', 'r') as file:
    responses = json.load(file)

# Create an intents object and set it to default
intents = discord.Intents.default()
intents.message_content = True  # Ensure you have access to message content
intents.members = True  # To access member information
intents.reactions = True  # To access reaction events

# Create a bot instance with intents and a command prefix
bot = commands.Bot(command_prefix='/', intents=intents)

# List of allowed admins (user IDs) and owner ID
ALLOWED_ADMINS = [801524743118651393]  # Replace with actual user IDs
OWNER_ID = 833429492760313856  # Replace with the server owner ID

# Role and emoji mapping (to be updated dynamically)
ROLE_EMOJI_MAPPING = {}

def clean_message(content):
    # Remove mentions (e.g., <@!?(\d+)>)
    content = re.sub(r'<@!?(\d+)>', '', content)
    # Remove special characters like ?, /, ! and trim whitespace
    content = re.sub(r'[!?/]', '', content)
    return content.strip()

@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync commands with Discord
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_message(message):
    # Prevent bot from replying to itself
    if message.author == bot.user:
        return

    # Check if the message is a command
    if message.content.startswith(bot.command_prefix):
        # Process the command
        await bot.process_commands(message)
    else:
        # Clean the message content
        cleaned_content = clean_message(message.content)
        content_lower = cleaned_content.lower()
        
        # Extract keys (questions) from responses
        questions = responses.keys()
        
        # Find the closest match to the user's message
        best_match, score = process.extractOne(content_lower, questions)

        # Set a higher threshold for matching accuracy
        threshold = 50  # Adjust this threshold as needed

        # Determine the response based on the score
        if score >= threshold:
            response_data = responses.get(best_match, {"responses": ["I don't understand that."], "default": "I don't understand that."})
            reply = random.choice(response_data["responses"])
        else:
            reply = "ngomong apasi"

        # Add a random delay before sending the response
        delay = random.uniform(1, 5)  # Random delay between 1 and 10 seconds
        await asyncio.sleep(delay)  # Wait for the random duration

        # Send the response to the channel
        await message.channel.send(reply)

# Define a slash command to show profile (Public Command)
@bot.tree.command(name='profile', description='View the profile of a user.')
@app_commands.describe(user='The user whose profile you want to view.')
async def profile(interaction: discord.Interaction, user: discord.Member = None):
    if user is None:
        await interaction.response.send_message("Please mention a user to view their profile.")
        return

    # Retrieve user profile information
    profile_info = (
        f"**Username:** {user.name}\n"
        f"**ID:** {user.id}\n"
        f"**Joined Server On:** {user.joined_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**Account Created On:** {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**Status:** {user.status}\n"
    )
    
    # Check if avatar exists
    if user.avatar:
        profile_info += f"**Avatar:** [Click here]({user.avatar.url})\n"
    else:
        profile_info += "**Avatar:** No profile picture available.\n"
    
    # Send profile information to the channel
    await interaction.response.send_message(profile_info)

# Define a slash command for DM (Admin Command)
@bot.tree.command(name='dm', description='Send a DM to a user.')
@app_commands.describe(user='The user to DM', message='The message to send')
async def dm(interaction: discord.Interaction, user: discord.User, message: str):
    # Check if the user has admin or owner permissions
    user_id = interaction.user.id
    if user_id == OWNER_ID or user_id in ALLOWED_ADMINS:
        try:
            # Send DM to the user
            await user.send(message)
            # Send confirmation to the channel
            await interaction.response.send_message(f"Message sent to {user.name}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"Cannot send message to {user.name}. They may have DMs disabled.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}")
    else:
        await interaction.response.send_message("You do not have the required permissions to use this command.")

# Define a new slash command to send a message with reaction roles (Admin Command)
@bot.tree.command(name='send', description='Send a message to a specific channel with reaction roles.')
@app_commands.describe(channel='The channel to send the message to', text='The text message to send', role='The role to assign with reactions')
async def send(interaction: discord.Interaction, channel: discord.TextChannel, text: str, role: discord.Role):
    user_id = interaction.user.id
    if user_id == OWNER_ID or user_id in ALLOWED_ADMINS:
        try:
            # Send the message
            sent_message = await channel.send(text)
            # Add a reaction to the message
            emoji = '👍'  # You can change this to any emoji you want
            await sent_message.add_reaction(emoji)
            # Update the ROLE_EMOJI_MAPPING
            ROLE_EMOJI_MAPPING[emoji] = role.id
            await interaction.response.send_message(f"Message sent to {channel.mention} with reaction '{emoji}' for role '{role.name}'.")
        except discord.Forbidden:
            await interaction.response.send_message(f"Cannot send message to {channel.mention}. The bot may not have permission to send messages in that channel.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}")
    else:
        await interaction.response.send_message("You do not have the required permissions to use this command.")

# Register the /setwallet command (Admin/Owner Only)
@bot.tree.command(name="setwallets", description="Set a user's wallet balance (Admin only).")
@app_commands.describe(user="The user whose balance you want to set", balance="The amount of W-Coins to set")
async def set_wallet_command(interaction: discord.Interaction, user: discord.Member, balance: int):
    await set_wallet(interaction, user, balance)

# Register the /wallets command (Self-check only)
@bot.tree.command(name="wallets", description="Check your own wallet balance.")
async def check_wallet_command(interaction: discord.Interaction):
    await check_wallet(interaction)

# Register the /blackjack command
@bot.tree.command(name="blackjack", description="Challenge a user to a game of Blackjack!")
@app_commands.describe(opponent="The user you want to challenge", bet="The amount of W-Coins to bet")
async def blackjack_command(interaction: discord.Interaction, opponent: discord.Member, bet: int):
    if bet < MIN_BET or bet > MAX_BET:
        await interaction.response.send_message(f"Invalid bet amount. You must bet between {MIN_BET} and {MAX_BET} W-Coins.", ephemeral=True)
    else:
        await blackjack(interaction, opponent, bet)

# Event to handle reaction addition
@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return

    # Check if the reaction is on a message sent by the bot
    if reaction.message.author == bot.user:
        role_id = ROLE_EMOJI_MAPPING.get(reaction.emoji)
        if role_id:
            role = discord.utils.get(user.guild.roles, id=role_id)
            if role:
                try:
                    await user.add_roles(role)
                    print(f"Assigned role '{role.name}' to {user.name}.")
                except discord.Forbidden:
                    print(f"Cannot assign role '{role.name}' to {user.name}.")
                except Exception as e:
                    print(f"An error occurred: {str(e)}")

# Event to handle reaction removal
@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user:
        return

    # Check if the reaction is on a message sent by the bot
    if reaction.message.author == bot.user:
        role_id = ROLE_EMOJI_MAPPING.get(reaction.emoji)
        if role_id:
            role = discord.utils.get(user.guild.roles, id=role_id)
            if role:
                try:
                    await user.remove_roles(role)
                    print(f"Removed role '{role.name}' from {user.name}.")
                except discord.Forbidden:
                    print(f"Cannot remove role '{role.name}' from {user.name}.")
                except Exception as e:
                    print(f"An error occurred: {str(e)}")

# Run the bot
bot.run(DISCORD_TOKEN)
