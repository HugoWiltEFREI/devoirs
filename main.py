import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta

import json
import os

SETTINGS_FILE = "settings.json"

# Load user settings from file
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save user settings to file
def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(user_settings, f, indent=4)

# Load settings at startup
user_settings = load_settings()




# Default values
GUILD_ID = 781595409872584706  # Replace with your server ID
REMINDER_CHANNEL_ID = 1340781926876844133  # Replace with your reminder channel ID
DEFAULT_EXAM_REMINDER_DAYS = 3  # Default days before exam to send reminder
DEFAULT_HOMEWORK_REMINDER_DAYS = 1  # Default days before homework to send reminder

# List of allowed user IDs who can modify the reminder channel settings
ALLOWED_USER_IDS = [683735007109709871]  # Replace with your admin user IDs

SUBJECTS = {
    "FH401B": {"name": "Dissertation et rhétorique", "url": "https://moodle.myefrei.fr/course/view.php?id=14237"},
    "FL401B": {"name": "English : Study Abroad", "url": "https://moodle.myefrei.fr/course/view.php?id=14243"},
    "TI404B": {"name": "Bases de données", "url": "https://moodle.myefrei.fr/course/view.php?id=14280"},
    "TI403B": {"name": "POO : Java", "url": "https://moodle.myefrei.fr/course/view.php?id=14275"},
    "TI402B": {"name": "Programmation Web", "url": "https://moodle.myefrei.fr/course/view.php?id=14272"},
    "SM401B": {"name": "Modélisation mathématique", "url": "https://moodle.myefrei.fr/course/view.php?id=14248"},
    "SM402B": {"name": "Automates", "url": "https://moodle.myefrei.fr/course/view.php?id=14252"},
    "SM403B": {"name": "Analyse de données", "url": "https://moodle.myefrei.fr/course/view.php?id=14255"},
    "SP401B": {"name": "Électromagnétique", "url": "https://moodle.myefrei.fr/course/view.php?id=14260"},
    "SP402B": {"name": "Thermodynamique", "url": "https://moodle.myefrei.fr/course/view.php?id=14264"},
    "TE403B": {"name": "Canaux de transmission", "url": "https://moodle.myefrei.fr/course/view.php?id=14268"},
    "TI450B": {"name": "Delivery Project", "url": "https://moodle.myefrei.fr/course/view.php?id=14283"}
}
SUBJECT_CHOICES = [app_commands.Choice(name=v["name"], value=k) for k, v in SUBJECTS.items()]
TYPE_CHOICES = [app_commands.Choice(name="Exam", value="exam"), app_commands.Choice(name="Homework", value="homework"), app_commands.Choice(name="Other", value="other")]
IMPORTANCE_CHOICES = [app_commands.Choice(name=f"{i} ({'★' * i})", value=i) for i in range(1, 6)]
WEEKDAY_CHOICES = [app_commands.Choice(name=day, value=i) for i, day in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])]

# Enable the necessary intents
intents = discord.Intents.default()
intents.messages = True  # Ensures the bot can read and send messages

# Store user-specific settings
user_settings = {}


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.reminders = []  # Store reminders

    async def setup_hook(self):
        try:
            # Sync slash commands globally instead of just for a specific guild
            await self.tree.sync()  # Sync commands globally
            print("Slash commands synced globally.")
            self.reminder_task.start()  # Start the reminder loop
            self.cleanup_task.start()  # Start the cleanup task
        except Exception as e:
            print(f"❌ Error syncing commands: {e}")
            raise

    @tasks.loop(minutes=1)
    async def reminder_task(self):
        """Background task to send reminders at the right time."""
        now = datetime.utcnow()

        for reminder in bot.reminders[:]:  # Iterate over a copy to modify safely
            if now >= reminder["date"]:
                channel_id = reminder.get("channel_id", REMINDER_CHANNEL_ID)  # Default if missing

                channel = bot.get_channel(channel_id)
                if not channel:
                    print(f"⚠️ Warning: Could not find channel {channel_id} for reminder {reminder}. Skipping.")
                    continue  # Skip this reminder if channel doesn't exist

                embed = discord.Embed(
                    title=f"⏰ Reminder: {reminder['type'].capitalize()}",
                    description=reminder["description"],
                    color=discord.Color.red()
                )
                embed.add_field(name="📅 Due Date", value=f"<t:{int(reminder['date'].timestamp())}:F>", inline=False)
                embed.add_field(name="🔥 Importance", value=str(reminder["importance"]), inline=True)

                await channel.send(embed=embed)
                bot.reminders.remove(reminder)  # Remove sent reminder

    @tasks.loop(hours=24, minutes=45)  # This task will run at 20:45 UTC daily
    async def cleanup_task(self):
        now = datetime.utcnow()
        expired_reminders = [reminder for reminder in self.reminders if reminder["date"] < now]
        for reminder in expired_reminders:
            if "message_id" in reminder:
                # Get the channel and delete the message if it exists
                channel = self.get_channel(reminder["channel_id"])
                try:
                    message = await channel.fetch_message(reminder["message_id"])
                    await message.delete()
                    print(f"✅ Deleted expired reminder message: {message.id}")
                except discord.NotFound:
                    print(f"❌ Message not found for reminder: {reminder['message_id']}")
                except discord.Forbidden:
                    print(f"❌ No permission to delete message: {reminder['message_id']}")
                except discord.HTTPException as e:
                    print(f"❌ Failed to delete message {reminder['message_id']}: {e}")

                self.reminders.remove(reminder)

    def create_colored_embed(self, importance):
        # Color scale from light green (1) to dark red (5)
        colors = {
            1: discord.Color.green(),
            2: discord.Color(0x66FF33),  # Light green
            3: discord.Color(0xFFFF00),  # Yellow
            4: discord.Color(0xFF9900),  # Orange
            5: discord.Color.red()  # Dark red
        }
        return discord.Embed(color=colors.get(importance, discord.Color.default()))

    async def get_user_settings(self, user_id):
        return user_settings.get(user_id, {
            "exam_reminder_days": DEFAULT_EXAM_REMINDER_DAYS,
            "homework_reminder_days": DEFAULT_HOMEWORK_REMINDER_DAYS,
            "reminder_channel": REMINDER_CHANNEL_ID
        })


bot = MyBot()


@bot.tree.command(name="ping", description="Ping the bot.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@bot.tree.command(name="add", description="Add a new reminder.")
@app_commands.describe(
    type="Select the type of reminder",
    date="Due date (YYYY-MM-DD HH:MM) or leave empty if selecting a weekday",
    weekday="Select a weekday instead of entering a manual date",
    time="Specify the time if using a weekday (HH:MM)",
    description="Short description of the reminder (optional)",
    importance="Select difficulty level",
    subject="Select a subject"
)
@app_commands.choices(type=TYPE_CHOICES, subject=SUBJECT_CHOICES, importance=IMPORTANCE_CHOICES, weekday=WEEKDAY_CHOICES)
async def add(
    interaction: discord.Interaction,
    type: app_commands.Choice[str],
    subject: app_commands.Choice[str],
    importance: int = 3,
    date: str = None,
    weekday: app_commands.Choice[int] = None,
    time: str = "12:00",
    description: str = None
):
    print(
        f"Received command: /add with params - type: {type.name}, subject: {subject.name}, date: {date}, weekday: {weekday}, time: {time}, importance: {importance}"
    )  # Debug log

    reminder_date = None

    # Handle manual date input
    if date:
        try:
            reminder_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message("❌ Invalid date format. Use YYYY-MM-DD HH:MM.", ephemeral=True)
            return
    elif weekday is not None:  # Handle weekday selection
        try:
            hour, minute = map(int, time.split(":"))
            today = datetime.now()
            today_weekday = today.weekday()
            days_until = (weekday.value - today_weekday) % 7
            if days_until == 0 and today.hour > hour:
                days_until = 7

            reminder_date = today + timedelta(days=days_until)
            reminder_date = reminder_date.replace(hour=hour, minute=minute, second=0)
        except ValueError:
            await interaction.response.send_message("❌ Invalid time format. Use HH:MM.", ephemeral=True)
            return

    if reminder_date is None:
        await interaction.response.send_message("❌ Please provide either a manual date or a weekday.", ephemeral=True)
        return

    # Convert to Unix timestamp for Discord formatting
    timestamp = int(reminder_date.timestamp())

    # Get subject details
    subject_details = SUBJECTS.get(subject.value, {"name": "Unknown", "url": "N/A"})

    # Add the reminder to the list
    bot.reminders.append({
        "type": type.value,
        "date": reminder_date,
        "subject": subject_details["name"],
        "subject_code": subject.value,
        "description": description or "",
        "importance": importance,
        "user_id": interaction.user.id
    })

    # Create an embed message
    embed = discord.Embed(
        title=f"📌 Reminder: {subject_details['name']}",
        description=f"**Type:** {type.name}\n"
                    f"⏳ **Time left:** <t:{timestamp}:R>\n"
                    f"📅 **Due Date:** <t:{timestamp}:F>\n\n"
                    f"{description or ''}",
        color=bot.create_colored_embed(importance).color
    )
    embed.add_field(name="📚 Subject", value=f"[{subject_details['name']}]({subject_details['url']})", inline=False)
    embed.add_field(name="🔗 Course Link", value=subject_details["url"], inline=False)

    # Send reminder to the designated channel
    channel = bot.get_channel(REMINDER_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

    # Check if the reminder is within the threshold for DM
    days_left = (reminder_date - datetime.now()).days
    if type.value == "exam" and days_left <= DEFAULT_EXAM_REMINDER_DAYS:
        # Send DM for exam reminders within 3 days
        try:
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("✅ Reminder has been sent to the channel and your DMs!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("✅ Reminder sent to the channel, but I couldn't DM you. Please enable DMs from server members!", ephemeral=True)
    elif type.value == "homework" and days_left <= DEFAULT_HOMEWORK_REMINDER_DAYS:
        # Send DM for homework reminders within 1 day
        try:
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("✅ Reminder has been sent to the channel and your DMs!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("✅ Reminder sent to the channel, but I couldn't DM you. Please enable DMs from server members!", ephemeral=True)
    else:
        await interaction.response.send_message("✅ Reminder has been sent to the channel!", ephemeral=True)

@bot.tree.command(name="settings", description="Modify your personal reminder settings.")
@app_commands.describe(
    exam_reminder_days="Days before the exam to send a reminder",
    homework_reminder_days="Days before the homework to send a reminder",
    reminder_channel="Channel ID to send reminders (Leave blank for default)"
)
async def settings(interaction: discord.Interaction, exam_reminder_days: int = None, homework_reminder_days: int = None,
                   reminder_channel: str = None):
    user_id = str(interaction.user.id)  # Convert to string for JSON compatibility
    settings_msg = "Your settings have been updated:\n"

    # Ensure user exists in settings
    if user_id not in user_settings:
        user_settings[user_id] = {}

    # Check if the user is allowed to modify the reminder channel
    if reminder_channel is not None:
        if user_id not in ALLOWED_USER_IDS:
            await interaction.response.send_message("❌ You are not authorized to change the reminder channel.",
                                                    ephemeral=True)
            return
        try:
            reminder_channel_id = int(reminder_channel)
            user_settings[user_id]["reminder_channel"] = reminder_channel_id
            settings_msg += f"📢 Reminders will now be sent to channel {reminder_channel_id}.\n"
        except ValueError:
            settings_msg += "❌ Invalid channel ID. Please provide a valid numeric ID.\n"

    # Update exam and homework reminder days
    if exam_reminder_days is not None:
        user_settings[user_id]["exam_reminder_days"] = exam_reminder_days
        settings_msg += f"📝 Exam reminder will now be sent {exam_reminder_days} days before.\n"

    if homework_reminder_days is not None:
        user_settings[user_id]["homework_reminder_days"] = homework_reminder_days
        settings_msg += f"📝 Homework reminder will now be sent {homework_reminder_days} days before.\n"

    # Save updated settings
    save_settings()

    await interaction.response.send_message(settings_msg, ephemeral=True)


@bot.tree.command(name="purge", description="Delete all reminders (Admin only).")
@app_commands.describe(user_id="(Optional) User ID to delete only their reminders and DMs.")
async def purge(interaction: discord.Interaction, user_id: str = None):
    """Admin-only command to delete all reminders or a specific user's reminders and DMs."""
    if interaction.user.id not in ALLOWED_USER_IDS:  # Ensure only admins can use this
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer()  # Prevents timeout issues

    deleted_reminders = 0
    deleted_messages = 0

    if user_id:  # Purge a specific user's reminders and DMs
        user_id = int(user_id)
        initial_count = len(bot.reminders)
        bot.reminders = [r for r in bot.reminders if r["user_id"] != user_id]  # Remove only that user's reminders
        deleted_reminders = initial_count - len(bot.reminders)

        # Try deleting DMs
        user = await bot.fetch_user(user_id)
        if user:
            dm_channel = user.dm_channel or await user.create_dm()  # Ensure DM channel exists
            if dm_channel:
                try:
                    async for message in dm_channel.history(limit=None):  # Delete all messages
                        if message.author == bot.user:
                            await message.delete()
                            deleted_messages += 1
                except discord.Forbidden:
                    print(f"⚠️ Cannot access DMs of user {user_id}.")
                except discord.HTTPException:
                    print(f"⚠️ Failed to delete messages in {user_id}'s DMs.")

        await interaction.followup.send(f"✅ Purged {deleted_reminders} reminders and {deleted_messages} DM messages for <@{user_id}>.", ephemeral=True)

    else:  # Global purge (delete all reminders and messages)
        deleted_reminders = len(bot.reminders)
        bot.reminders.clear()  # Remove all reminders

        # Purge all bot messages in the reminder channel
        channel = bot.get_channel(REMINDER_CHANNEL_ID)
        if channel:
            messages_to_delete = []
            async for message in channel.history(limit=100):
                if message.author == bot.user:
                    messages_to_delete.append(message)

            if messages_to_delete:
                await channel.delete_messages(messages_to_delete)
                deleted_messages = len(messages_to_delete)

        await interaction.followup.send(f"✅ Purged all reminders and {deleted_messages} messages from the reminder channel.", ephemeral=True)


@bot.tree.command(name="debug", description="View your current reminder settings.")
async def debug(interaction: discord.Interaction):
    user_id = str(interaction.user.id)  # Convert to string for JSON compatibility

    # Load user settings from JSON file
    try:
        with open(SETTINGS_FILE, "r") as f:
            user_settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        user_settings = {}  # If file is missing or corrupted, use empty settings

    # Get the user's settings or default values if missing
    settings = user_settings.get(user_id, {})

    exam_reminder_days = settings.get("exam_reminder_days", DEFAULT_EXAM_REMINDER_DAYS)
    homework_reminder_days = settings.get("homework_reminder_days", DEFAULT_HOMEWORK_REMINDER_DAYS)
    reminder_channel = settings.get("reminder_channel", "Default Channel")

    settings_msg = (
        f"🔧 **Your current settings:**\n"
        f"📅 Exam Reminder Days: {exam_reminder_days}\n"
        f"📅 Homework Reminder Days: {homework_reminder_days}\n"
        f"📢 Reminder Channel ID: {reminder_channel}"
    )

    await interaction.response.send_message(settings_msg, ephemeral=True)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")  # Confirm that the bot has logged in


# Replace with your actual token
TokenDiscord = os.getenv('TOKEN', None)
if not TokenDiscord:
    print("❌ Token not found! Make sure to set the environment variable.")
else:
    bot.run(TokenDiscord)