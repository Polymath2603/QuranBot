# QuranBot Roadmap (TODO)

## 📌 High Priority / Next Features
1. **Bookmarks**: Add a `🔖` button to the `more` keyboard in `verses.py` alongside a `/bookmarks` list view.
2. **Daily Verse Push**: Add a subscription flag (`/subscribe`) to send a beautiful verse every day organically.
3. **Smart Replies**: Suggest the next logical verse or consecutive flow based on previous queries.
4. **Quiz / Memorization Mode**: Present a verse with missing words or ask "What is the next aya?".

## 🎨 UI/UX Improvements
* **Pagination in Search**: The current search results show up to N ayas. Implement an inline pagination button system for large results.
* **Menu Organization**: Group settings into sub-menus to prevent the main settings page from becoming overwhelming as more options get added.
* **Better Visual Feedback**: Add loading "typing..." or "uploading..." statuses while FFmpeg is processing media in the background.

## ⚡ Performance Optimization
* **Database Connection Pooling**: Move to `async_scoped_session` in SQLAlchemy for better handling of heavy concurrent telegram loads.
* **Hardware Acceleration**: Implement NVENC/VAAPI for `ffmpeg` generating video passes to speed up render times dramatically.
* **Pre-Caching**: Pre-render common ayat (like Ayatul Kursi, Al-Fatiha) in the background when server CPU is idle.

## 🛠 Technical Debt
* **Typing & Linting**: Clean up several private member access warnings (`_font`, `_wrap`, etc.) and ensure strict Pyright pass across the board.
* **Logging System**: Pipe logs to a more robust aggregator like Datadog or ELK instead of local `bot.log` files if the userbase scales.
* **Queue Persistence**: The `_cancelled_ids` set is cleared on restart which might orphan some tasks. Add a dedicated `cancellation` status query lookup during boot.

## 🐞 Known Bugs
* No major blocking bugs currently reported.
* Extremely long verses (e.g., Al-Baqarah 282) may still stretch vertically too much in portrait video mode. Text wrapping logic scaling may need edge-case tweaking.
