import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
raw_admins = os.getenv("ADMINS")
ADMINS = list(map(int, raw_admins.split(","))) if raw_admins else []
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# --- FOYDALI FUNKSIYALAR ---
pending_deals = {}
ended_deals = {}
faol_savdolar = set()
async def is_admin_or_owner(chat_id: int, user_id: int) -> bool:
    """Admin yoki owner ekanligini tekshiradi"""
    try:
        # Avval ADMINS ro'yxatidan tekshirish
        if user_id in ADMINS:
            return True
        
        # Guruh adminlarini tekshirish
        members = await bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in members)
    except:
        return False

async def mute_user(user_id: int):
    """Foydalanuvchini mute qiladi"""
    try:
        await bot.restrict_chat_member(
            GROUP_ID,
            user_id,
            permissions=types.ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
                can_manage_topics=False
            )
        )
        return True
    except Exception as e:
        logging.error(f"Mute xatoligi: {e}")
        return False

async def unmute_user(user_id: int):
    """Foydalanuvchini unmute qiladi (YOZISH HUQUQini beradi)"""
    try:
        # Avval guruh default HUQUQlarini olish
        chat = await bot.get_chat(GROUP_ID)
        default_permissions = chat.permissions
        
        # AGAr default permissions yo'q bo'lsa, to'liq HUQUQlarni berish
        if not default_permissions:
            permissions = types.ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        else:
            permissions = default_permissions
        
        await bot.restrict_chat_member(
            GROUP_ID,
            user_id,
            permissions=permissions
        )
        return True
    except Exception as e:
        logging.error(f"Unmute xatoligi: {e}")
        # AGAr yuqoridagi usul ishlamasa, to'g'ridan-to'g'ri ban olib tashlash
        try:
            await bot.unban_chat_member(GROUP_ID, user_id, only_if_banned=False)
            return True
        except Exception as e2:
            logging.error(f"Unban xatoligi: {e2}")
            return False

async def get_user_info(user_id: int) -> str:
    """Foydalanuvchi ma'lumotini oladi"""
    try:
        user = await bot.get_chat_member(GROUP_ID, user_id)
        if user.user.username:
            return f"@{user.user.username}"
        else:
            return f"{user.user.first_name} (ID: {user_id})"
    except:
        return f"ID: {user_id}"

# YANGI FUNKSIYA: FoydalanuvchilarGA HUQUQ berish
async def grant_permissions(oluvchi_id: int, sotuvchi_id: int, message: types.Message):
    """Oluvchi va sotuvchiGA YOZISH HUQUQlarini beradi"""
    oluvchi_info = await get_user_info(oluvchi_id)
    sotuvchi_info = await get_user_info(sotuvchi_id)
    
    # OluvchiGA HUQUQ berish
    oluvchi_success = await unmute_user(oluvchi_id)
    if oluvchi_success:
        await message.answer("✅ OLUVCHI MUTE DAN OLINDI!", show_alert=True)
    else:
        await message.answer("⚠️ MUTE QILISHDA XATOLIK YUZ BERDI!", show_alert=True)

    
    # SotuvchiGA HUQUQ berish
    sotuvchi_success = await unmute_user(sotuvchi_id)
    if sotuvchi_success:
        await message.answer("✅ SOTUVCHI MUTE DAN OLINDI!", show_alert=True)
    else:
        await message.answer("⚠️ MUTE QILISHDA XATOLIK YUZ BERDI!", show_alert=True)

# YANGI FUNKSIYA: Foydalanuvchilarni mute qilish
async def revoke_permissions(oluvchi_id: int, sotuvchi_id: int, message: types.Message):
    """OLUVCHI VA SOTUVCHI mute qiladi"""
    oluvchi_info = await get_user_info(oluvchi_id)
    sotuvchi_info = await get_user_info(sotuvchi_id)
    
    # Oluvchini mute qilish
    oluvchi_success = await mute_user(oluvchi_id)
    if oluvchi_success:
        await message.answer("✅ OLUVCHI MUTE DAN OLINDI!", show_alert=True)
    else:
        await message.answer("⚠️ MUTE QILISHDA XATOLIK YUZ BERDI!", show_alert=True)
    
    # Sotuvchini mute qilish
    sotuvchi_success = await mute_user(sotuvchi_id)
    if sotuvchi_success:
        await message.answer("✅ SOTUVCHI MUTE DAN OLINDI!", show_alert=True)
    else:
       await message.answer("⚠️ MUTE QILISHDA XATOLIK YUZ BERDI!", show_alert=True)

# --- YANGI A'ZOLARNI MUTE QILISH ---
@dp.message(F.new_chat_members)
async def on_user_joined(message: types.Message):
    """YANGI KIRGAN AZOLARNI AVTOMATIK MUTE QILINDI"""
    for user in message.new_chat_members:
        if not user.is_bot:
            success = await mute_user(user.id)
            if success:
                await message.answer(f"")

# --- SAVDO BOSHLANDI ROZIMISIZ TUGMASI ---
@dp.callback_query(F.data.startswith("roziman"))
async def on_roziman_clicked(call: types.CallbackQuery):
    """Roziman tugmasi bosilGAnda"""
    try:
        data_parts = call.data.split(":")
        oluvchi_id = int(data_parts[1])
        sotuvchi_id = int(data_parts[2])
        user_id = call.from_user.id
        
        deal_key = (oluvchi_id, sotuvchi_id)
        
        # Savdo mavjudligini tekshirish
        if deal_key not in pending_deals:
            await call.answer("⚠️ Bu savdo topilmadi!", show_alert=True)
            return
        
        # Faqat oluvchi yoki sotuvchi bosishi mumkin
        if user_id not in [oluvchi_id, sotuvchi_id]:
            await call.answer("⚠️ Siz bu savdoGA tegishli emassiz!", show_alert=True)
            return
        
        # Rozilik qo'shish
        pending_deals[deal_key].add(user_id)
        
        # Ikkalasi ham roziman deGAn bo'lsa
        if len(pending_deals[deal_key]) == 2:
            faol_savdolar.add((oluvchi_id, sotuvchi_id))
            # Foydalanuvchi ma'lumotlari
            oluvchi_info = await get_user_info(oluvchi_id)
            sotuvchi_info = await get_user_info(sotuvchi_id)
            
            # Savdo boshlandi xabari
            await call.message.answer(f"""
✅ <b>SAVDO BOSHLANDI!</b>

📋 <b>Oluvchi:</b> <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a>
📋 <b>Sotuvchi:</b> <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a>

🎯 Endi adminlar tomonidan YOZISH HUQUQi beriladi!
            """)
            
            # Avtomatik HUQUQ berish (bot o'zi komanda yubormaydi, to'g'ridan-to'g'ri funksiyani chaqiradi)
            await grant_permissions(oluvchi_id, sotuvchi_id, call.message)
            
            # Pending ro'yxatidan o'chirish
            del pending_deals[deal_key]
            ended_deals[deal_key] = set()
        else:
            await call.answer("✅ Rozilik qabul qilindi! Ikkinchi tomonni kutmoqdamiz...", show_alert=True)
    
    except Exception as e:
        await call.answer(f"⚠️ XATOLIK: {str(e)}", show_alert=True)

# --- SAVDO BOSHLASH ---
@dp.message(Command("startSavdo"))
async def start_savdo(message: types.Message):
    """Savdo jarayonini boshlaydi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ Faqat adminlar va ownerlar uchun!")
    try:
        parts = message.text.split()
        if len(parts) != 3:
            return await message.answer("⚠️ To'g'ri format: /startSavdo oluvchiID sotuvchiID")
        
        oluvchi_id = int(parts[1])
        sotuvchi_id = int(parts[2])
        
        faol_savdolar.add((oluvchi_id, sotuvchi_id))

        
        # Foydalanuvchi ma'lumotlarini olish
        oluvchi_info = await get_user_info(oluvchi_id)
        sotuvchi_info = await get_user_info(sotuvchi_id)
        
        # Savdoni pending ro'yxatiGA qo'shish
        deal_key = (oluvchi_id, sotuvchi_id)
        pending_deals[deal_key] = set()
        
        # Roziman tugmalari
        oluvchi_btn = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ ROZIMAN", callback_data=f"roziman:{oluvchi_id}:{sotuvchi_id}")
            ]]
        )
        
        sotuvchi_btn = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ ROZIMAN", callback_data=f"roziman:{oluvchi_id}:{sotuvchi_id}")
            ]]
        )
 
       
        # Zayafka xabari
        zayafka_text = f"""
🎉 <b>SAVDO ZAYAFKASI!</b>

📋 <b>Oluvchi:</b> <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a>
📋 <b>Sotuvchi:</b> <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a>

⚡️ Savdo boshlanishi uchun ikkala tomon ham rozilik bildirishi kerak!
        """
        
       
        await message.answer(f"{zayafka_text}\n\n👤 <b> <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a> - <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a></b>, roziligingizni bildiring:", reply_markup=sotuvchi_btn)
        
    except ValueError:
        await message.answer("⚠️ ID raqamlar noto'g'ri!")
    except Exception as e:
        await message.answer(f"⚠️ XATOLIK: {str(e)}")

# --- SAVDO TUGATILDI ROZIMISIZ TUGMASI ---
@dp.callback_query(F.data.startswith("savdo_end"))
async def on_savdo_end_clicked(call: types.CallbackQuery):
    """Savdo tuGAtildi tugmasi bosilGAnda - tugmaning o'zini yangilaydi"""
    try:
        data_parts = call.data.split(":")
        oluvchi_id = int(data_parts[1])
        sotuvchi_id = int(data_parts[2])
        user_id = call.from_user.id

        deal_key = (oluvchi_id, sotuvchi_id)

        # Global ended_deals dictionary
        global ended_deals
        if "ended_deals" not in globals():
            ended_deals = {}

        if deal_key not in ended_deals:
            ended_deals[deal_key] = set()

        # Faqat oluvchi yoki sotuvchi bosishi mumkin
        if user_id not in [oluvchi_id, sotuvchi_id]:
            await call.answer("⚠️ Siz bu savdoGA tegishli emassiz!", show_alert=True)
            return

        # Allaqachon bosGAn bo‘lsa
        if user_id in ended_deals[deal_key]:
            await call.answer("⏳ Siz allaqachon bosGAnsiz.", show_alert=True)
            return

        # Rozilikni saqlaymiz
        ended_deals[deal_key].add(user_id)

        # Tugma matnini tayyorlaymiz
        text = ""
        if ended_deals[deal_key] == {oluvchi_id}:
            text = "📥 Oluvchi rozi"
        elif ended_deals[deal_key] == {sotuvchi_id}:
            text = "📤 Sotuvchi rozi"
        elif ended_deals[deal_key] == {oluvchi_id, sotuvchi_id}:
            text = "✅ Oluvchi va Sotuvchi rozi"

        # Tugmani yangilaymiz
        new_markup = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text=text, callback_data=f"savdo_end:{oluvchi_id}:{sotuvchi_id}")
            ]]
        )
        await call.message.edit_reply_markup(reply_markup=new_markup)

        # Hammasi bosilGAn bo‘lsa – dictni tozalaymiz
        if len(ended_deals[deal_key]) == 2:
            del ended_deals[deal_key]
            faol_savdolar.discard(deal_key)

        await call.answer("✅ Qabul qilindi")

    except Exception as e:
        await call.answer(f"⚠️ XATOLIK: {str(e)}", show_alert=True)

# --- SAVDONI TUGATISH ---
@dp.message(Command("endSavdo"))
async def end_savdo(message: types.Message):
    """Savdo jarayonini tuGAtadi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ Faqat adminlar va ownerlar uchun!")
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            return await message.answer("⚠️ To'g'ri format: /endSavdo oluvchiID sotuvchiID")
        
        oluvchi_id = int(parts[1])
        sotuvchi_id = int(parts[2])
        
        # Foydalanuvchi ma'lumotlari
        oluvchi_info = await get_user_info(oluvchi_id)
        sotuvchi_info = await get_user_info(sotuvchi_id)
        
        # Chiroy tugma yaratish
        end_button = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ SAVDO TUGATILDI", callback_data=f"savdo_end:{oluvchi_id}:{sotuvchi_id}")
            ]]
        )
        
        # Savdo tuGAtildi xabari tugma bilan
        await message.answer(f"""
⚠️ <b>SAVDO TUGATILDI!</b>

📋 <b>Oluvchi:</b> <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a>
📋 <b>Sotuvchi:</b> <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a>

🔒 Foydalanuvchilar yana mute qilinadi!
        """, reply_markup=end_button)
        
        # Avtomatik mute qilish (bot o'zi komanda yubormaydi, to'g'ridan-to'g'ri funksiyani chaqiradi)
        await revoke_permissions(oluvchi_id, sotuvchi_id, message)
        faol_savdolar.discard((oluvchi_id, sotuvchi_id))
    
    except ValueError:
        await message.answer("⚠️ ID raqamlar noto'g'ri!")
    except Exception as e:
        await message.answer(f"⚠️ XATOLIK: {str(e)}") 

# --- OLUVCHIGA YOZISH HUQUQI BERISH ---
@dp.message(Command("startOluvchi"))
async def start_oluvchi(message: types.Message):
    """OluvchiGA YOZISH HUQUQini beradi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ Faqat adminlar va ownerlar uchun!")
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return await message.answer("⚠️ To'g'ri format: /startOluvchi oluvchiID")
        
        oluvchi_id = int(parts[1])
        success = await unmute_user(oluvchi_id)
        oluvchi_info = await get_user_info(oluvchi_id)
        
        if success:
            await message.answer("✅ OLUVCHI MUTE DAN OLINDI!", show_alert=True)
        else:
            await message.answer("⚠️ MUTE QILISHDA XATOLIK YUZ BERDI!", show_alert=True)

    
    except ValueError:
        await message.answer("⚠️ ID noto'g'ri!")
    except Exception as e:
        await message.answer(f"⚠️ XATOLIK: {str(e)}")

# --- SOTUVCHIGA YOZISH HUQUQI BERISH ---
@dp.message(Command("startSotuvchi"))
async def start_sotuvchi(message: types.Message):
    """SotuvchiGA YOZISH HUQUQini beradi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ Faqat adminlar va ownerlar uchun!")
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return await message.answer("⚠️ To'g'ri format: /startSotuvchi sotuvchiID")
        
        sotuvchi_id = int(parts[1])
        success = await unmute_user(sotuvchi_id)
        sotuvchi_info = await get_user_info(sotuvchi_id)
        
        if success:
            await message.answer("✅ SOTUVCHI MUTE DAN OLINDI!", show_alert=True)
        else:
            await message.answer("⚠️ MUTE QILISHDA XATOLIK YUZ BERDI!", show_alert=True)

    
    except ValueError:
        await message.answer("⚠️ ID noto'g'ri!")
    except Exception as e:
        await message.answer(f"⚠️ XATOLIK: {str(e)}")

# --- OLUVCHINI MUTE QILISH ---
@dp.message(Command("endOluvchi"))
async def end_oluvchi(message: types.Message):
    """Oluvchini mute qiladi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ Faqat adminlar va ownerlar uchun!")
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return await message.answer("⚠️ To'g'ri format: /endOluvchi oluvchiID")
        
        oluvchi_id = int(parts[1])
        success = await mute_user(oluvchi_id)
        oluvchi_info = await get_user_info(oluvchi_id)
        
        if success:
            await message.answer("❌ OLUVCHI MUTE QILINDI!", show_alert=True)
        else:
            await message.answer("⚠️ MUTE QILISHDA XATOLIK YUZ BERDI!", show_alert=True)

    
    except ValueError:
        await message.answer("⚠️ ID noto'g'ri!")
    except Exception as e:
        await message.answer(f"⚠️ XATOLIK: {str(e)}")

# --- SOTUVCHINI MUTE QILISH ---
@dp.message(Command("endSotuvchi"))
async def end_sotuvchi(message: types.Message):
    """Sotuvchini mute qiladi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ Faqat adminlar va ownerlar uchun!")
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return await message.answer("⚠️ To'g'ri format: /endSotuvchi sotuvchiID")
        
        sotuvchi_id = int(parts[1])
        success = await mute_user(sotuvchi_id)
        sotuvchi_info = await get_user_info(sotuvchi_id)
        
        if success:
            await message.answer("❌ SOTUVCHI MUTE QILINDI!", show_alert=True)
        else:
            await message.answer("⚠️ MUTE QILISHDA XATOLIK YUZ BERDI!", show_alert=True)

    except ValueError:
        await message.answer("⚠️ ID noto'g'ri!")
    except Exception as e:
        await message.answer(f"⚠️ XATOLIK: {str(e)}")

# --- YORDAM KOMANDASI ---
@dp.message(Command("help"))
async def help_command(message: types.Message):
    """BARCHA KOMANDALAR RO‘YXATI — FAQAT ADMINLARGA"""

    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ FAQAT ADMINLAR VA OWNERLARGA RUXSAT!")

    help_text = """
🤖 <b>SAVDO BOT — KOMANDALAR</b>

━━━━━━━━━━━━━━━━━━━━━
🎯 <b>SAVDO BOSHLASH/TUGATISH:</b>
━━━━━━━━━━━━━━━━━━━━━
🚀 <code>/startSavdo OLUVCHI_ID SOTUVCHI_ID</code> — Savdoni boshlash  
🛑 <code>/endSavdo OLUVCHI_ID SOTUVCHI_ID</code> — Savdoni tuGAtish

━━━━━━━━━━━━━━━━━━━━━
👥 <b>YOZISH HUQUQLARI:</b>
━━━━━━━━━━━━━━━━━━━━━
✉️ <code>/startOluvchi ID</code> — OluvchiGA YOZISH HUQUQi  
✉️ <code>/startSotuvchi ID</code> — SotuvchiGA YOZISH HUQUQi  
🔇 <code>/endOluvchi ID</code> — Oluvchini mute qilish  
🔇 <code>/endSotuvchi ID</code> — Sotuvchini mute qilish

━━━━━━━━━━━━━━━━━━━━━
📊 <b>FAOL SAVDOLAR:</b>
━━━━━━━━━━━━━━━━━━━━━
📋 <code>/fullSavdo</code> — Hozirgi barcha faol savdolarni ko‘rish

━━━━━━━━━━━━━━━━━━━━━
ℹ️ <b>YORDAM:</b>
━━━━━━━━━━━━━━━━━━━━━
🆘 <code>/help</code> — Yordam menyusi

━━━━━━━━━━━━━━━━━━━━━
❗ <b>ESLATMA:</b> Yangi kirGAnlar avtomatik <b>mute</b> qilinadi!
━━━━━━━━━━━━━━━━━━━━━
"""
    await message.answer(help_text)
# --- HAMMA SAVDOLAR TOPLAMI ---
@dp.message(Command("fullSavdo"))
async def full_savdo(message: types.Message):
    """FAOL SAVDOLAR RO‘YXATI — FAQAT ADMINLAR UCHUN"""

    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("⚠️ FAQAT ADMINLAR VA OWNERLAR UCHUN!")

    try:
        index = 1
        text = "<b>📊 FAOL SAVDOLAR ROʻYXATI</b>\n\n"

        # 🔄 1-QISM: ROZILIK KUTILAYOTGAN SAVDOLAR
        for (oluvchi_id, sotuvchi_id), rozi_users in pending_deals.items():
            oluvchi_link = f"<a href='tg://user?id={oluvchi_id}'>OLUVCHI</a>"
            sotuvchi_link = f"<a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a>"
            holat = "🟡 ROZILIK KUTILMOQDA" if len(rozi_users) < 2 else "✅ ROZILIK BERILGAN"

            text += f"🔢 <b>SAVDO #{index}</b>\n"
            text += f"👤 {oluvchi_link}\n"
            text += f"🛒 {sotuvchi_link}\n"
            text += f"📌 HOLATI: <b>{holat}</b>\n\n"
            index += 1


# 🔵 2-QISM: ROZILIK BERILGAN, YAKUN KUTILAYOTGAN SAVDOLAR
        for (oluvchi_id, sotuvchi_id), rozi_users in ended_deals.items():
           if len(rozi_users) < 2:
            oluvchi_link = f"<a href='tg://user?id={oluvchi_id}'>OLUVCHI</a>"
            sotuvchi_link = f"<a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a>"

        text += f"🔢 <b>SAVDO #{index}</b>\n"
        text += f"👤 {oluvchi_link}\n"
        text += f"🛒 {sotuvchi_link}\n"
        text += f"📌 HOLATI: <b>🔵 SAVDO BOSHLANGAN</b>\n\n"
        index += 1

        if index == 1:
            return await message.answer("📭 <b>HOZIRDA HECH QANDAY FAOL SAVDO YOʻQ!</b>")

        await message.answer(text)

    except Exception as e:
        await message.answer(f"⚠️ <b>XATOLIK:</b> {str(e)}")

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    """Botni ishGA tushirish"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Bot ishGA tushmoqda...")

    try:
        for admin_id in ADMINS:
            await bot.send_message(admin_id, "🤖 <b>BOT ISHGA TUSHDI!</b>")
    except Exception as e:
        logging.warning(f"AdminlarGA xabar yuborishda XATOLIK: {e}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())