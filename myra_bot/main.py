import os
import random
import discord
from discord.ext import commands
from discord.ext.commands import BucketType, cooldown
import json

intents = discord.Intents.default()
intents.message_content = True  # Make sure this is enabled in your Discord Developer Portal!

bot = commands.Bot(command_prefix="!", intents=intents)

# Load or initialize user stats
STATS_FILE = "user_stats.json"
if os.path.exists(STATS_FILE):
    with open(STATS_FILE, "r") as f:
        user_stats = json.load(f)
else:
    user_stats = {}

# Blessing data with rarity, colors, images, and texts
blessings = [
    {
        "name": "common",
        "chance": 0.45,
        "color": 0x2ECC71,  # Green
        "text": "Myra shines her radiant gaze upon you; your tavern ticket pulls are destined to reveal mightier heroes. Epic energies surge through this blessing!",
        "image": "images/Blessings1.jpg",
    },
    {
        "name": "rare",
        "chance": 0.33,
        "color": 0x3498DB,  # Blue
        "text": "You have been blessed — the treasures within your gold chests now gleam with greater fortune.",
        "image": "images/Blessings2.jpg",
    },
    {
        "name": "epic",
        "chance": 0.14,
        "color": 0x9B59B6,  # Purple
        "text": "You have earned Myra's favor; your next summon holds the promise of exceptional fortune.",
        "image": "images/Blessings3.jpg",
    },
    {
        "name": "legendary",
        "chance": 0.06,  # The remaining probability (adjusted to sum to 1)
        "color": 0xF1C40F,  # Gold
        "text": "The legendary blessing of Myra surrounds you; may your journey be extraordinary!",
        "image": "images/Blessings3.jpg",
    },
    {
        "name": "mythic",
        "chance": 0.02,
        "color": 0xE74C3C,  # Red
        "text": "A mythic blessing descends upon you, a rare gift of immeasurable power!",
        "image": "images/Blessings3.jpg",
    },
]

# Bad fortune (no rarity)
bad_fortune = {
    "text": "Alas, Myra's mischief has befallen you. Beware the shadows and misfortune lurking ahead.",
    "image": "images/badluck.jpg",
    "color": 0x95A5A6,  # Grey
}

# Helper function to pick a blessing rarity based on chance
def pick_blessing():
    roll = random.random()
    cumulative = 0
    for b in blessings:
        cumulative += b["chance"]
        if roll <= cumulative:
            return b
    return blessings[-1]  # fallback to mythic if something weird happens

# Save user stats to file
def save_stats():
    with open(STATS_FILE, "w") as f:
        json.dump(user_stats, f)

# Cooldown decorator: 24 hours per user per command
COOLDOWN_SECONDS = 60 * 60 * 24

@bot.command(name="bless")
@cooldown(1, COOLDOWN_SECONDS, BucketType.user)
async def bless(ctx):
    # Decide if bad fortune or good blessing (say 1 in 10 chance bad fortune)
    if random.random() < 0.10:
        embed = discord.Embed(
            title="Bad Fortune",
            description=bad_fortune["text"],
            color=bad_fortune["color"],
        )
        file = discord.File(bad_fortune["image"], filename="badluck.jpg")
        embed.set_image(url="attachment://badluck.jpg")
        await ctx.send(embed=embed, file=file)
        return

    blessing = pick_blessing()
    embed = discord.Embed(
        title=f"Myra's Blessing: {blessing['name'].capitalize()}",
        description=blessing["text"],
        color=blessing["color"],
    )
    filename = blessing["image"].split("/")[-1]
    file = discord.File(blessing["image"], filename=filename)
    embed.set_image(url=f"attachment://{filename}")

    user_id = str(ctx.author.id)
    # Track counts only for good blessings
    if blessing["name"] != "bad":
        if user_id not in user_stats:
            user_stats[user_id] = {
                "common": 0,
                "rare": 0,
                "epic": 0,
                "legendary": 0,
                "mythic": 0,
            }
        user_stats[user_id][blessing["name"]] += 1
        save_stats()

    await ctx.send(embed=embed, file=file)

@bless.error
async def bless_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        time_left = error.retry_after
        hours = int(time_left // 3600)
        minutes = int((time_left % 3600) // 60)
        seconds = int(time_left % 60)
        await ctx.send(
            f"⏳ You need to wait {hours}h {minutes}m {seconds}s before using this command again."
        )
    else:
        await ctx.send(f"An error occurred: {str(error)}")

@bot.command(name="mystats")
async def mystats(ctx):
    user_id = str(ctx.author.id)
    if user_id not in user_stats:
        await ctx.send("You don't have any blessings yet. Use `!bless` to get started!")
        return
    stats = user_stats[user_id]
    embed = discord.Embed(
        title=f"{ctx.author.display_name}'s Blessing Stats",
        color=discord.Color.blue(),
    )
    for rarity in ["mythic", "legendary", "epic", "rare", "common"]:
        embed.add_field(name=rarity.capitalize(), value=str(stats.get(rarity, 0)), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    # Sort users by their mythic count, then legendary, etc.
    def sort_key(item):
        stats = item[1]
        return (
            stats.get("mythic", 0),
            stats.get("legendary", 0),
            stats.get("epic", 0),
            stats.get("rare", 0),
            stats.get("common", 0),
        )
    sorted_users = sorted(user_stats.items(), key=sort_key, reverse=True)
    embed = discord.Embed(
        title="Myra's Blessing Leaderboard",
        color=discord.Color.gold(),
    )
    count = 0
    for user_id, stats in sorted_users:
        count += 1
        user = await bot.fetch_user(int(user_id))
        embed.add_field(
            name=f"{count}. {user.name}",
            value=(
                f"Mythic: {stats.get('mythic', 0)} | Legendary: {stats.get('legendary', 0)} | "
                f"Epic: {stats.get('epic', 0)} | Rare: {stats.get('rare', 0)} | Common: {stats.get('common', 0)}"
            ),
            inline=False,
        )
        if count >= 10:
            break
    await ctx.send(embed=embed)

@leaderboard.error
async def leaderboard_error(ctx, error):
    await ctx.send(f"An error occurred: {str(error)}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        bot.run(token)
