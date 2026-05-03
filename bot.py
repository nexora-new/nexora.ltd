import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "reaction_roles.json"

# { guild_id: { message_id: { emoji_str: role_id } } }
reaction_roles: dict = {}


# ─── Data helpers ────────────────────────────────────────────────────────────

def load_data():
    global reaction_roles
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            reaction_roles = json.load(f)
    except FileNotFoundError:
        reaction_roles = {}


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(reaction_roles, f, ensure_ascii=False, indent=2)


# ─── Bot events ──────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    load_data()
    await bot.change_presence(activity=discord.Game(name="!rr help"))
    print(f"✅  บอทพร้อมใช้งาน: {bot.user}  (ID: {bot.user.id})")


# ─── Command group ───────────────────────────────────────────────────────────

@bot.group(name="rr", invoke_without_command=True)
@commands.has_permissions(manage_roles=True)
async def rr(ctx: commands.Context):
    embed = discord.Embed(
        title="🎭 Reaction Role Bot — คำสั่ง",
        color=0x5865F2,
    )
    embed.add_field(
        name="!rr setup <#channel> <หัวข้อ> [คำอธิบาย]",
        value="สร้างข้อความสำหรับกดรับยศในห้องที่ระบุ",
        inline=False,
    )
    embed.add_field(
        name="!rr add <message_id> <emoji> <@role>",
        value="ผูก emoji กับยศ (เพิ่มหลัง setup)",
        inline=False,
    )
    embed.add_field(
        name="!rr remove <message_id> <emoji>",
        value="ลบการผูก emoji-ยศออก",
        inline=False,
    )
    embed.add_field(
        name="!rr list",
        value="แสดงรายการ reaction roles ทั้งหมดในเซิร์ฟเวอร์",
        inline=False,
    )
    embed.set_footer(text="ต้องการสิทธิ์ Manage Roles ในการใช้คำสั่ง")
    await ctx.send(embed=embed)


# ─── !rr setup ───────────────────────────────────────────────────────────────

@rr.command(name="setup")
@commands.has_permissions(manage_roles=True)
async def rr_setup(
    ctx: commands.Context,
    channel: discord.TextChannel,
    title: str,
    *,
    description: str = "กดอิโมจิด้านล่างเพื่อรับยศที่ต้องการ!",
):
    embed = discord.Embed(title=title, description=description, color=0x5865F2)
    embed.set_footer(text="กดอิโมจิเพื่อรับยศ • กดอีกครั้งเพื่อคืนยศ")
    msg = await channel.send(embed=embed)

    gid = str(ctx.guild.id)
    mid = str(msg.id)
    reaction_roles.setdefault(gid, {})[mid] = {}
    save_data()

    await ctx.send(
        f"✅ สร้างข้อความรับยศใน {channel.mention} แล้ว!\n"
        f"Message ID: `{mid}`\n"
        f"ใช้ `!rr add {mid} <emoji> <@role>` เพื่อผูก emoji กับยศ"
    )


# ─── !rr add ─────────────────────────────────────────────────────────────────

@rr.command(name="add")
@commands.has_permissions(manage_roles=True)
async def rr_add(
    ctx: commands.Context,
    message_id: str,
    emoji: str,
    role: discord.Role,
):
    gid = str(ctx.guild.id)
    data = reaction_roles.get(gid, {})

    if message_id not in data:
        await ctx.send(
            "❌ ไม่พบ Message ID นี้ในระบบ\n"
            "ใช้ `!rr setup` เพื่อสร้างข้อความก่อน หรือตรวจสอบ ID อีกครั้ง"
        )
        return

    # Find the message across all text channels
    target_msg: discord.Message | None = None
    for ch in ctx.guild.text_channels:
        try:
            target_msg = await ch.fetch_message(int(message_id))
            break
        except Exception:
            continue

    if target_msg is None:
        await ctx.send("❌ ไม่พบข้อความ ตรวจสอบว่าบอทเข้าถึงห้องนั้นได้")
        return

    reaction_roles[gid][message_id][emoji] = role.id
    save_data()

    try:
        await target_msg.add_reaction(emoji)
    except discord.HTTPException:
        await ctx.send("⚠️ เพิ่ม emoji ในข้อความไม่ได้ (อาจเป็น emoji ที่ไม่รองรับ) แต่บันทึกข้อมูลแล้ว")

    await _refresh_embed(target_msg, gid, message_id, ctx.guild)
    await ctx.send(f"✅ ผูก {emoji} → {role.mention} แล้ว!")


# ─── !rr remove ──────────────────────────────────────────────────────────────

@rr.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def rr_remove(ctx: commands.Context, message_id: str, emoji: str):
    gid = str(ctx.guild.id)
    data = reaction_roles.get(gid, {}).get(message_id, {})

    if emoji not in data:
        await ctx.send("❌ ไม่พบ emoji นี้ใน message ID ดังกล่าว")
        return

    del reaction_roles[gid][message_id][emoji]
    save_data()

    # Try to find & update the message
    for ch in ctx.guild.text_channels:
        try:
            msg = await ch.fetch_message(int(message_id))
            await _refresh_embed(msg, gid, message_id, ctx.guild)
            break
        except Exception:
            continue

    await ctx.send(f"✅ ลบ {emoji} ออกจาก message `{message_id}` แล้ว")


# ─── !rr list ────────────────────────────────────────────────────────────────

@rr.command(name="list")
@commands.has_permissions(manage_roles=True)
async def rr_list(ctx: commands.Context):
    gid = str(ctx.guild.id)
    guild_data = reaction_roles.get(gid, {})

    if not guild_data:
        await ctx.send("ยังไม่มี reaction roles ในเซิร์ฟเวอร์นี้")
        return

    embed = discord.Embed(title="📋 Reaction Roles ทั้งหมด", color=0x5865F2)
    for mid, emojis in guild_data.items():
        if emojis:
            lines = "\n".join(f"{e} → <@&{r}>" for e, r in emojis.items())
            embed.add_field(name=f"Message ID: {mid}", value=lines, inline=False)

    if not embed.fields:
        embed.description = "ยังไม่มียศที่ผูกไว้"

    await ctx.send(embed=embed)


# ─── Reaction events ─────────────────────────────────────────────────────────

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id or payload.guild_id is None:
        return

    gid = str(payload.guild_id)
    mid = str(payload.message_id)
    emoji = str(payload.emoji)

    role_id = reaction_roles.get(gid, {}).get(mid, {}).get(emoji)
    if not role_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    member = guild.get_member(payload.user_id)
    role = guild.get_role(role_id)
    if member and role:
        try:
            await member.add_roles(role, reason="Reaction Role")
            print(f"➕ เพิ่มยศ '{role.name}' ให้ {member} ({emoji})")
        except discord.Forbidden:
            print(f"⚠️  ไม่มีสิทธิ์เพิ่มยศ '{role.name}'")


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None:
        return

    gid = str(payload.guild_id)
    mid = str(payload.message_id)
    emoji = str(payload.emoji)

    role_id = reaction_roles.get(gid, {}).get(mid, {}).get(emoji)
    if not role_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    member = guild.get_member(payload.user_id)
    role = guild.get_role(role_id)
    if member and role:
        try:
            await member.remove_roles(role, reason="Reaction Role removed")
            print(f"➖ ลบยศ '{role.name}' จาก {member} ({emoji})")
        except discord.Forbidden:
            print(f"⚠️  ไม่มีสิทธิ์ลบยศ '{role.name}'")


# ─── Error handler ────────────────────────────────────────────────────────────

@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้ (ต้องการ Manage Roles)")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ ขาด argument: `{error.param.name}` — พิมพ์ `!rr` เพื่อดูวิธีใช้")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ argument ไม่ถูกต้อง — ตรวจสอบการ mention ยศหรือห้อง")
    elif isinstance(error, commands.CommandNotFound):
        pass  # ignore unknown commands silently
    else:
        print(f"Unhandled error: {error}")


# ─── Embed refresh helper ─────────────────────────────────────────────────────

async def _refresh_embed(
    message: discord.Message,
    guild_id: str,
    message_id: str,
    guild: discord.Guild,
):
    """Rebuild the reaction-role embed with current emoji-role list."""
    if not message.embeds:
        return

    old = message.embeds[0]
    # Separate original description from the auto-generated roles table
    original_desc = (old.description or "").split("\n\n📌")[0]

    roles_data = reaction_roles.get(guild_id, {}).get(message_id, {})
    if roles_data:
        table = "\n".join(f"{e}  →  <@&{r}>" for e, r in roles_data.items())
        full_desc = original_desc + f"\n\n📌 **ยศที่รับได้:**\n{table}"
    else:
        full_desc = original_desc

    new_embed = discord.Embed(
        title=old.title,
        description=full_desc,
        color=old.color,
    )
    if old.footer:
        new_embed.set_footer(text=old.footer.text)

    await message.edit(embed=new_embed)


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("กำหนด DISCORD_TOKEN ใน .env หรือ environment variable ก่อน!")
    bot.run(TOKEN)
