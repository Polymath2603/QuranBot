<div align="center">

# 🌙 بوت القرآن الكريم

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21+-229ED9)](https://github.com/python-telegram-bot/python-telegram-bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

🇸🇦 العربية · [🌐 English](README.en.md)

</div>

---

بوت تيليجرام للقرآن الكريم. ابحث بالآية أو السورة أو الصفحة، استمع بصوت 18 قارئاً، اقرأ التفسير، وصدّر ملفات الترجمة — أو اطلب فيديو الآية مباشرة.

---

## المميزات

- 🎬 **توليد فيديو** — فيديو لكل آية مع الصوت المتزامن، أفقي أو عمودي. الوحيد في تيليجرام.
- 🎧 **18 قارئاً** — العفاسي، السديس، عبد الباسط، الحصري، وغيرهم.
- 🔍 **بحث ذكي** — يبحث في النص الكامل مع تطبيع عربي شامل (ألفات، تشكيل، همزات).
- 📚 **تفسيران** — الميسر والجلالين مع تصفح بالصفحات.
- 📄 **تصدير** — TXT وSRT وLRC مع توقيتات دقيقة.
- ⚡ **إرسال فوري** — الملفات المولَّدة مُخزَّنة، والطلبات المكررة تُرسَل فوراً.
- 🌐 **عربي وإنجليزي** — واجهة بالكامل بالغتين.

---

## طريقة الاستخدام

أرسل اسم سورة أو رقم آية أو صفحة أو نصاً عربياً للبحث:

| المدخل | مثال |
|---|---|
| سورة + آية | `البقرة ٢٥٥` · `Baqarah 255` |
| نطاق | `الفاتحة ١ إلى ٧` · `1:1-7` |
| اسم سورة | `الكهف` · `Kahf` |
| صفحة | `صفحة ٥` · `page 5` |
| بحث | `وما توفيقي إلا بالله` |

تظهر الآية مع أزرار التفاعل:

| الزر | |
|---|---|
| 📚 تفسير | التفسير |
| 📄 نص | النص أو ملف TXT / SRT / LRC |
| 🎧 صوت | الصوت |
| 🎬 فيديو | الفيديو |
| 📄 صفحة N | الصفحة في المصحف |

---

## الإعدادات

| | الخيارات |
|---|---|
| اللغة | العربية / English |
| صيغة النص | رسالة / TXT / SRT / LRC |
| التفسير | تفسير الميسر / تفسير الجلالين |
| نسبة الفيديو | أفقي 16:9 / عمودي 9:16 |
| القارئ | 18 خياراً |

---

## التشغيل الذاتي

**المتطلبات:** Python 3.10+ وFFmpeg

```bash
git clone https://github.com/yourname/quranbot
cd quranbot
pip install -r requirements.txt
```

أنشئ ملف `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

```bash
python bot.py
```

**الإعدادات الرئيسية في `config.py`:**

```python
ADMIN_IDS            = [123456789]
MAX_AYAS_PER_REQUEST = 50          # حد النطاقات؛ السور الكاملة بلا حد
VIDEO_DEFAULT_RATIO  = "landscape" # أو "portrait"
DEFAULT_VOICE        = "Alafasy_64kbps"
```

---

## الدعم

| | |
|---|---|
| 💳 PayPal | `paypal.com/ncp/payment/W78F6W4TXZ4CS` |
| 🔶 Binance ID | `1011264323` |
| 🟡 Bybit ID | `467077834` |
| ₿ BTC | `15kPSKNLEgVH6Jy3RtNaT2mPsxTMS6MAEp` |
| 🔷 ETH / BNB | `0xc4f7076dd25a38f2256b5c23b8ca859cc42924cf` |
| 🟣 SOL | `EWcxGVtbohy8CdFLb2HNUqSHdecRiWKLywgMLwsXByhn` |

---

## مصادر

نص القرآن وبيانات الصفحات: [Tanzil.net](https://tanzil.net)
الملفات الصوتية: [EveryAyah.com](https://everyayah.com)
التفسير: [AlQuran.cloud](https://alquran.cloud)
الخط العثماني: [KFGQPC](https://fonts.qurancomplex.gov.sa) — مجمع الملك فهد لطباعة المصحف الشريف
