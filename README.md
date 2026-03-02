<div align="center">

# 🌙 بوت القرآن الكريم

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21+-229ED9)](https://github.com/python-telegram-bot/python-telegram-bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

🇸🇦 العربية · [🌐 English](README.en.md)

</div>

---

بوت تيليجرام للقرآن الكريم. ابحث، استمع، اقرأ التفسير، صدّر ملفات الترجمة، أو اطلب فيديو الآية مباشرة.

---

## المميزات

- 🎬 **توليد فيديو** — فيديو لكل آية مع الصوت المتزامن، أفقي أو عمودي. الوحيد في تيليجرام.
- 🎧 **18 قارئاً** — العفاسي، السديس، عبد الباسط، الحصري، وغيرهم.
- 🔍 **بحث ذكي** — يبحث في النص الكامل مع تطبيع عربي شامل (ألفات، تشكيل، همزات).
- 📚 **تفسيران** — الميسر والجلالين مع تصفح بالصفحات.
- 📄 **تصدير** — SRT وLRC مع توقيتات دقيقة.
- 📿 **أحاديث نبوية** — `/hadith` يُرسل حديثاً عشوائياً بالعربية. `/chadith` (للمشرف) يُرسله للقناة.
- ⚡ **إرسال فوري** — الملفات المولَّدة مُخزَّنة، والطلبات المكررة تُرسَل فوراً.
- 🌐 **عربي وإنجليزي** — واجهة بالكامل بالغتين.

---

## طريقة الاستخدام

أرسل اسم سورة أو رقم آية أو صفحة أو نصاً عربياً للبحث:

| المدخل | مثال |
|---|---|
| سورة + آية | `البقرة 255` · `Baqarah 255` |
| نطاق | `الفاتحة 1-7` · `1:1-7` |
| اسم سورة | `الكهف` · `Kahf` |
| صفحة | `صفحة 5` · `page 5` |
| بحث | `وما توفيقي إلا بالله` |

تظهر الآية مع أزرار التفاعل:

| الزر | |
|---|---|
| 📚 تفسير | الميسر أو الجلالين |
| 📖 نص | النص أو ملف SRT / LRC |
| 🎧 صوت | MP3 |
| 🎬 فيديو | فيديو مع الصوت |
| 📄 صفحة N | الصفحة في المصحف |

---

## الإعدادات

| | الخيارات |
|---|---|
| اللغة | العربية / English |
| صيغة النص | رسالة / SRT / LRC |
| التفسير | تفسير الميسر / تفسير الجلالين |
| نسبة الفيديو | أفقي 16:9 / عمودي 9:16 |
| القارئ | 18 خياراً |

---

## التشغيل الذاتي

**المتطلبات:** Python 3.10+، FFmpeg (في `bin/` أو مثبَّت على النظام)

```bash
git clone https://github.com/yourname/quranbot
cd quranbot
pip install -r requirements.txt
```

أنشئ ملف `.env`:

```env
BOT_TOKEN=your_token_here
CHANNEL_URL=https://t.me/yourchannel
CHANNEL_ID=@yourchannel
ADMIN_IDS=123456789
DONATE_URL=https://t.me/yourchannel/123
```

```bash
python bot.py
```

**الإعدادات الرئيسية في `config.py`:**

```python
ADMIN_IDS            = [123456789]
CHANNEL_URL          = "https://t.me/yourchannel"
CHANNEL_ID           = "@yourchannel"
MAX_AYAS_PER_REQUEST = 40
VIDEO_DEFAULT_RATIO  = "portrait"
DEFAULT_VOICE        = "Alafasy_64kbps"
```

---

## الدعم

| | |
|---|---|
| 💳 PayPal | `paypal.com/ncp/payment/W78F6W4TXZ4CS` |
| 🔸 Binance ID | `1011264323` |
| 🟡 Bybit ID | `467077834` |
| 🟢 TRC20 | `TMW5uSDN6sMUBNirMoqY1icpsfa7GhPZfK` |
| 🟢 BEP20/ERC20 | `0x7a8887c2ac3e596f6170c9e28b44e6b6d025c854` |
| 🔵 LTC | `LVswXiD6Vd2dejXvGbZLa1R8jkvg748F4q` |
| 🔵 TON | `UQAllRezWgHi3LPrSwyvAb4zazIph6j6goU7lMaqcFWFBxVH` |
| 🟠 BTC | `1rSX6BDN1nqDMyBHqceySkZSs6PHUP23m` |
| 🟣 SOL | `d8RonhC8oEHssrQjN1Y4UWHnd6MMP33XGCKtfNL4j59` |
| ⭐ Telegram Stars | عبر البوت مباشرة |

---

## مصادر البيانات

| | المصدر | الرخصة |
|---|---|---|
| نص القرآن + البيانات | [Tanzil.net](https://tanzil.net) | CC BY 3.0 |
| الملفات الصوتية | [EveryAyah.com](https://everyayah.com) | مجاني، غير تجاري |
| API التفسير | [AlQuran.cloud](https://alquran.cloud/api) | مجاني |
| الخط العثماني | [KFGQPC](https://fonts.qurancomplex.gov.sa) | مجاني، غير تجاري |
| قواعد الأحاديث | [IsmailHosenIsmailJames](https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite) | MIT |
