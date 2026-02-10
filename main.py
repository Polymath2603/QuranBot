#!/usr/bin/env python3
import sys


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "cli":
            from cli import main as cli_main
            cli_main()
        elif sys.argv[1] == "bot":
            from bot import main as bot_main
            bot_main()
        else:
            print("Usage: python main.py [cli|bot]")
    else:
        print("QBot - Quran Bot")
        print("\nUsage:")
        print("  python main.py cli   - Start the CLI interface")
        print("  python main.py bot   - Start the Telegram bot")
        print("\nFor more information, see README.md")


if __name__ == "__main__":
    main()