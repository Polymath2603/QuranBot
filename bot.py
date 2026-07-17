#!/usr/bin/env python3
"""bot.py — thin entrypoint.

The Telegram bot implementation lives in bot_handlers.py (handlers + wiring),
with the callback router in bot_router.py. This module exists so the documented
`python3 bot.py` launch command keeps working; it just delegates to main().
"""
from bot_handlers import main

if __name__ == "__main__":
    main()
