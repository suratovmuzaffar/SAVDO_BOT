# Savdo botidan foydalanish qo‘llanmasi

Bot savdo boshlanishida sotuvchi va oluvchidan rozilik so‘raydi. Ikkalasi rozi bo‘lgach bot ularga adminlik beradi; savdo tugaganda adminlikni oladi. Oddiy a’zolarning yozish huquqini guruh sozlamasidan cheklash kerak.

## O‘rnatish va ishga tushirish

`SAVDO_BOT.py` bilan bir papkadagi `.env` faylida `BOT_TOKEN` va `ADMINS` bo‘lsin:

```env
BOT_TOKEN=BotFather_dan_olingan_bot_tokeni
ADMINS=123456789,987654321
UZCARD=8600123412341234
HUMO=9860123412341234
VISA=4111111111111111
```

To‘lov kartalaridan foydalanmoqchi bo‘lmasangiz, tegishli `UZCARD`, `HUMO` yoki `VISA` qatorini bo‘sh qoldiring yoki olib tashlang. Faqat to‘ldirilgan kartalar savdo faol bo‘lganda xaridorga yuboriladi.

PowerShell’da:

```powershell
cd "$HOME\OneDrive\Desktop\SAVDO_BOT_TEST"
py -m pip install aiogram python-dotenv
py SAVDO_BOT.py
```

Bot ishlab turgan paytda PowerShell oynasini ochiq qoldiring; to‘xtatish uchun Ctrl+C bosing.

## Guruhni sozlash

1. Botni guruhga qo‘shib, administrator qiling.
2. Botga **Yangi administratorlar qo‘shish** (`can_promote_members`) huquqini bering.
3. Guruh sozlamalarida oddiy a’zolarning xabar yuborishini o‘chiring.
4. Sotuvchi va oluvchi savdo guruhining a’zosi bo‘lishi kerak.

Bot savdo qatnashchilarini admin qiladi. Administratorlarda guruhga yozish imkoni bo‘ladi. Bot boshqa admin huquqlarini bermaslikka sozlangan; adminlikni berish Telegram’ning `promoteChatMember` API metodiga tayanadi.

## Buyruqlar

Buyruqlarni savdo guruhida yuboring. ID raqamlarni Telegram foydalanuvchi ID’si bilan almashtiring. ID sini bilmagan qatnashchi avval botga shaxsiy chatda `/start` yuborib, keyin `/id` yuborishi mumkin; bot ID raqamini qaytaradi. Foydalanuvchi botga birinchi bo‘lib yozishi shart, bot o‘zi shaxsiy chatni boshlab bera olmaydi.

| Buyruq | Vazifasi |
|---|---|
| `/start SOTUVCHI_ID 1 OLUVCHI_ID 2` | Savdoni ochadi. `1` — sotuvchi, `2` — oluvchi. `.env`da kiritilgan kartalar savdo faol bo‘lgach oluvchiga yuboriladi. |
| `/end SAVDO_RAQAMI` | Ko‘rsatilgan savdoni tugatib, ikki qatnashchidan adminlikni oladi. |
| `/admin FOYDALANUVCHI 1` | Foydalanuvchiga sotuvchi roli bilan adminlik beradi. |
| `/admin FOYDALANUVCHI 2` | Foydalanuvchiga oluvchi roli bilan adminlik beradi. |
| `/unadmin FOYDALANUVCHI` | Foydalanuvchidan adminlikni oladi; rol raqami kerak emas. |
| `/status` | Shu guruhdagi kutilayotgan va faol savdolarni, raqamlari bilan ko‘rsatadi. |
| `/help` | Buyruqlar bo‘yicha qisqa ko‘rsatmani chiqaradi. |

### Misol

```text
/start 111111111 1 222222222 2
```

Bot savdoga avtomatik raqam beradi. Oluvchi va sotuvchi rozilikni tasdiqlagach, bot har ikkalasiga adminlik beradi. `.env`da kiritilgan kartalar bo‘lsa, bot savdo faol bo‘lganda guruhga oluvchini belgilab to‘lov qilishni so‘raydi; chekni guruhga yuborishni eslatadi. Savdo #1 ni yakunlash:

```text
/end 1
```

`/admin` orqali berilgan adminlik qo‘lda beriladi va avtomatik savdo raqamiga bog‘lanmaydi. Savdo orqali admin qilinganda bot xabarda rolni (`SOTUVCHI` yoki `OLUVCHI`) va savdo raqamini ko‘rsatadi.

### Foydalanuvchini ID, username yoki havola bilan ko‘rsatish

ID ishlaydi, masalan `/admin 123456789 1`. Profil havolasidan ID ko‘rinishidagi Telegram deep linkni (`tg://user?id=123456789`) yuborish ham mumkin. `@username` yoki `https://t.me/username` bot shu guruhda foydalanuvchini oldin ko‘rgan bo‘lsa ishlaydi; guruh adminlarining username'lari ham bevosita topiladi. Bot guruh xabarlaridan username va ID mosligini eslab qoladi. Profilga olib boradigan Telegram `text_mention` havolasidagi ID ham olinadi.

Telegram Bot API istalgan shaxsiy `@username`ni ID ga mustaqil topib bera olmaydi. Admin-only guruhda oddiy qatnashchilar xabar yozolmagani uchun bot ularning username’ini tanimasligi mumkin. Shunda qatnashchi botga shaxsiy chatda `/start`, so‘ng `/id` yuborib olgan raqamli ID sini admin’ga beradi. ID o‘rnida ishlating: `/start 111111111 1 222222222 2`. Bot guruh adminlarining username’larini ham qidirib ko‘radi, lekin bu Telegram’dan har qanday username’ni qidirish imkonini bermaydi.

## Eslatmalar

- Savdo raqamlari va holati `.savdo_state.json` faylida saqlanadi; bot qayta ishga tushganda ham `/end SAVDO_RAQAMI` ishlaydi.
- Rozilik 10 daqiqada to‘liq bo‘lmasa, so‘rov bekor qilinadi.
- Botga adminlik berish huquqi bo‘lmasa, Telegram qaytargan xato guruhda ko‘rinadi. Bot faqat o‘zi ko‘targan adminlikni olishi mumkin.

