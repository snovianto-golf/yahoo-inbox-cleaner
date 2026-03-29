import imaplib
import email
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/cleaner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

YAHOO_IMAP_HOST = "imap.mail.yahoo.com"
YAHOO_IMAP_PORT = 993


def connect_to_yahoo():
    email_addr = os.getenv("YAHOO_EMAIL")
    app_password = os.getenv("YAHOO_APP_PASSWORD")
    if not email_addr or not app_password:
        raise ValueError("YAHOO_EMAIL and YAHOO_APP_PASSWORD must be set in .env")
    logger.info(f"Connecting to Yahoo IMAP as {email_addr}...")
    mail = imaplib.IMAP4_SSL(YAHOO_IMAP_HOST, YAHOO_IMAP_PORT)
    mail.login(email_addr, app_password)
    logger.info("Connected successfully.")
    return mail


def list_folders(mail):
    _, folders = mail.list()
    folder_names = []
    for f in folders:
        parts = f.decode().split('"')
        name = parts[-1].strip().strip('"')
        folder_names.append(name)
    return folder_names


def ensure_folder_exists(mail, folder_name):
    """Create folder if it doesn't already exist."""
    _, folders = mail.list()
    existing = [f.decode().split('"')[-1].strip().strip('"') for f in folders]
    if folder_name not in existing:
        mail.create(f'"{folder_name}"')
        logger.info(f"Created folder: '{folder_name}'")
    else:
        logger.info(f"Folder already exists: '{folder_name}'")


def search_emails(mail, folder, imap_criteria):
    try:
        mail.select(folder, readonly=True)
    except Exception as e:
        logger.error(f"Could not select folder '{folder}': {e}")
        return []
    try:
        _, data = mail.search(None, imap_criteria)
        ids = data[0].split()
        return ids
    except Exception as e:
        logger.error(f"Search failed with criteria '{imap_criteria}': {e}")
        return []


def fetch_email_samples(mail, email_ids, max_samples=5):
    samples = []
    for eid in email_ids[:max_samples]:
        _, data = mail.fetch(eid, "(RFC822.HEADER)")
        msg = email.message_from_bytes(data[0][1])
        samples.append({
            "from": msg.get("From", "(unknown)"),
            "subject": msg.get("Subject", "(no subject)"),
            "date": msg.get("Date", "(unknown date)")
        })
    return samples


def move_emails(mail, source_folder, email_ids, target_folder, batch_size=50):
    """Move emails to a target folder using IMAP COPY + delete.
    Re-selects folder each batch and expunges immediately to keep
    sequence numbers fresh and avoid stale ID errors on large mailboxes.
    """
    ensure_folder_exists(mail, target_folder)
    total = len(email_ids)
    moved = 0

    for i in range(0, total, batch_size):
        # Re-select source folder each batch so sequence numbers stay fresh
        mail.select(source_folder)
        batch = email_ids[i:i + batch_size]
        id_str = b",".join(batch)
        result, _ = mail.copy(id_str, f'"{target_folder}"')
        if result == "OK":
            mail.store(id_str, "+FLAGS", "\\Deleted")
            mail.expunge()  # Expunge per batch to keep IDs stable
            moved += len(batch)
            logger.info(f"Moved {moved}/{total} emails to '{target_folder}'...")
        else:
            logger.error(f"Copy failed for batch at index {i}")

    logger.info(f"Done. Moved {moved} emails to '{target_folder}'.")
    return moved


def delete_emails(mail, folder, email_ids, batch_size=50):
    """Permanently delete emails."""
    total = len(email_ids)
    deleted = 0

    for i in range(0, total, batch_size):
        mail.select(folder)
        batch = email_ids[i:i + batch_size]
        id_str = b",".join(batch)
        mail.store(id_str, "+FLAGS", "\\Deleted")
        mail.expunge()
        deleted += len(batch)
        logger.info(f"Deleted {deleted}/{total} emails...")

    logger.info(f"Permanently deleted {total} emails from '{folder}'.")
    return total


def archive_emails(mail, folder, email_ids):
    """Move emails to Yahoo's Archive folder."""
    return move_emails(mail, folder, email_ids, "Archive")


def run_cleanup(query_result: dict, dry_run: bool = True):
    mail = connect_to_yahoo()

    source_folder = query_result.get("folder", "INBOX")
    imap_criteria = query_result.get("imap_criteria", "ALL")
    action        = query_result.get("action", "delete")
    target_folder = query_result.get("target_folder")
    description   = query_result.get("description", "matching emails")

    action_label = {
        "delete":  "🗑  Delete",
        "move":    f"📁 Move to '{target_folder}'",
        "archive": "📦 Archive"
    }.get(action, action)

    print(f"\n📬 Source  : {source_folder}")
    print(f"🔍 Filter  : {imap_criteria}")
    print(f"⚡ Action  : {action_label}")
    print(f"📝 Summary : {description}\n")

    email_ids = search_emails(mail, source_folder, imap_criteria)

    if not email_ids:
        print("✅ No emails matched. Nothing to do.")
        mail.logout()
        return

    print(f"Found {len(email_ids)} email(s) matching your query.\n")

    samples = fetch_email_samples(mail, email_ids)
    print("Sample emails:")
    for i, s in enumerate(samples, 1):
        print(f"  {i}. From    : {s['from'][:60]}")
        print(f"     Subject : {s['subject'][:65]}")
        print(f"     Date    : {s['date']}\n")

    if dry_run:
        print(f"[DRY RUN] Would {action} {len(email_ids)} emails.")
        print("Type 'confirm' at the next prompt to proceed.\n")
        mail.logout()
        return

    # --- Single confirmation, no second prompt ---
    if action == "delete":
        count = delete_emails(mail, source_folder, email_ids)
        print(f"\n✅ Deleted {count} emails.")

    elif action == "move":
        if not target_folder:
            target_folder = "To Review"
        count = move_emails(mail, source_folder, email_ids, target_folder)
        print(f"\n✅ Moved {count} emails to '{target_folder}'.")

    elif action == "archive":
        count = archive_emails(mail, source_folder, email_ids)
        print(f"\n✅ Archived {count} emails.")

    mail.logout()
