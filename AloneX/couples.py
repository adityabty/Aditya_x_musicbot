import os
import random
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw
from pyrogram import errors, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message

from AloneX import app
from AloneX.mongo.couples_db import get_couple, save_couple


def today() -> str:
    return datetime.now().strftime("%d/%m/%Y")


def tomorrow() -> str:
    return (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")


def circular(path: str) -> Image.Image:
    img  = Image.open(path).resize((486, 486))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + img.size, fill=255)
    img.putalpha(mask)
    return img


async def safe_get_user(uid: int):
    try:
        return await app.get_users(uid)
    except errors.PeerIdInvalid:
        return None


async def safe_photo(uid: int, name: str):
    fallback = "TEAMXMUSIC/assets/upic.png"
    try:
        chat = await app.get_chat(uid)
        return await app.download_media(chat.photo.big_file_id, file_name=name)
    except Exception:
        return fallback


async def generate_image(chat_id: int, uid1: int, uid2: int, date: str) -> str:
    base = Image.open("TEAMXMUSIC/assets/TEAMX/TEAMXCP.png")
    p1   = await safe_photo(uid1, "pfp1.png")
    p2   = await safe_photo(uid2, "pfp2.png")

    base.paste(circular(p1), (410, 500), circular(p1))
    base.paste(circular(p2), (1395, 500), circular(p2))

    out_path = f"couple_{chat_id}_{date.replace('/','-')}.png"
    base.save(out_path)

    for pf in (p1, p2):
        if Path(pf).name.startswith("pfp") and Path(pf).exists():
            os.remove(pf)

    return out_path


@app.on_message(filters.command("couple"))
async def couples_handler(_, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply("**ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴏɴʟʏ ᴡᴏʀᴋs ɪɴ ɢʀᴏᴜᴘs.**")

    wait = await message.reply("🦋")
    cid  = message.chat.id
    date = today()

    record = await get_couple(cid, date)
    if record:
        uid1, uid2, img_path = record["user1"], record["user2"], record["img"]
        user1 = await safe_get_user(uid1)
        user2 = await safe_get_user(uid2)

        # if users invalid or image missing -> regenerate
        if not (user1 and user2) or not img_path or not Path(img_path).exists():
            record = None

    if not record:
        members = [
            m.user.id async for m in app.get_chat_members(cid, limit=250)
            if not m.user.is_bot
        ]
        if len(members) < 2:
            return await wait.edit("**ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴜsᴇʀs ɪɴ ᴛʜᴇ ɢʀᴏᴜᴘ.**")

        tries = 0
        while tries < 5:
            uid1, uid2 = random.sample(members, 2)
            user1 = await safe_get_user(uid1)
            user2 = await safe_get_user(uid2)
            if user1 and user2:
                break
            tries += 1
        else:
            return await wait.edit("**ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰɪɴᴅ ᴠᴀʟɪᴅ ᴍᴇᴍʙᴇʀꜱ.**")

        img_path = await generate_image(cid, uid1, uid2, date)
        await save_couple(cid, date, {"user1": uid1, "user2": uid2}, img_path)

    caption = (
        "🍓🌸🐇 𝒦𝒶𝓌𝒶𝒾𝒾 𝒞𝑜𝓊𝓅𝓁𝑒 𝑜𝒻 𝓉𝒽𝑒 𝒟𝒶𝓎 🐇🌸🍓\n\n"
        "♡﹕𝒯𝑜𝒹𝒶𝓎’𝓈 𝒞𝓊𝓉𝑒 𝒫𝒶𝒾𝓇﹕\n"
        f"   {user1.mention} 🐰 {user2.mention}\n\n"
        f"📅 𝒩𝑒𝓍𝓉 𝒞𝒽𝑜𝓈𝑒𝓃 𝒞𝑜𝓊𝓅𝓁𝑒﹕ `{tomorrow()}`\n\n"
        "💖 𝑅𝒜𝐼𝒩 𝒷𝓇𝒾𝓃𝑔𝓈 𝓁𝑜𝓋𝑒 — 𝓎𝑜𝓊 𝓂𝒾𝑔𝒽𝓉 𝒷𝑒 𝓃𝑒𝓍𝓉! 🌸"
    )

    await message.reply_photo(img_path, caption=caption)
    await wait.delete()
