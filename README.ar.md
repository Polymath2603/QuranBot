<div align="center">

# 🌙 بوت القرآن الكريم

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21+-229ED9)](https://github.com/python-telegram-bot/python-telegram-bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

🇸🇦 العربية · [🌐 English](README.md)

**[▶️ افتح البوت](https://t.me/YOUR_BOT_USERNAME)** · **[📢 القناة](https://t.me/YOUR_CHANNEL_USERNAME)**

</div>

---

مجموعة أدوات شاملة للقرآن الكريم تتضمن بوت تيليجرام قوي وأدوات مكتبية مستقلة (GUI/CLI) لإنتاج فيديوهات آيات عالية الجودة.

---

## ✨ المميزات

- 📖 **Mushaf API** — عرض صفحات المصحف بجودة عالية (حفص، ورش، التجويد) عبر خادم عن بعد أو محلياً.
- 🎬 **محرك فيديو عالمي** — توليد فيديوهات للآيات مع صوت متزامن، حدود للنص، وخلفيات ديناميكية.
- 🖥️ **واجهة مكتبية (GUI)** — تطبيق Python/Tkinter لإنتاج فيديوهات الآيات مع خاصية حفظ الإعدادات تلقائياً.
- ⌨️ **أداة سطر الأوامر (CLI)** — توليد الفيديوهات بدون واجهة، مثالية للأتمتة ولمحبي الـ terminal.
- 🎨 **قوالب برمجية (Templates)** — اختر بين النمط `default` (التقليدي) أو `enhanced` (مع أسماء سور ورموز غرافيكية ثابتة).
- 🎧 **25+ قارئاً** — دعم كامل لقرّاء everyayah.com مع التخزين التلقائي.
- 🔍 **بحث ذكي** — بحث في النص الكامل مع تمييز الكلمات المطابقة وتطبيع عربي شامل.
- 📚 **12+ تفسيراً** — مكتبة شاملة تشمل الميسر والجلالين وترجمات بلغات متعددة.
- 📄 **تصدير** — ملفات SRT وLRC مع توقيتات دقيقة لكل آية.

---

## 🚀 أدوات المكتب (جديد!)

### 🖥️ واجهة الفيديو (GUI)
أنتج فيديوهات قرآنية احترافية لوسائل التواصل الاجتماعي دون الحاجة لكتابة كود.
- **إعدادات محفوظة**: التطبيق يتذكر اختيارك للقراء، الألوان، والمسارات.
- **اختيار ملفات أصلي**: يدعم `Zenity` (لينكس) أو الحمالات القياسية لتوافق كامل مع النظام.
- **تحديث تلقائي**: ضبط نطاق الآيات تلقائياً عند تغيير السورة.

```bash
python3 video_gui.py
```

### ⌨️ أداة سطر الأوامر (CLI)
مثالية للأتمتة والبيئات التي لا تدعم الواجهات الرسومية.
- **تحكم كامل**: تجاوز الخطوط، الألوان، القوالب، والخلفيات عبر الأوامر.
- **سريع**: يستخدم نفس محرك FFmpeg عالي الأداء الخاص بالبوت.

```bash
# مثال: توليد سورة الكوثر بصوت العفاسي والقالب المحسّن
python3 video_cli.py -s 108 -v Alafasy_64kbps -t enhanced -o kawthar.mp4
```

---

## 🤖 بوت التيليجرام

يبقى البوت هو الواجهة الأساسية للتفاعل العام:
- **تصفح المصحف**: `/page <n>`
- **البحث في الآيات**: `/search <query>`
- **أحاديث يومية**: جدولة النشر التلقائي في القنوات.
- **تسريع العتاد**: دعم مدمج لـ NVENC (NVIDIA) وVAAPI وVideoToolbox.

---

## 🛠️ التشغيل

**المتطلبات:** Python 3.10+، FFmpeg

1. **التحميل والتثبيت**:
   ```bash
   git clone https://github.com/yourname/quranbot
   cd quranbot
   pip install -r requirements.txt
   ```

2. **إعداد البيئة**:
   ```bash
   cp .env.example .env
   # أدخل BOT_TOKEN والبيانات الأخرى
   ```

3. **التشغيل**:
   - لتشغيل بوت تيليجرام: `python3 bot.py`
   - لتشغيل واجهة الفيديو: `python3 video_gui.py`

---

## ☕ الدعم

إذا وجدت هذا المشروع مفيداً، يمكنك دعم استمرار تطويره:

| | |
|---|---|
| 💳 **PayPal** | `paypal.com/ncp/payment/W78F6W4TXZ4CS` |
| 🔸 **Binance** | `1011264323` |
| 🟡 **Bybit** | `467077834` |
| 🟢 **TRC20** | `TMW5uSDN6sMUBNirMoqY1icpsfa7GhPZfK` |
| 🟢 **BEP20/ERC20** | `0x7a8887c2ac3e596f6170c9e28b44e6b6d025c854` |
| 🔵 **LTC** | `LVswXiD6Vd2dejXvGbZLa1R8jkvg748F4q` |
| 🔵 **TON** | `UQAllRezWgHi3LPrSwyvAb4zazIph6j6goU7lMaqcFWFBxVH` |
| 🟠 **BTC** | `1rSX6BDN1nqDMyBHqceySkZSs6PHUP23m` |
| 🟣 **SOL** | `d8RonhC8oEHssrQjN1Y4UWHnd6MMP33XGCKtfNL4j59` |
| ⭐ **Telegram Stars** | عبر البوت مباشرة |

---

## 📖 مصادر البيانات

| | المصدر | الرخصة |
|---|---|---|
| نص القرآن + البيانات | [Tanzil.net](https://tanzil.net) | CC BY 3.0 |
| الملفات الصوتية | [EveryAyah.com](https://everyayah.com) | مجاني، غير تجاري |
| API التفسير | [AlQuran.cloud](https://alquran.cloud/api) | مجاني |
| الخط العثماني | [KFGQPC](https://fonts.qurancomplex.gov.sa) | مجاني، غير تجاري |
| قواعد الأحاديث | [IsmailHosenIsmailJames](https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite) | MIT |
