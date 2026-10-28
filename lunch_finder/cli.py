from __future__ import annotations

import argparse
from pathlib import Path

from lunch_finder.config import AppConfig
from lunch_finder.env import load_dotenv
from lunch_finder.monitor import run_once
from lunch_finder.notifiers import TelegramNotifier


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl and rank nearby lunch offers.")
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the digest without sending Telegram or marking offers notified.",
    )
    parser.add_argument(
        "--show-chat-ids",
        action="store_true",
        help="List Telegram chats seen by the bot, without sending a message.",
    )
    args = parser.parse_args()

    load_dotenv()
    config = AppConfig.from_file(args.config)
    if args.show_chat_ids:
        candidates = TelegramNotifier(config.telegram).chat_candidates()
        if not candidates:
            print("No chats found. Send /start to the bot or a message in its group, then retry.")
        for chat_id, chat_type, title in candidates:
            print(f"{chat_id}\t{chat_type}\t{title}")
        return
    selected, failures = run_once(config, dry_run=args.dry_run)
    print(f"Selected {len(selected)} new offer(s).")
    for failure in failures:
        print(f"WARNING {failure.restaurant_name}: {failure.error}")


if __name__ == "__main__":
    main()
