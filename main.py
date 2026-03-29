#!/usr/bin/env python3
"""
Yahoo Inbox Cleaner
-------------------
Manage Yahoo emails using plain-English queries powered by an LLM.
Supports: delete, move to folder, archive.

Usage:
  python main.py                             # interactive mode
  python main.py --query "move all LinkedIn emails to To Review"
  python main.py --query "delete all Grab emails older than 3 months" --confirm
  python main.py --list-folders
"""

import argparse
import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from llm_parser import parse_query_with_llm
from cleaner import connect_to_yahoo, list_folders, run_cleanup


BANNER = """
╔══════════════════════════════════════════════╗
║       Yahoo Inbox Cleaner  🧹                ║
║  Plain-English Email Cleanup with LLM        ║
╚══════════════════════════════════════════════╝
"""

EXAMPLE_QUERIES = [
    "Move all LinkedIn emails to a folder called To Review",
    "Move all emails from Shopee to Shopee Cleanup folder",
    "Delete all emails from newsletters older than 6 months",
    "Move emails from grab.com to a review folder",
    "Delete all emails with 'unsubscribe' in the subject",
    "Move all Facebook emails to Social folder",
    "Delete all emails older than 1 year",
]


def interactive_mode():
    print(BANNER)
    print("LLM Provider:", os.getenv("LLM_PROVIDER", "groq").upper())
    print("\nExample queries:")
    for i, q in enumerate(EXAMPLE_QUERIES, 1):
        print(f"  {i}. {q}")

    print("\nType your query below (or 'quit' to exit):\n")

    while True:
        try:
            query = input("📬 What do you want to do?\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue

        # Dry run first — show preview
        process_query(query, dry_run=True)

        # Single confirmation prompt
        confirm = input("Type 'confirm' to proceed, or press Enter to cancel: ").strip().lower()
        if confirm == "confirm":
            process_query(query, dry_run=False)

        another = input("\nDo something else? (y/n): ").strip().lower()
        if another != "y":
            break

    print("\nDone. Check logs/cleaner.log for full history.")


def process_query(query: str, dry_run: bool = True):
    print(f"\n🤖 Interpreting: \"{query}\"")
    try:
        parsed = parse_query_with_llm(query)
    except Exception as e:
        print(f"❌ LLM parsing failed: {e}")
        return
    print(f"✅ Understood as: {parsed['description']}")
    run_cleanup(parsed, dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Yahoo Inbox Cleaner — manage emails with plain-English queries"
    )
    parser.add_argument("--query", "-q", type=str, help="Plain-English email management query")
    parser.add_argument("--confirm", action="store_true", help="Execute action (default is dry-run preview)")
    parser.add_argument("--list-folders", action="store_true", help="List all folders in your Yahoo mailbox")

    args = parser.parse_args()

    if args.list_folders:
        mail = connect_to_yahoo()
        folders = list_folders(mail)
        print("\nYour Yahoo folders:")
        for f in folders:
            print(f"  📁 {f}")
        mail.logout()
        return

    if args.query:
        process_query(args.query, dry_run=not args.confirm)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
