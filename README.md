<div align="center">

# 🌙 بوت القرآن الكريم

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21+-229ED9)](https://github.com/python-telegram-bot/python-telegram-bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

🇸🇦 العربية · [🌐 English](README.en.md)

**[▶️ افتح البوت](https://t.me/YOUR_BOT_USERNAME)** · **[📢 القناة](https://t.me/YOUR_CHANNEL_USERNAME)**

</div>

---

بوت تيليجرام للقرآن الكريم. ابحث، استمع، اقرأ التفسير، وشاهد فيديو الآيات مع الصوت.

---

## المميزات

- 📖 **المصحف** — عرض صفحات المصحف بثلاثة مصادر: حفص، ورش، والتجويد الملوّن. يخزّن file\_id بعد أول إرسال.
- 🖼️ **صور الآيات** — صور عالية الجودة (1080px) بثلاثة خطوط وثلاث سمات. الأبعاد تلقائية أو ثابتة.
- 🎬 **فيديو** — فيديو لكل آية مع الصوت المتزامن، أفقي أو عمودي. الوحيد من نوعه في تيليجرام.
- 🎧 **18 قارئاً** — العفاسي، السديس، عبد الباسط، الحصري، وغيرهم.
- 🔍 **بحث ذكي** — بحث في النص الكامل مع تطبيع عربي شامل (ألفات، تشكيل، همزات).
- 📚 **تفسيران** — الميسر والجلالين، من ملف محلي ثم API احتياطي.
- 📄 **تصدير** — SRT وLRC مع توقيتات دقيقة.
- 📿 **أحاديث** — `/hadith` حديث عشوائي. ينشر تلقائياً في القناة يومياً.
- ⚡ **إرسال فوري** — file\_id مخزّن لكل ملف مُرسَل سابقاً.
- 🌐 **عربي وإنجليزي** — واجهة كاملة بالغتين.

---

## طريقة الاستخدام

أرسل اسم سورة أو رقم آية أو صفحة أو نصاً للبحث:

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
| 📖 نص | النص أو ملف SRT / LRC |
| 📚 تفسير | الميسر أو الجلالين |
| 🖼️ صورة | صورة الآية (إن كانت قصيرة) |
| 🎬 فيديو | فيديو مع الصوت |
| 📄 الصفحة N | صفحة المصحف |
| 🎧 صوت | MP3 |

---

## الإعدادات

```
⚙️ الإعدادات
├─ 📖 المصدر  (حفص / ورش / تجويد)
├─ 🎙️ القارئ  (18 خياراً)
└─ ⚙️ أخرى
    ├─ 📚 التفسير  (الميسر / الجلالين)
    ├─ 📄 التنسيق  (رسالة / صورة / SRT / LRC)
    ├─ 🎬 الفيديو
    │   ├─ الخط  (عثماني / أميري / نوتو نسخ)
    │   ├─ السمة  (داكن / ورقي / ليلي)
    │   └─ النسبة  (عمودي 9:16 / أفقي 16:9)
    └─ 🖼️ الصورة
        ├─ الخط  (عثماني / أميري / نوتو نسخ)
        ├─ السمة  (ورقي / داكن / ليلي)
        └─ الدقة  (تلقائي / عمودي / أفقي)
```

---

## التشغيل

**المتطلبات:** Python 3.10+، FFmpeg

```bash
git clone https://github.com/yourname/quranbot
cd quranbot
pip install -r requirements.txt
```

أنشئ ملف `.env` (انظر `.env.example`):

```bash
cp .env.example .env
# ثم عدّل BOT_TOKEN والإعدادات الأخرى
```

ثنائيات FFmpeg الثابتة (اختياري — إن لم يكن FFmpeg مثبتاً في PATH):

```bash
mkdir -p bin
# Linux x86_64:
wget -q https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-linux64-gpl.tar.xz -O /tmp/ff.tar.xz
tar -xf /tmp/ff.tar.xz -C /tmp
cp /tmp/ffmpeg-*/bin/{ffmpeg,ffprobe} bin/
chmod +x bin/ffmpeg bin/ffprobe
```

```bash
python bot.py
```

### صفحات المصحف (اختياري)

ضع ملفات PNG في `data/images/{source}/`:

```
data/images/hafs/1.png  …  604.png
data/images/warsh/1.png  …
data/images/tajweed/1.png  …
```

البوت يخزّن file\_id تلقائياً في `ids.json` بعد أول إرسال.

### ملفات التفسير المحلية (اختياري)

```
data/tafsir/muyassar.json   {"1:1": "نص التفسير", ...}
data/tafsir/jalalayn.json
```

إن لم تكن موجودة، يُرجع البوت إلى alquran.cloud API.

---

## الدعم

| | |
|---|---|
| 💳 PayPal | `paypal.com/ncp/payment/W78F6W4TXZ4CS` |
| 🔸 Binance | `1011264323` |
| 🟡 Bybit | `467077834` |
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
