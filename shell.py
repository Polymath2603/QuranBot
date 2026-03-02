#!/usr/bin/env python3
"""VPS Shell Bot — persistent pty session with live-streaming output."""

import asyncio
import fcntl
import logging
import os
import pty
import re
import signal
import subprocess
import sys

from telegram import Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    MessageHandler, filters, ContextTypes,
)

# ── Hardcoded credentials (personal, not in git) ───────────────────────────
BOT_TOKEN = "YOUR_SHELL_BOT_TOKEN"
ADMIN_IDS = [123456789]   # your Telegram user ID(s)

EDIT_INTERVAL = 0.8    # seconds between live edits
TAIL_CHARS    = 1000   # visible chars kept in the live message
IDLE_TIMEOUT  = 8.0    # seconds of silence → stop reading

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

_ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07|\r')

_HERE = os.path.dirname(os.path.abspath(__file__))


# ── Persistent bash session ────────────────────────────────────────────────
class _Session:
    def __init__(self):
        self.pid: int | None = None
        self.fd:  int | None = None
        self._spawn()

    def _spawn(self):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:                       # child process
            os.execvpe("bash", ["bash"], {**os.environ, "TERM": "dumb", "PS1": ""})
        # parent — make reads non-blocking
        flags = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def send(self, cmd: str):
        os.write(self.fd, (cmd.rstrip("\n") + "\n").encode())

    def read(self) -> str:
        try:
            return os.read(self.fd, 8192).decode(errors="replace")
        except (BlockingIOError, OSError):
            return ""

    def reset(self):
        try:
            if self.pid:
                os.kill(self.pid, signal.SIGKILL)
                os.waitpid(self.pid, os.WNOHANG)
        except OSError:
            pass
        try:
            if self.fd is not None:
                os.close(self.fd)
        except OSError:
            pass
        self.pid = self.fd = None
        self._spawn()


_session = _Session()


def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


# ── Handlers ───────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "🖥 Shell ready — send any command.\n"
        "/reset to start a fresh session."
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    _session.reset()
    await update.message.reply_text("♻️ Session reset.")


async def handle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    cmd = update.message.text.strip()
    if not cmd:
        return

    _session.send(cmd)
    live = await update.message.reply_text("⏳")

    buf       = ""
    last_sent = ""
    loop      = asyncio.get_event_loop()
    deadline  = loop.time() + IDLE_TIMEOUT

    while loop.time() < deadline:
        chunk = _session.read()
        if chunk:
            buf      = _ANSI.sub("", buf + chunk)
            deadline = loop.time() + IDLE_TIMEOUT   # reset idle timer on new output

        tail = buf[-TAIL_CHARS:]
        display = f"`{tail}`" if tail.strip() else "_(no output yet)_"

        if display != last_sent:
            try:
                await live.edit_text(display, parse_mode="Markdown")
                last_sent = display
            except Exception:
                pass

        await asyncio.sleep(EDIT_INTERVAL)


def main():
    if not BOT_TOKEN:
        sys.exit("BOT_TOKEN is empty — edit shell.py")
    if not ADMIN_IDS:
        sys.exit("ADMIN_IDS is empty — edit shell.py")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cmd))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
