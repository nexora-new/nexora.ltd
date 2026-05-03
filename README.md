# 🎭 Discord Reaction Role Bot

บอทกดอิโมจิรับยศสำหรับ Discord — deploy บน Railway ผ่าน GitHub

---

## ✨ ฟีเจอร์

- กดอิโมจิ → รับยศอัตโนมัติ
- ถอนอิโมจิ → คืนยศอัตโนมัติ
- รองรับหลาย message / หลาย emoji ต่อเซิร์ฟเวอร์
- embed อัปเดตอัตโนมัติเมื่อเพิ่ม/ลบ role

---

## 🚀 วิธี Deploy

### 1. สร้าง Discord Bot

1. ไปที่ [Discord Developer Portal](https://discord.com/developers/applications)
2. **New Application** → ตั้งชื่อ → **Bot** → **Add Bot**
3. เปิด Privileged Gateway Intents ทั้ง 3 ตัว:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
   - ✅ Presence Intent
4. **Reset Token** → คัดลอก Token ไว้
5. **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Manage Roles`, `Send Messages`, `Read Message History`, `Add Reactions`, `Embed Links`
6. เปิด URL ที่ได้เพื่อเชิญบอทเข้าเซิร์ฟเวอร์

### 2. Push ขึ้น GitHub

```bash
git init
git add .
git commit -m "init reaction role bot"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

> ⚠️ อย่า push ไฟล์ `.env` หรือ `reaction_roles.json` ขึ้น GitHub

### 3. Deploy บน Railway

1. ไปที่ [railway.app](https://railway.app) → **New Project**
2. เลือก **Deploy from GitHub repo** → เลือก repo ที่สร้าง
3. ไปที่แท็บ **Variables** → เพิ่ม:
   ```
   DISCORD_TOKEN = (วาง token ของบอทที่นี่)
   ```
4. Railway จะ build และ deploy อัตโนมัติ ✅

> 💡 **หมายเหตุ:** Railway มี ephemeral filesystem — ข้อมูล `reaction_roles.json` จะหายเมื่อ redeploy
> แนะนำให้ใช้ Railway Volume หรือ re-setup หลัง deploy ใหม่

---

## 📖 Slash Commands

> ต้องมีสิทธิ์ **Manage Roles** ในการใช้คำสั่ง (เฉพาะผู้ใช้ที่มีสิทธิ์เท่านั้นจะเห็นตัวเลือก)

| คำสั่ง | ตัวเลือก | คำอธิบาย |
|--------|---------|----------|
| `/setup` | `channel` `title` `description` `image` | สร้างข้อความรับยศ |
| `/add` | `message_id` `emoji` `role` | ผูก emoji กับยศ |
| `/remove` | `message_id` `emoji` | ลบการผูก emoji-ยศ |
| `/list` | — | แสดงรายการทั้งหมด |
| `/delete-message` | `message_id` | ลบข้อความรับยศออกจากระบบ |

### ✨ ฟีเจอร์พิเศษ
- **Autocomplete**: `message_id` และ `emoji` จะมีตัวเลือกให้คลิกได้เลย ไม่ต้องพิมพ์เอง
- **Ephemeral**: คำสั่งทั้งหมดตอบกลับแบบ "เห็นเฉพาะคนใช้" ไม่รกห้อง
- **Image support**: `/setup` รองรับอัปโหลดรูปภาพได้โดยตรง

### ตัวอย่างการใช้งาน

```
/setup channel:#รับยศ title:เลือกยศของคุณ description:กดอิโมจิด้านล่าง

# message_id จะปรากฎใน autocomplete ของ /add อัตโนมัติ
/add message_id:[เลือกจากรายการ] emoji:🎮 role:@Gamer
/add message_id:[เลือกจากรายการ] emoji:🎵 role:@Music
/list
```

---

## 🛠 รัน Local (สำหรับทดสอบ)

```bash
pip install -r requirements.txt
cp .env.example .env
# แก้ไข .env ใส่ DISCORD_TOKEN จริง
python bot.py
```

---

## 📁 โครงสร้างไฟล์

```
discord-reaction-role-bot/
├── bot.py              # โค้ดหลักของบอท
├── requirements.txt    # Python dependencies
├── Procfile            # Railway/Heroku start command
├── railway.toml        # Railway config
├── .env.example        # ตัวอย่าง environment variables
├── .gitignore
└── README.md
```
