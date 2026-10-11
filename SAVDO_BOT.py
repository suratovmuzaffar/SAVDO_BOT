import asyncio
import html
import json
import logging
import os
import re
import time
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
raw_admins = os.getenv("ADMINS")
ADMINS = list(map(int, raw_admins.split(","))) if raw_admins else []
PAYMENT_CARDS = [
    (label, os.getenv(env_name, "").strip())
    for label, env_name in (("Uzcard", "UZCARD"), ("Humo", "HUMO"), ("Visa", "VISA"))
    if os.getenv(env_name, "").strip()
]
bot = Bot(token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
pending_deals = {}
ended_deals = {}
faol_savdolar = set()
savdo_ma_lumotlari = {}
next_trade_number = 1
known_users = {}
state_path = Path(__file__).resolve().parent / ".savdo_state.json"

def load_state():
    global next_trade_number
    try:
        if not state_path.exists():
            return
        data = json.loads(state_path.read_text(encoding="utf-8"))
        next_trade_number = int(data.get("next_trade_number", 1))
        known_users.update(data.get("known_users", {}))
        for item in data.get("deals", []):
            deal_key = (int(item["chat_id"]), int(item["trade_number"]))
            deal = {
                "sotuvchi_id": int(item["sotuvchi_id"]),
                "oluvchi_id": int(item["oluvchi_id"]),
                "status": item.get("status", "Rozilik kutilmoqda"),
                "created_at": float(item.get("created_at", 0)),
            }
            savdo_ma_lumotlari[deal_key] = deal
            if deal["status"] == "Rozilik kutilmoqda":
                pending_deals[deal_key] = set(map(int, item.get("consented", [])))
            if deal["status"] == "Faol":
                faol_savdolar.add(deal_key)
            if item.get("ended"):
                ended_deals[deal_key] = set(map(int, item["ended"]))
        if savdo_ma_lumotlari:
            next_trade_number = max(next_trade_number, max(key[1] for key in savdo_ma_lumotlari) + 1)
        logging.info("Savdo holati diskdan yuklandi: %s ta savdo", len(savdo_ma_lumotlari))
    except Exception as e:
        logging.error("SAVDO HOLATINI YUKLASH XATOSI: %s", e)

def save_state():
    try:
        deals = []
        for (chat_id, trade_number), deal in savdo_ma_lumotlari.items():
            deals.append({
                "chat_id": chat_id,
                "trade_number": trade_number,
                "sotuvchi_id": deal["sotuvchi_id"],
                "oluvchi_id": deal["oluvchi_id"],
                "status": deal["status"],
                "created_at": deal.get("created_at", 0),
                "consented": list(pending_deals.get((chat_id, trade_number), set())),
                "ended": list(ended_deals.get((chat_id, trade_number), set())),
            })
        data = {"next_trade_number": next_trade_number, "deals": deals, "known_users": known_users}
        temp_path = state_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(state_path)
    except Exception as e:
        logging.error("SAVDO HOLATINI SAQLASH XATOSI: %s", e)

def remember_user(chat_id: int, user: types.User):
    prefix = f"{chat_id}:"
    stale_keys = [key for key, value in known_users.items() if key.startswith(prefix) and value == user.id]
    for key in stale_keys:
        known_users.pop(key, None)
    changed = bool(stale_keys)
    if user.username:
        key = f"{prefix}{user.username.lower()}"
        if known_users.get(key) != user.id:
            known_users[key] = user.id
            changed = True
    if changed:
        save_state()

def command_parts(message: types.Message) -> list[str]:
    """Buyruq ichidagi bosiladigan foydalanuvchi havolalarini ID/username tokeniga aylantiradi."""
    text = message.text or ""
    replacements = []
    for entity in message.entities or []:
        if entity.type not in ("text_mention", "text_link"):
            continue
        start_units = entity.offset
        end_units = entity.offset + entity.length
        start = end = 0
        units = 0
        for index, char in enumerate(text):
            if units == start_units:
                start = index
            if units >= end_units:
                end = index
                break
            units += len(char.encode("utf-16-le")) // 2
        else:
            end = len(text)
        replacement = None
        if entity.user:
            replacement = str(entity.user.id)
        elif entity.url:
            linked_id = re.search(r"tg://user\?id=(\d+)", entity.url)
            linked_username = re.search(r"(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{5,})", entity.url, re.IGNORECASE)
            if linked_id:
                replacement = linked_id.group(1)
            elif linked_username:
                replacement = "@" + linked_username.group(1)
        if replacement:
            replacements.append((start, end, replacement))
    for start, end, replacement in sorted(replacements, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text.split()

async def resolve_user_id(token: str, message: types.Message, mention_index: int = 0) -> int:
    token = token.strip()
    if token.isdigit():
        return int(token)
    tg_link = re.search(r"tg://user\?id=(\d+)", token)
    if tg_link:
        return int(tg_link.group(1))

    username_match = re.search(r"(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{5,})(?:\?.*)?/?$", token, re.IGNORECASE)
    username = username_match.group(1) if username_match else token.lstrip("@")
    username_key = f"{message.chat.id}:{username.lower()}"
    text = message.text or ""
    encoded_text = text.encode("utf-16-le")
    for entity in message.entities or []:
        start = entity.offset * 2
        end = (entity.offset + entity.length) * 2
        entity_text = encoded_text[start:end].decode("utf-16-le", errors="ignore")
        if entity_text == token and entity.url:
            linked_id = re.search(r"tg://user\?id=(\d+)", entity.url)
            if linked_id:
                return int(linked_id.group(1))
            linked_username = re.search(r"(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{5,})", entity.url, re.IGNORECASE)
            if linked_username:
                linked_key = f"{message.chat.id}:{linked_username.group(1).lower()}"
                if linked_key in known_users:
                    return int(known_users[linked_key])
    matching_users = []
    for entity in message.entities or []:
        if not entity.user:
            continue
        start = entity.offset * 2
        end = (entity.offset + entity.length) * 2
        entity_text = encoded_text[start:end].decode("utf-16-le", errors="ignore")
        if entity_text == token or (entity.user.username or "").lower() == username.lower():
            matching_users.append(entity.user)
    if matching_users:
        chosen = matching_users[min(mention_index, len(matching_users) - 1)]
        return chosen.id
    if username_key in known_users:
        return int(known_users[username_key])
    if username_match or token.startswith("@"):
        try:
            members = await bot.get_chat_administrators(message.chat.id)
            for member in members:
                if (member.user.username or "").lower() == username.lower():
                    return member.user.id
        except Exception as e:
            logging.debug("Admin username qidiruvi bajarilmadi: %s", e)
    raise ValueError(
        f"{token} topilmadi. Username botga tanish emas. ID yoki tg://user?id=ID profil havolasidan foydalaning."
    )

load_state()
# ^ --- BOT SOZLAMMALARI --- ^
async def is_admin_or_owner(chat_id: int, user_id: int) -> bool:
    """ADMIN YOKI OWNER EKANLIGINI TEKSHIRADI"""
    try:
        if user_id in ADMINS:
            return True
        members = await bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in members)
    except:
        return False
async def promote_trade_user(chat_id: int, user_id: int):
    """Savdo qatnashchisiga faqat adminlik maqomini beradi, qo‘shimcha huquqlarsiz."""
    try:
        await bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False,
        )
        return True, None
    except Exception as e:
        logging.error(f"ADMIN QILISH XATOLIGI: {e}")
        return False, str(e)

async def demote_trade_user(chat_id: int, user_id: int):
    """Bot bergan adminlik huquqlarini olib tashlaydi."""
    try:
        await bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            is_anonymous=False,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False,
        )
        return True
    except Exception as e:
        logging.error(f"ADMINLIKDAN OLISH XATOLIGI: {e}")
        return False
async def get_user_info(user_id: int) -> str:
    """FOYDALANUVCHI MA'LUMOTINI OLADI (faqat ID bilan)"""
    return f"<a href='tg://user?id={user_id}'>ID: {user_id}</a>"
async def grant_permissions(chat_id: int, oluvchi_id: int, sotuvchi_id: int, trade_number: int, message: types.Message):
    """OLUVCHI VA SOTUVCHINI ADMIN QILADI VA ADMINLARGA XABAR YUBORADI"""
    oluvchi_info = await get_user_info(oluvchi_id)
    sotuvchi_info = await get_user_info(sotuvchi_id)
    oluvchi_success, oluvchi_error = await promote_trade_user(chat_id, oluvchi_id)
    sotuvchi_success, sotuvchi_error = await promote_trade_user(chat_id, sotuvchi_id)
    text = f"⬆️ <b>SAVDO #{trade_number} ADMINLIGI NATIJASI</b>\n\n"
    if oluvchi_success:
        text += f"✅ <b>OLUVCHI</b> {oluvchi_info} ADMIN QILINDI — SAVDO #{trade_number}\n"
    else:
        text += f"⚠️ OLUVCHIGA ADMINLIK BERILMADI: <code>{oluvchi_error}</code>\n"
    if sotuvchi_success:
        text += f"✅ <b>SOTUVCHI</b> {sotuvchi_info} ADMIN QILINDI — SAVDO #{trade_number}\n"
    else:
        text += f"⚠️ SOTUVCHIGA ADMINLIK BERILMADI: <code>{sotuvchi_error}</code>\n"
    if oluvchi_success and sotuvchi_success:
        text += "\n✅ Ikkala qatnashchiga ham adminlik berildi."
    else:
        text += "\n❗ Savdo to‘liq boshlanmadi. Bot huquqlarini tekshirib, /start buyrug‘ini qayta yuboring."
    await message.answer(text)
    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logging.warning(f"Admin ID {admin_id} ga xabar yuborilmadi: {e}")
    return oluvchi_success and sotuvchi_success
# --- YANGI FUNKSIYA: FOYDALANUVCHILARNI MUTE QILISH ---
async def revoke_permissions(chat_id: int, oluvchi_id: int, sotuvchi_id: int, trade_number: int, message: types.Message):
    """OLUVCHI VA SOTUVCHIDAN ADMINLIK OLINDI VA ADMINLARGA XABAR YUBORILDI"""
    oluvchi_info = await get_user_info(oluvchi_id)
    sotuvchi_info = await get_user_info(sotuvchi_id)
    oluvchi_success = await demote_trade_user(chat_id, oluvchi_id)
    sotuvchi_success = await demote_trade_user(chat_id, sotuvchi_id)
    text = f"⬇️ <b>SAVDO #{trade_number} YAKUNLANDI</b>\n\n"
    if oluvchi_success:
        text += f"✅ <b>OLUVCHI</b> {oluvchi_info} DAN ADMINLIK OLINDI — SAVDO #{trade_number}\n"
    else:
        text += f"⚠️ OLUVCHIDAN ADMINLIK OLISHDA XATOLIK!\n"
    if sotuvchi_success:
        text += f"✅ <b>SOTUVCHI</b> {sotuvchi_info} DAN ADMINLIK OLINDI — SAVDO #{trade_number}\n"
    else:
        text += f"⚠️ SOTUVCHIDAN ADMINLIK OLISHDA XATOLIK!\n"
    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logging.warning(f"Admin ID {admin_id} ga xabar yuborilmadi: {e}")
    return oluvchi_success and sotuvchi_success
# --- SAVDONI BEKOR QILISH ---
async def timeout_cancel(chat_id: int, trade_number: int, wait_seconds: float = 600):
    """10 daqiqa ichida rozilik bermasa savdoni bekor qiladi"""
    await asyncio.sleep(wait_seconds)
    deal_key = (chat_id, trade_number)
    if deal_key in pending_deals:
        del pending_deals[deal_key]
        savdo_ma_lumotlari.pop(deal_key, None)
        save_state()
        await bot.send_message(
            chat_id,
            f"⏳ <b>SAVDO #{trade_number} BEKOR QILINDI</b>\n❌ 10 daqiqada ikkala tomon rozilik bermadi.")
# --- SAVDO BOSHLANDI ROZIMISIZ TUGMASI ---
@dp.callback_query(F.data.startswith("savdo_start"))
async def on_savdo_start_clicked(call: types.CallbackQuery):
    """ROZIMAN TUGMASI BOSILGANDA"""
    try:
        trade_number = int(call.data.split(":")[1])
        user_id = call.from_user.id
        deal_key = (call.message.chat.id, trade_number)
        deal = savdo_ma_lumotlari.get(deal_key)
        if deal_key not in pending_deals:
            await call.answer("⚠️ BU SAVDO TOPILMADI!", show_alert=True)
            return
        oluvchi_id = deal["oluvchi_id"]
        sotuvchi_id = deal["sotuvchi_id"]
        if user_id not in [oluvchi_id, sotuvchi_id]:
            await call.answer("⚠️ SIZ BU SAVDOGA TEGISHLI EMASSIZ!", show_alert=True)
            return
        remember_user(call.message.chat.id, call.from_user)
        if user_id in pending_deals[deal_key]:
            await call.answer("⏳ Siz allaqachon rozilik bildirgansiz.", show_alert=True)
            return
        pending_deals[deal_key].add(user_id)
        save_state()
        if pending_deals[deal_key] == {oluvchi_id}:
            text = "🫱 OLUCHI ROZI"
        elif pending_deals[deal_key] == {sotuvchi_id}:
            text = "🫲 SOTUVCHI ROZI"
        elif pending_deals[deal_key] == {oluvchi_id, sotuvchi_id}:
            text = "🤝 IKKALA TOMON ROZI"
        new_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=f"savdo_start:{trade_number}")]])
        await call.message.edit_reply_markup(reply_markup=new_markup)
        if len(pending_deals[deal_key]) == 2:
            promoted = await grant_permissions(call.message.chat.id, oluvchi_id, sotuvchi_id, trade_number, call.message)
            if promoted:
                faol_savdolar.add(deal_key)
                deal["status"] = "Faol"
                if PAYMENT_CARDS:
                    cards_text = "\n".join(
                        f"💳 <b>{label}:</b> <code>{html.escape(number)}</code>"
                        for label, number in PAYMENT_CARDS
                    )
                    await call.message.answer(
                        f"💳 <b>SAVDO #{trade_number}: TO‘LOV QILING</b>\n\n"
                        f"🛒 <a href='tg://user?id={oluvchi_id}'>Oluvchi</a>, savdo uchun to‘lovni quyidagi kartalardan biriga o‘tkazing:\n"
                        f"{cards_text}\n\n"
                        "To‘lovni amalga oshirgach, chekni guruhga yuboring."
                    )
            else:
                deal["status"] = "Adminlikda xatolik"
                await call.message.answer(f"⚠️ Savdo #{trade_number} faol deb belgilanmadi. Xatolikni tuzatib, /start buyrug‘ini qayta yuboring.")
            del pending_deals[deal_key]
            save_state()
    except Exception as e:
        await call.answer(f"⚠️ XATOLIK: {str(e)}", show_alert=True)
# --- SAVDO TUGATILDI MAMNUNMISIZ TUGMASI ---
@dp.callback_query(F.data.startswith("savdo_end"))
async def on_savdo_end_clicked(call: types.CallbackQuery):
    """SAVDO TUGATILDI TUGMASI BOSILGANDA - TUGMANING OZINI YANGILAYDI"""
    try:
        trade_number = int(call.data.split(":")[1])
        user_id = call.from_user.id
        deal_key = (call.message.chat.id, trade_number)
        deal = savdo_ma_lumotlari.get(deal_key)
        if not deal:
            await call.answer("⚠️ SAVDO TOPILMADI!", show_alert=True)
            return
        oluvchi_id = deal["oluvchi_id"]
        sotuvchi_id = deal["sotuvchi_id"]
        if deal_key not in ended_deals:
         ended_deals[deal_key] = set()
        if deal_key not in ended_deals:
            ended_deals[deal_key] = set()
        if user_id not in [oluvchi_id, sotuvchi_id]:
            await call.answer("⚠️ SIZ BU SAVDOGA TEGISHLI EMASSIZ!", show_alert=True)
            return
        if user_id in ended_deals[deal_key]:
            await call.answer("⏳ SIZ ALLAQACHON BOSGANSIZ.", show_alert=True)
            return
        ended_deals[deal_key].add(user_id)
        save_state()
        text = ""
        if ended_deals[deal_key] == {oluvchi_id}:
            text = "🫱 OLUVCHI ROZI"
        elif ended_deals[deal_key] == {sotuvchi_id}:
            text = "🫲 SOTUVCHI ROZI"
        elif ended_deals[deal_key] == {oluvchi_id, sotuvchi_id}:
            text = "🤝 OLUVCHI VA SOTUVCHI ROZI"
        new_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=f"savdo_end:{trade_number}")]])
        await call.message.edit_reply_markup(reply_markup=new_markup)
        if len(ended_deals[deal_key]) == 2:
            del ended_deals[deal_key]
            faol_savdolar.discard(deal_key)
            deal["status"] = "Yakunlandi"
            save_state()
        await call.answer("✅ QABUL QILINDI")
    except Exception as e:
        await call.answer(f"⚠️ XATOLIK: {str(e)}", show_alert=True)
@dp.message(Command("start"))
async def start_savdo(message: types.Message):
    """Savdo uchun sotuvchi va oluvchidan rozilik so‘raydi."""
    global next_trade_number
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("Bu buyruqni savdo guruhida yuboring.")
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ FAQAT GURUH ADMINLARI UCHUN!")
    try:
        parts = command_parts(message)
        if len(parts) != 5:
            return await message.answer(
                "Format: /start FOYDALANUVCHI_ID 1 FOYDALANUVCHI_ID 2\n"
                "1 — sotuvchi, 2 — oluvchi. Misol: /start 111111 1 222222 2"
            )
        first_id = await resolve_user_id(parts[1], message, 0)
        first_role = int(parts[2])
        second_id = await resolve_user_id(parts[3], message, 1)
        second_role = int(parts[4])
        if first_id == second_id or {first_role, second_role} != {1, 2}:
            return await message.answer("⚠️ Ikki xil foydalanuvchi kiriting: bittasi 1 (sotuvchi), bittasi 2 (oluvchi).")
        sotuvchi_id = first_id if first_role == 1 else second_id
        oluvchi_id = first_id if first_role == 2 else second_id
        trade_number = next_trade_number
        next_trade_number += 1
        deal_key = (message.chat.id, trade_number)
        pending_deals[deal_key] = set()
        savdo_ma_lumotlari[deal_key] = {
            "sotuvchi_id": sotuvchi_id,
            "oluvchi_id": oluvchi_id,
            "status": "Rozilik kutilmoqda",
            "created_at": time.time(),
        }
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🤝 SAVDONI BOSHLASHGA ROZIMAN", callback_data=f"savdo_start:{trade_number}")
        ]])
        await message.answer(
            f"🛍 <b>SAVDO #{trade_number} SO‘ROVI</b>\n\n"
            f"🧑‍💼 <b>Sotuvchi:</b> <a href='tg://user?id={sotuvchi_id}'>ID {sotuvchi_id}</a>\n"
            f"🛒 <b>Oluvchi:</b> <a href='tg://user?id={oluvchi_id}'>ID {oluvchi_id}</a>\n\n"
            ("Savdo boshlanishi uchun ikkala tomon ham rozilik tugmasini bosishi kerak."
             + (" To‘lov kartalari savdo faol bo‘lganda oluvchiga ko‘rsatiladi." if PAYMENT_CARDS else "")),
            reply_markup=keyboard,
        )
        save_state()
        elapsed = time.time() - savdo_ma_lumotlari[deal_key]["created_at"]
        asyncio.create_task(timeout_cancel(message.chat.id, trade_number, max(0, 600 - elapsed)))
    except ValueError as e:
        await message.answer(f"⚠️ {html.escape(str(e)) or 'ID va rol raqamlarini to‘g‘ri kiriting.'}")
    except Exception as e:
        await message.answer(f"⚠️ XATOLIK: {html.escape(str(e))}")

@dp.message(Command("end"))
async def end_savdo(message: types.Message):
    """Savdo raqami orqali savdoni yakunlaydi va adminlikni oladi."""
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("Bu buyruqni savdo guruhida yuboring.")
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ FAQAT GURUH ADMINLARI UCHUN!")
    try:
        parts = command_parts(message)
        if len(parts) != 2:
            return await message.answer("Format: /end SAVDO_RAQAMI. Misol: /end 1")
        trade_number = int(parts[1])
        deal_key = (message.chat.id, trade_number)
        deal = savdo_ma_lumotlari.get(deal_key)
        if not deal:
            return await message.answer(f"⚠️ SAVDO #{trade_number} TOPILMADI.")
        if deal["status"] != "Faol":
            return await message.answer(f"⚠️ SAVDO #{trade_number} faol emas (holati: {deal['status']}).")
        sotuvchi_id = deal["sotuvchi_id"]
        oluvchi_id = deal["oluvchi_id"]
        faol_savdolar.discard(deal_key)
        demoted = await revoke_permissions(message.chat.id, oluvchi_id, sotuvchi_id, trade_number, message)
        if not demoted:
            deal["status"] = "Adminlikni olishda xatolik"
            save_state()
            return await message.answer(f"⚠️ SAVDO #{trade_number}: kamida bitta qatnashchidan adminlik olinmadi. Bot huquqlarini tekshiring.")
        deal["status"] = "Yakunlandi"
        save_state()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Savdodan mamnunman", callback_data=f"savdo_end:{trade_number}")
        ]])
        await message.answer(
            f"🏁 <b>SAVDO #{trade_number} YAKUNLANDI</b>\n"
            f"🧑‍💼 Sotuvchi adminligi olindi.\n🛒 Oluvchi adminligi olindi.",
            reply_markup=keyboard,
        )
    except ValueError:
        await message.answer("⚠️ Savdo raqami butun son bo‘lishi kerak.")
    except Exception as e:
        await message.answer(f"⚠️ XATOLIK: {html.escape(str(e))}")
@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    """Foydalanuvchini 1=sotuvchi yoki 2=oluvchi roli bilan admin qiladi."""
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("Bu buyruqni guruhda yuboring.")
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ FAQAT GURUH ADMINLARI UCHUN!")
    try:
        parts = command_parts(message)
        if len(parts) != 3 or int(parts[2]) not in (1, 2):
            return await message.answer("Format: /admin FOYDALANUVCHI_ID 1|2\n1 — sotuvchi, 2 — oluvchi. Misol: /admin 123456789 1")
        user_id, role = await resolve_user_id(parts[1], message), int(parts[2])
        success, error = await promote_trade_user(message.chat.id, user_id)
        role_name = "SOTUVCHI" if role == 1 else "OLUVCHI"
        if success:
            result = f"✅ <b>{role_name}</b> <a href='tg://user?id={user_id}'>ID {user_id}</a> ADMIN QILINDI. SAVDO: qo‘lda berildi."
        else:
            result = f"⚠️ <b>{role_name}</b> ID {user_id} ADMIN QILINMADI: <code>{html.escape(error or '')}</code>"
        await message.answer(result)
    except ValueError as e:
        await message.answer(f"⚠️ {html.escape(str(e)) or 'Foydalanuvchi ID va rolni to‘g‘ri kiriting.'}")

@dp.message(Command("unadmin"))
async def unadmin_command(message: types.Message):
    """Foydalanuvchidan adminlikni oladi."""
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("Bu buyruqni guruhda yuboring.")
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ FAQAT GURUH ADMINLARI UCHUN!")
    try:
        parts = (message.text or "").split()
        if len(parts) != 2:
            return await message.answer("Format: /unadmin FOYDALANUVCHI_ID. Misol: /unadmin 123456789")
        user_id = await resolve_user_id(parts[1], message)
        success = await demote_trade_user(message.chat.id, user_id)
        if success:
            await message.answer(f"✅ <a href='tg://user?id={user_id}'>ID {user_id}</a> ADMINLIKDAN OLINDI.")
        else:
            await message.answer(f"⚠️ ID {user_id} DAN ADMINLIKNI OLISHDA XATOLIK. Bot faqat o‘zi ko‘targan adminni tushira oladi.")
    except ValueError as e:
        await message.answer(f"⚠️ {html.escape(str(e)) or 'Foydalanuvchi ID ni to‘g‘ri kiriting.'}")
# --- YORDAM KOMANDASI ---
@dp.message(Command("help"))
async def help_command(message: types.Message):
    """BARCHA KOMANDALAR RO‘YXATI — FAQAT ADMINLARGA"""
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ FAQAT ADMINLAR VA OWNERLARGA RUXSAT!")
    help_text = """
🤖 <b>SAVDO BOT — BUYRUQLAR</b>

<b>SAVDO OCHISH VA YAKUNLASH:</b>
 /start SOTUVCHI 1 OLUVCHI 2 — ID, tg://user?id=ID havolasi yoki bot guruhda tanigan @username kiriting.
1 — sotuvchi, 2 — oluvchi. Ikkalasi rozilik tugmasini bosgach, bot adminlik beradi.
Misol: <code>/start 111111 1 222222 2</code>
/end SAVDO_RAQAMI — savdoni yakunlab, ikki qatnashchidan adminlikni oladi.

<b>ADMINLIKNI QO‘LDA BOSHQARISH:</b>
/admin FOYDALANUVCHI 1|2 — ID, havola yoki guruhda tanilgan @username bilan admin qiladi.
/unadmin FOYDALANUVCHI — shu turdagi qiymat bilan adminlikni oladi.

<b>HOLAT VA YORDAM:</b>
/status — shu guruhdagi kutilayotgan va faol savdolarni raqami bilan ko‘rsatadi.
/help — ushbu qo‘llanmani ko‘rsatadi.

Savdo raqamlari va holati bot qayta ishga tushganda ham saqlanadi.
Buyruqlarni guruh adminlari yoki .env dagi ADMINS ro‘yxatidagi foydalanuvchilar ishlata oladi.
Oddiy a’zolarning yozish huquqini guruh sozlamalaridan cheklang.
"""
    await message.answer(help_text)

@dp.message(Command("id"))
async def id_command(message: types.Message):
    """Foydalanuvchiga Telegram ID sini beradi."""
    user = message.from_user
    if not user:
        return await message.answer("Foydalanuvchi aniqlanmadi. Botga shaxsiy chatda /id yuboring.")
    remember_user(message.chat.id, user)
    await message.answer(
        f"🆔 Sizning Telegram ID: <code>{user.id}</code>\n"
        "Savdo guruhidagi admin shu ID bilan /start buyrug‘ini yuborishi mumkin."
    )

# --- HAMMA SAVDOLAR TOPLAMI ---
@dp.message(Command("status"))
async def status_command(message: types.Message):
    """Joriy guruhdagi kutilayotgan va faol savdolarni raqamlari bilan ko‘rsatadi."""
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ FAQAT GURUH ADMINLARI UCHUN!")
    rows = []
    for (chat_id, trade_number), deal in sorted(savdo_ma_lumotlari.items(), key=lambda item: item[0][1]):
        if chat_id != message.chat.id or deal["status"] == "Yakunlandi":
            continue
        seller = deal["sotuvchi_id"]
        buyer = deal["oluvchi_id"]
        rows.append(
            f"<b>SAVDO #{trade_number}</b> — {html.escape(deal['status'])}\n"
            f"🧑‍💼 SOTUVCHI: <a href='tg://user?id={seller}'>ID {seller}</a>\n"
            f"🛒 OLUVCHI: <a href='tg://user?id={buyer}'>ID {buyer}</a>"
        )
    if not rows:
        return await message.answer("📭 Bu guruhda kutilayotgan yoki faol savdo yo‘q.")
    await message.answer("📊 <b>SAVDOLAR HOLATI</b>\n\n" + "\n\n".join(rows))

@dp.message()
async def cache_group_usernames(message: types.Message):
    """Guruhda ko‘rilgan foydalanuvchilarning @username'larini keyingi buyruqlar uchun eslab qoladi."""
    if message.chat.type not in ("group", "supergroup"):
        return
    if message.from_user:
        remember_user(message.chat.id, message.from_user)
    for member in message.new_chat_members or []:
        remember_user(message.chat.id, member)

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    """BOTNI ISHGA TUSHURISH"""
    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.info("BOT ISHGA TUSHMOQDA...")
    for (chat_id, trade_number), deal in list(savdo_ma_lumotlari.items()):
        if deal["status"] == "Rozilik kutilmoqda":
            elapsed = time.time() - deal.get("created_at", time.time())
            asyncio.create_task(timeout_cancel(chat_id, trade_number, max(0, 600 - elapsed)))
    try:
        for admin_id in ADMINS:
            await bot.send_message(admin_id, "🤖 <b>BOT ISHGA TUSHDI!</b>")
    except Exception as e:
        logging.warning(f"ADMINGA XABAR YUBORISHDA XATOLIK: {e}")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())








