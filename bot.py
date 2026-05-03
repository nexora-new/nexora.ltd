import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "reaction_roles.json"
reaction_roles: dict = {}


# ─── Data helpers ─────────────────────────────────────────────────────────────

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


# ─── Bot ready ────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    load_data()
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Sync error: {e}")
    await bot.change_presence(activity=discord.Game(name="/set • กดรับยศ"))
    print(f"✅ พร้อมใช้งาน: {bot.user}  (ID: {bot.user.id})")


# ─── Autocomplete ─────────────────────────────────────────────────────────────

async def msg_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    gid = str(interaction.guild_id)
    return [
        app_commands.Choice(name=f"ID: {mid}", value=mid)
        for mid in reaction_roles.get(gid, {}).keys()
        if current in mid
    ][:25]


# ─── /set  (คำสั่งหลัก — จบในขั้นตอนเดียว) ───────────────────────────────────

@bot.tree.command(
    name="set",
    description="🎭 สร้างข้อความรับยศพร้อม emoji ในคำสั่งเดียว",
)
@app_commands.describe(
    channel     = "ห้องที่จะส่งข้อความ",
    title       = "หัวข้อข้อความ",
    description = "คำอธิบาย (ไม่บังคับ)",
    image       = "รูปภาพ (ไม่บังคับ)",
    emoji1="อิโมจิที่ 1",  role1="ยศที่ 1",
    emoji2="อิโมจิที่ 2",  role2="ยศที่ 2",
    emoji3="อิโมจิที่ 3",  role3="ยศที่ 3",
    emoji4="อิโมจิที่ 4",  role4="ยศที่ 4",
    emoji5="อิโมจิที่ 5",  role5="ยศที่ 5",
)
@app_commands.checks.has_permissions(manage_roles=True)
async def set_cmd(
    interaction: discord.Interaction,
    channel:     discord.TextChannel,
    title:       str,
    description: str                   = "กดอิโมจิด้านล่างเพื่อรับยศที่ต้องการ!",
    image:       discord.Attachment | None = None,
    emoji1: str | None = None,  role1: discord.Role | None = None,
    emoji2: str | None = None,  role2: discord.Role | None = None,
    emoji3: str | None = None,  role3: discord.Role | None = None,
    emoji4: str | None = None,  role4: discord.Role | None = None,
    emoji5: str | None = None,  role5: discord.Role | None = None,
):
    await interaction.response.defer(ephemeral=True)

    # รวม emoji-role pairs ที่กรอกมา
    pairs = [
        (e, r)
        for e, r in [
            (emoji1, role1), (emoji2, role2), (emoji3, role3),
            (emoji4, role4), (emoji5, role5),
        ]
        if e and r
    ]

    # ตรวจสอบลำดับ role ของบอท
    bad_roles = [r for _, r in pairs if interaction.guild.me.top_role <= r]
    if bad_roles:
        names = ", ".join(r.mention for r in bad_roles)
        await interaction.followup.send(
            f"❌ บอทไม่สามารถให้ยศ {names} ได้\n"
            "ยศของบอทต้องอยู่สูงกว่าในรายการ Server Settings → Roles",
            ephemeral=True,
        )
        return

    # สร้าง embed
    desc_full = description
    if pairs:
        table = "\n".join(f"{e}  →  {r.mention}" for e, r in pairs)
        desc_full = description + f"\n\n📌 **ยศที่รับได้:**\n{table}"

    embed = discord.Embed(title=title, description=desc_full, color=0x5865F2)
    embed.set_footer(text="กดอิโมจิเพื่อรับยศ • กดอีกครั้งเพื่อคืนยศ")
    if image:
        embed.set_image(url=image.url)

    msg = await channel.send(embed=embed)

    # บันทึกข้อมูล
    gid = str(interaction.guild_id)
    mid = str(msg.id)
    reaction_roles.setdefault(gid, {})[mid] = {}

    for emoji_str, role in pairs:
        reaction_roles[gid][mid][emoji_str] = role.id
        try:
            await msg.add_reaction(emoji_str)
        except discord.HTTPException:
            pass  # emoji ผิดรูปแบบ / custom ที่ไม่มี

    save_data()

    result_lines = [f"✅ สร้างข้อความรับยศใน {channel.mention} แล้ว!"]
    if pairs:
        result_lines.append("**ผูกแล้ว:**")
        result_lines += [f"• {e} → {r.mention}" for e, r in pairs]
    else:
        result_lines.append("⚠️ ยังไม่ได้ผูก emoji ไหน — ใช้ `/add` เพิ่มได้ภายหลัง")

    await interaction.followup.send("\n".join(result_lines), ephemeral=True)


# ─── /add  (เพิ่ม emoji ภายหลัง) ────────────────────────────────────────────

@bot.tree.command(name="add", description="➕ เพิ่ม emoji-ยศ เข้าข้อความที่มีอยู่")
@app_commands.describe(
    message_id="ข้อความรับยศ (เลือกจากรายการ)",
    emoji="อิโมจิ",
    role="ยศ",
)
@app_commands.autocomplete(message_id=msg_autocomplete)
@app_commands.checks.has_permissions(manage_roles=True)
async def add_cmd(
    interaction: discord.Interaction,
    message_id: str,
    emoji: str,
    role: discord.Role,
):
    await interaction.response.defer(ephemeral=True)
    gid = str(interaction.guild_id)

    if message_id not in reaction_roles.get(gid, {}):
        await interaction.followup.send("❌ ไม่พบข้อความนี้ในระบบ ใช้ `/set` เพื่อสร้างใหม่", ephemeral=True)
        return

    if interaction.guild.me.top_role <= role:
        await interaction.followup.send(f"❌ ยศของบอทต้องสูงกว่า {role.mention}", ephemeral=True)
        return

    target_msg = await _find_message(interaction.guild, int(message_id))
    if not target_msg:
        await interaction.followup.send("❌ ไม่พบข้อความ", ephemeral=True)
        return

    reaction_roles[gid][message_id][emoji] = role.id
    save_data()

    try:
        await target_msg.add_reaction(emoji)
    except discord.HTTPException:
        pass

    await _refresh_embed(target_msg, gid, message_id)
    await interaction.followup.send(f"✅ เพิ่ม {emoji} → {role.mention} แล้ว!", ephemeral=True)


# ─── /remove  (ลบ emoji) ─────────────────────────────────────────────────────

async def emoji_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    gid = str(interaction.guild_id)
    mid = getattr(interaction.namespace, "message_id", None)
    emojis = list(reaction_roles.get(gid, {}).get(str(mid), {}).keys()) if mid else []
    return [app_commands.Choice(name=e, value=e) for e in emojis if current in e][:25]


@bot.tree.command(name="remove", description="➖ ลบ emoji-ยศออกจากข้อความ")
@app_commands.describe(message_id="ข้อความรับยศ", emoji="อิโมจิที่จะลบ")
@app_commands.autocomplete(message_id=msg_autocomplete, emoji=emoji_autocomplete)
@app_commands.checks.has_permissions(manage_roles=True)
async def remove_cmd(
    interaction: discord.Interaction,
    message_id: str,
    emoji: str,
):
    await interaction.response.defer(ephemeral=True)
    gid = str(interaction.guild_id)

    if emoji not in reaction_roles.get(gid, {}).get(message_id, {}):
        await interaction.followup.send("❌ ไม่พบ emoji นี้", ephemeral=True)
        return

    del reaction_roles[gid][message_id][emoji]
    save_data()

    msg = await _find_message(interaction.guild, int(message_id))
    if msg:
        try:
            await msg.clear_reaction(emoji)
        except Exception:
            pass
        await _refresh_embed(msg, gid, message_id)

    await interaction.followup.send(f"✅ ลบ {emoji} แล้ว", ephemeral=True)


# ─── /list ────────────────────────────────────────────────────────────────────

@bot.tree.command(name="list", description="📋 แสดง reaction roles ทั้งหมด")
@app_commands.checks.has_permissions(manage_roles=True)
async def list_cmd(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    data = {m: e for m, e in reaction_roles.get(gid, {}).items() if e}

    if not data:
        await interaction.response.send_message(
            "ยังไม่มี reaction roles — ใช้ `/set` เพื่อสร้าง", ephemeral=True
        )
        return

    embed = discord.Embed(title="📋 Reaction Roles", color=0x5865F2)
    for mid, emojis in data.items():
        lines = "\n".join(f"{e} → <@&{r}>" for e, r in emojis.items())
        embed.add_field(name=f"📌 Message ID: {mid}", value=lines, inline=False)
    embed.set_footer(text=f"ทั้งหมด {sum(len(v) for v in data.values())} การผูก")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─── /delete ──────────────────────────────────────────────────────────────────

@bot.tree.command(name="delete", description="🗑️ ลบข้อความรับยศออกจากระบบ")
@app_commands.describe(message_id="ข้อความที่จะลบ (เลือกจากรายการ)")
@app_commands.autocomplete(message_id=msg_autocomplete)
@app_commands.checks.has_permissions(manage_roles=True)
async def delete_cmd(interaction: discord.Interaction, message_id: str):
    await interaction.response.defer(ephemeral=True)
    gid = str(interaction.guild_id)

    if message_id not in reaction_roles.get(gid, {}):
        await interaction.followup.send("❌ ไม่พบ Message ID นี้", ephemeral=True)
        return

    del reaction_roles[gid][message_id]
    save_data()

    msg = await _find_message(interaction.guild, int(message_id))
    if msg:
        try:
            await msg.delete()
        except Exception:
            pass

    await interaction.followup.send("✅ ลบข้อความรับยศแล้ว", ephemeral=True)


# ─── Reaction events ──────────────────────────────────────────────────────────

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id or not payload.guild_id:
        return
    await _toggle_role(payload, add=True)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if not payload.guild_id:
        return
    await _toggle_role(payload, add=False)


async def _toggle_role(payload: discord.RawReactionActionEvent, add: bool):
    role_id = (
        reaction_roles
        .get(str(payload.guild_id), {})
        .get(str(payload.message_id), {})
        .get(str(payload.emoji))
    )
    if not role_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    member = guild.get_member(payload.user_id)
    role   = guild.get_role(role_id)
    if not (member and role):
        return

    try:
        if add:
            await member.add_roles(role, reason="Reaction Role")
            print(f"➕ {role.name} → {member} ({payload.emoji})")
        else:
            await member.remove_roles(role, reason="Reaction Role removed")
            print(f"➖ {role.name} ← {member} ({payload.emoji})")
    except discord.Forbidden:
        print(f"⚠️  ไม่มีสิทธิ์จัดการยศ '{role.name}'")


# ─── Error handler ────────────────────────────────────────────────────────────

@bot.tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ ต้องการสิทธิ์ Manage Roles"
    elif isinstance(error, app_commands.BotMissingPermissions):
        msg = "❌ บอทไม่มีสิทธิ์เพียงพอ"
    else:
        msg = f"❌ เกิดข้อผิดพลาด: {error}"
        print(f"[Error] {error}")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _find_message(guild: discord.Guild, message_id: int) -> discord.Message | None:
    for ch in guild.text_channels:
        try:
            return await ch.fetch_message(message_id)
        except Exception:
            continue
    return None


async def _refresh_embed(message: discord.Message, guild_id: str, message_id: str):
    if not message.embeds:
        return

    old = message.embeds[0]
    base_desc = (old.description or "").split("\n\n📌")[0]
    roles_data = reaction_roles.get(guild_id, {}).get(message_id, {})

    if roles_data:
        table = "\n".join(f"{e}  →  <@&{r}>" for e, r in roles_data.items())
        full_desc = base_desc + f"\n\n📌 **ยศที่รับได้:**\n{table}"
    else:
        full_desc = base_desc

    new_embed = discord.Embed(title=old.title, description=full_desc, color=old.color)
    if old.image:
        new_embed.set_image(url=old.image.url)
    if old.footer:
        new_embed.set_footer(text=old.footer.text)

    await message.edit(embed=new_embed)


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("กำหนด DISCORD_TOKEN ใน .env ก่อน!")
    bot.run(TOKEN)
