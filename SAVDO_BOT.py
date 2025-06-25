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
    """Foydalanuvchini unmute qiladi (yozish huquqini beradi)"""
    try:
        # Avval guruh default huquqlarini olish
        chat = await bot.get_chat(GROUP_ID)
        default_permissions = chat.permissions
        
        # Agar default permissions yo'q bo'lsa, to'liq huquqlarni berish
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
        # Agar yuqoridagi usul ishlamasa, to'g'ridan-to'g'ri ban olib tashlash
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

# YANGI FUNKSIYA: Foydalanuvchilarga huquq berish
async def grant_permissions(oluvchi_id: int, sotuvchi_id: int, message: types.Message):
    """Oluvchi va sotuvchiga yozish huquqlarini beradi"""
    oluvchi_info = await get_user_info(oluvchi_id)
    sotuvchi_info = await get_user_info(sotuvchi_id)
    
    # Oluvchiga huquq berish
    oluvchi_success = await unmute_user(oluvchi_id)
    if oluvchi_success:
        await message.answer(f"✅ Oluvchi <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a> ga yozish huquqi berildi!")
    else:
        await message.answer(f"❌ Oluvchi <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a> ga huquq berishda xatolik!")
    
    # Sotuvchiga huquq berish
    sotuvchi_success = await unmute_user(sotuvchi_id)
    if sotuvchi_success:
        await message.answer(f"✅ Sotuvchi <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a> ga yozish huquqi berildi!")
    else:
        await message.answer(f"❌ Sotuvchi <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a> ga huquq berishda xatolik!")

# YANGI FUNKSIYA: Foydalanuvchilarni mute qilish
async def revoke_permissions(oluvchi_id: int, sotuvchi_id: int, message: types.Message):
    """Oluvchi va sotuvchini mute qiladi"""
    oluvchi_info = await get_user_info(oluvchi_id)
    sotuvchi_info = await get_user_info(sotuvchi_id)
    
    # Oluvchini mute qilish
    oluvchi_success = await mute_user(oluvchi_id)
    if oluvchi_success:
        await message.answer(f"🔇 Oluvchi <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a> mute qilindi!")
    else:
        await message.answer(f"❌ Oluvchi <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a> ni mute qilishda xatolik!")
    
    # Sotuvchini mute qilish
    sotuvchi_success = await mute_user(sotuvchi_id)
    if sotuvchi_success:
        await message.answer(f"🔇 Sotuvchi <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a> mute qilindi!")
    else:
        await message.answer(f"❌ Sotuvchi <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a> ni mute qilishda xatolik!")

# --- YANGI A'ZOLARNI MUTE QILISH ---
@dp.message(F.new_chat_members)
async def on_user_joined(message: types.Message):
    """Yangi kirgan a'zolarni avtomatik mute qiladi"""
    for user in message.new_chat_members:
        if not user.is_bot:
            success = await mute_user(user.id)
            if success:
                await message.answer(f"")

# --- SAVDO BOSHLASH ---
@dp.message(Command("startSavdo"))
async def start_savdo(message: types.Message):
    """Savdo jarayonini boshlaydi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("❌ Faqat adminlar va ownerlar uchun!")
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            return await message.answer("❌ To'g'ri format: /startSavdo oluvchiID sotuvchiID")
        
        oluvchi_id = int(parts[1])
        sotuvchi_id = int(parts[2])
        
        # Foydalanuvchi ma'lumotlarini olish
        oluvchi_info = await get_user_info(oluvchi_id)
        sotuvchi_info = await get_user_info(sotuvchi_id)
        
        # Savdoni pending ro'yxatiga qo'shish
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
        await message.answer("❌ ID raqamlar noto'g'ri!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

# --- ROZIMAN TUGMASI BOSILGANDA ---
@dp.callback_query(F.data.startswith("roziman"))
async def on_roziman_clicked(call: types.CallbackQuery):
    """Roziman tugmasi bosilganda"""
    try:
        data_parts = call.data.split(":")
        oluvchi_id = int(data_parts[1])
        sotuvchi_id = int(data_parts[2])
        user_id = call.from_user.id
        
        deal_key = (oluvchi_id, sotuvchi_id)
        
        # Savdo mavjudligini tekshirish
        if deal_key not in pending_deals:
            await call.answer("❌ Bu savdo topilmadi!", show_alert=True)
            return
        
        # Faqat oluvchi yoki sotuvchi bosishi mumkin
        if user_id not in [oluvchi_id, sotuvchi_id]:
            await call.answer("❌ Siz bu savdoga tegishli emassiz!", show_alert=True)
            return
        
        # Rozilik qo'shish
        pending_deals[deal_key].add(user_id)
        
        # Ikkalasi ham roziman degan bo'lsa
        if len(pending_deals[deal_key]) == 2:
            # Foydalanuvchi ma'lumotlari
            oluvchi_info = await get_user_info(oluvchi_id)
            sotuvchi_info = await get_user_info(sotuvchi_id)
            
            # Savdo boshlandi xabari
            await call.message.answer(f"""
✅ <b>SAVDO BOSHLANDI!</b>

📋 <b>Oluvchi:</b> <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a>
📋 <b>Sotuvchi:</b> <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a>

🎯 Endi adminlar tomonidan yozish huquqi beriladi!
            """)
            
            # Avtomatik huquq berish (bot o'zi komanda yubormaydi, to'g'ridan-to'g'ri funksiyani chaqiradi)
            await grant_permissions(oluvchi_id, sotuvchi_id, call.message)
            
            # Pending ro'yxatidan o'chirish
            del pending_deals[deal_key]
        else:
            await call.answer("✅ Rozilik qabul qilindi! Ikkinchi tomonni kutmoqdamiz...", show_alert=True)
    
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

# --- SAVDO TUGATILDI TUGMASI ---
@dp.callback_query(F.data.startswith("savdo_end"))
async def on_savdo_end_clicked(call: types.CallbackQuery):
    """Savdo tugatildi tugmasi bosilganda"""
    try:
        data_parts = call.data.split(":")
        oluvchi_id = int(data_parts[1])
        sotuvchi_id = int(data_parts[2])
        user_id = call.from_user.id
        
        # Faqat oluvchi yoki sotuvchi bosishi mumkin
        if user_id not in [oluvchi_id, sotuvchi_id]:
            await call.answer("❌ Siz bu savdoga tegishli emassiz!", show_alert=True)
            return
        
        # Chiroy javob berish
        await call.answer("✅ Savdo muvaffaqiyatli tugatildi!", show_alert=True)
        
    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

# --- OLUVCHIGA YOZISH HUQUQI BERISH ---
@dp.message(Command("startOluvchi"))
async def start_oluvchi(message: types.Message):
    """Oluvchiga yozish huquqini beradi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("❌ Faqat adminlar va ownerlar uchun!")
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return await message.answer("❌ To'g'ri format: /startOluvchi oluvchiID")
        
        oluvchi_id = int(parts[1])
        success = await unmute_user(oluvchi_id)
        oluvchi_info = await get_user_info(oluvchi_id)
        
        if success:
            await message.answer(f"✅ Oluvchi <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a> ga yozish huquqi berildi!")
        else:
            await message.answer(f"❌ Oluvchi <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a> ga huquq berishda xatolik!")
    
    except ValueError:
        await message.answer("❌ ID noto'g'ri!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

# --- SOTUVCHIGA YOZISH HUQUQI BERISH ---
@dp.message(Command("startSotuvchi"))
async def start_sotuvchi(message: types.Message):
    """Sotuvchiga yozish huquqini beradi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("❌ Faqat adminlar va ownerlar uchun!")
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return await message.answer("❌ To'g'ri format: /startSotuvchi sotuvchiID")
        
        sotuvchi_id = int(parts[1])
        success = await unmute_user(sotuvchi_id)
        sotuvchi_info = await get_user_info(sotuvchi_id)
        
        if success:
            await message.answer(f"✅ Sotuvchi <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a> ga yozish huquqi berildi!")
        else:
            await message.answer(f"❌ Sotuvchi <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a> ga huquq berishda xatolik!")
    
    except ValueError:
        await message.answer("❌ ID noto'g'ri!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

# --- SAVDO TUGATILDI TUGMASI --- (YANGILANGAN)
@dp.callback_query(F.data.startswith("endSavdo"))
async def on_savdo_end_clicked(call: types.CallbackQuery):
    """Savdo tugatildi tugmasi bosilganda"""
    try:
        data_parts = call.data.split(":")
        oluvchi_id = int(data_parts[1])
        sotuvchi_id = int(data_parts[2])
        user_id = call.from_user.id

        deal_key = (oluvchi_id, sotuvchi_id)

        # Pending end deals (kim bosganini saqlaydi)
        if "ended_deals" not in globals():
            global ended_deals
            ended_deals = {}
        
        if deal_key not in ended_deals:
            ended_deals[deal_key] = set()
        
        # Faqat oluvchi yoki sotuvchi bosishi mumkin
        if user_id not in [oluvchi_id, sotuvchi_id]:
            await call.answer("❌ Siz bu savdoga tegishli emassiz!", show_alert=True)
            return

        # Allaqachon bosgan bo‘lsa
        if user_id in ended_deals[deal_key]:
            await call.answer("⏳ Siz allaqachon rozilik bildirgansiz.", show_alert=True)
            return

        # Yangi rozilikni qo‘shish
        ended_deals[deal_key].add(user_id)

        # Kim bosdi — javob
        if user_id == oluvchi_id:
            await call.message.answer("📥 <b>Oluvchi savdoning tugaganiga rozi</b>")
        elif user_id == sotuvchi_id:
            await call.message.answer("📤 <b>Sotuvchi savdoning tugaganiga rozi</b>")

        # Agar ikkala tomon ham rozi bo‘lsa:
        if len(ended_deals[deal_key]) == 2:
            await call.message.answer(f"""
✅ <b>SAVDO YAKUNLANDI!</b>

📋 <b>Oluvchi:</b> <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a>
📋 <b>Sotuvchi:</b> <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a>

🔒 Har ikki tomon savdoning tugaganiga rozilik bildirdi.
""")
            # Oxirida pendingni tozalash
            del ended_deals[deal_key]

        await call.answer("✅ Rozilik qabul qilindi!", show_alert=True)

    except Exception as e:
        await call.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

# --- OLUVCHINI MUTE QILISH ---
@dp.message(Command("endOluvchi"))
async def end_oluvchi(message: types.Message):
    """Oluvchini mute qiladi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("❌ Faqat adminlar va ownerlar uchun!")
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return await message.answer("❌ To'g'ri format: /endOluvchi oluvchiID")
        
        oluvchi_id = int(parts[1])
        success = await mute_user(oluvchi_id)
        oluvchi_info = await get_user_info(oluvchi_id)
        
        if success:
            await message.answer(f"🔇 Oluvchi <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a> mute qilindi!")
        else:
            await message.answer(f"❌ Oluvchi <a href='tg://user?id={oluvchi_id}'>OLUVCHI</a> ni mute qilishda xatolik!")
    
    except ValueError:
        await message.answer("❌ ID noto'g'ri!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

# --- SOTUVCHINI MUTE QILISH ---
@dp.message(Command("endSotuvchi"))
async def end_sotuvchi(message: types.Message):
    """Sotuvchini mute qiladi"""
    # Faqat admin va owner uchun
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("❌ Faqat adminlar va ownerlar uchun!")
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return await message.answer("❌ To'g'ri format: /endSotuvchi sotuvchiID")
        
        sotuvchi_id = int(parts[1])
        success = await mute_user(sotuvchi_id)
        sotuvchi_info = await get_user_info(sotuvchi_id)
        
        if success:
            await message.answer(f"🔇 Sotuvchi <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a> mute qilindi!")
        else:
            await message.answer(f"❌ Sotuvchi <a href='tg://user?id={sotuvchi_id}'>SOTUVCHI</a> ni mute qilishda xatolik!")
    
    except ValueError:
        await message.answer("❌ ID noto'g'ri!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

# --- YORDAM KOMANDASI ---
@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Barcha komandalar ro'yxati"""
    if not await is_admin_or_owner(message.chat.id, message.from_user.id):
        return await message.answer("❌ Faqat adminlar va ownerlar uchun!")
    
    help_text = """
🤖 <b>SAVDO BOT KOMANDALAR:</b>

🎯 <b>Savdo jarayoni:</b>
• <code>/startSavdo oluvchiID sotuvchiID</code> - Savdo boshlash
• <code>/endSavdo oluvchiID sotuvchiID</code> - Savdo tugatish

👥 <b>Foydalanuvchilar:</b>
• <code>/startOluvchi ID</code> - Oluvchiga yozish huquqi
• <code>/startSotuvchi ID</code> - Sotuvchiga yozish huquqi
• <code>/endOluvchi ID</code> - Oluvchini mute qilish
• <code>/endSotuvchi ID</code> - Sotuvchini mute qilish

ℹ️ <code>/help</code> - Bu yordam xabari

<b>Eslatma:</b> Yangi kirgan a'zolar avtomatik mute qilinadi!
    """
    await message.answer(help_text)

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    """Botni ishga tushirish"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())