import discord
import random
import asyncio
from discord.ui import Button, View
from features.wallets import load_wallets, save_wallets

# Define constants for bet limits
MIN_BET = 50
MAX_BET = 10000

# Function to draw a card
def draw_card():
    return random.randint(2, 10)

# Function to calculate total hand value
def hand_value(hand):
    return sum(hand)

# Function to update wallets
def update_wallet(user_id, amount):
    wallets = load_wallets()
    wallets[user_id] = wallets.get(user_id, 5000) + amount
    save_wallets(wallets)

# Blackjack game logic
async def blackjack(interaction: discord.Interaction, opponent: discord.Member, bet: int):
    # Load wallets
    wallets = load_wallets()
    user_id = str(interaction.user.id)
    opponent_id = str(opponent.id)

    # Check if both players have enough W-Coins
    if wallets.get(user_id, 5000) < bet:
        await interaction.response.send_message(f"Insufficient W-Coins! You only have {wallets.get(user_id, 5000)} W-Coins.", ephemeral=True)
        return

    if wallets.get(opponent_id, 5000) < bet:
        await interaction.response.send_message(f"{opponent.name} does not have enough W-Coins to match the bet.", ephemeral=True)
        return

    # Notify opponent of the challenge
    challenge_message = await interaction.channel.send(
        f"{interaction.user.mention} has challenged {opponent.mention} to a game of Blackjack for {bet} W-Coins! "
        f"React with ✅ to accept or ❌ to decline."
    )

    # Add reactions to the message
    await challenge_message.add_reaction("✅")
    await challenge_message.add_reaction("❌")

    # Check reaction
    def check(reaction, user):
        return user == opponent and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == challenge_message.id

    try:
        reaction, user = await interaction.client.wait_for('reaction_add', timeout=60.0, check=check)

        if str(reaction.emoji) == "✅":
            await interaction.channel.send(f"{opponent.mention} accepted the challenge!")
            await start_blackjack_game(interaction, opponent, bet)
        elif str(reaction.emoji) == "❌":
            await interaction.channel.send(f"{opponent.mention} declined the challenge.")
    except asyncio.TimeoutError:
        await interaction.channel.send(f"{opponent.mention} did not respond in time. Challenge cancelled.")

# Function to handle the Blackjack game
async def start_blackjack_game(interaction: discord.Interaction, opponent: discord.Member, bet: int):
    user_hand = [draw_card(), draw_card()]
    opponent_hand = [draw_card(), draw_card()]

    user_stand = False
    opponent_stand = False
    user_hits = 0
    opponent_hits = 0

    def get_hand_message(hand):
        return ', '.join(map(str, hand)) + f" (Total: {hand_value(hand)})"

    async def send_dm(user, content, view=None):
        try:
            await user.send(content=content, view=view)
        except discord.errors.NotFound:
            await interaction.channel.send(content=content, view=view)

    async def player_turn(player, hand, stand_flag, other_player, hits, is_user_turn):
        view = View()
        hit_button = Button(label="Hit", style=discord.ButtonStyle.primary)
        stand_button = Button(label="Stand", style=discord.ButtonStyle.secondary)

        async def hit_callback(interaction):
            nonlocal hits, stand_flag

            if stand_flag:
                await interaction.response.send_message("You've already stood. Please wait for the other player.", ephemeral=True)
                return

            if hits >= 3:
                await interaction.response.send_message("You have reached the maximum number of hits. You must stand.", ephemeral=True)
                stand_flag = True
                if is_user_turn:
                    user_stand = True
                else:
                    opponent_stand = True
                if user_stand and opponent_stand:
                    await determine_winner()
                return

            hand.append(draw_card())
            hits += 1
            hand_total = hand_value(hand)

            if hand_total > 21:
                await interaction.response.send_message(f"You have busted with {hand_total}! Waiting for {other_player.name} to finish their turn.", ephemeral=True)
                stand_flag = True
                if is_user_turn:
                    user_stand = True
                else:
                    opponent_stand = True
                if user_stand and opponent_stand:
                    await determine_winner()
                return
            elif hand_total == 21:
                await interaction.response.send_message(f"You have 21 with {get_hand_message(hand)}! Waiting for {other_player.name} to finish their turn.", ephemeral=True)
                stand_flag = True
                if is_user_turn:
                    user_stand = True
                else:
                    opponent_stand = True
                if user_stand and opponent_stand:
                    await determine_winner()
                return
            else:
                await interaction.response.send_message(f"Your hand: {get_hand_message(hand)}", ephemeral=True)

        async def stand_callback(interaction):
            nonlocal user_stand, opponent_stand, stand_flag
            if player == interaction.user:
                user_stand = True
            else:
                opponent_stand = True

            stand_flag = True
            await interaction.response.send_message(f"You stand with {get_hand_message(hand)}. Waiting for {other_player.name} to finish their turn.", ephemeral=True)
            if user_stand and opponent_stand:
                await determine_winner()
            elif is_user_turn:
                await player_turn(other_player, opponent_hand, opponent_stand, interaction.user, opponent_hits, False)

        hit_button.callback = hit_callback
        stand_button.callback = stand_callback

        view.add_item(hit_button)
        view.add_item(stand_button)

        await send_dm(player, f"Your hand: {get_hand_message(hand)}", view=view)

    async def determine_winner():
        user_total = hand_value(user_hand)
        opponent_total = hand_value(opponent_hand)

        # Debugging output
        print(f"User total: {user_total}")
        print(f"Opponent total: {opponent_total}")

        result_message = ""
        if user_total > 21 and opponent_total <= 21:
            result_message = f"You busted with {user_total}. {opponent.name} wins. You lose {bet} W-Coins."
            update_wallet(str(interaction.user.id), -bet)
            update_wallet(str(opponent.id), bet)
        elif opponent_total > 21 and user_total <= 21:
            result_message = f"{opponent.name} busted with {opponent_total}. You win {2 * bet} W-Coins."
            update_wallet(str(interaction.user.id), 2 * bet)
            update_wallet(str(opponent.id), -bet)
        elif user_total > 21 and opponent_total > 21:
            result_message = f"Both you and {opponent.name} busted. No W-Coins are exchanged."
        elif user_total > opponent_total:
            result_message = f"You win with {user_total} against {opponent_total}! You earn {2 * bet} W-Coins."
            update_wallet(str(interaction.user.id), 2 * bet)
            update_wallet(str(opponent.id), -bet)
        elif opponent_total > user_total:
            result_message = f"{opponent.name} wins with {opponent_total} against {user_total}. You lose {bet} W-Coins."
            update_wallet(str(interaction.user.id), -bet)
            update_wallet(str(opponent.id), bet)
        else:
            result_message = f"It's a draw! Both hands are {user_total}. No W-Coins are exchanged."

        await send_dm(interaction.user, f"Game over! {result_message}")
        await send_dm(opponent, f"Game over! {interaction.user.name}'s hand: {get_hand_message(user_hand)}. Your hand: {get_hand_message(opponent_hand)}. Result: {result_message}")

    # Start both players' turns
    await player_turn(interaction.user, user_hand, user_stand, opponent, user_hits, True)
    await player_turn(opponent, opponent_hand, opponent_stand, interaction.user, opponent_hits, False)
