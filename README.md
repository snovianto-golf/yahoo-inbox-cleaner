# Yahoo Inbox Cleaner

A prototype CLI tool that lets you clean up your Yahoo Mail inbox by typing plain English commands. No need to know IMAP syntax or dig through Yahoo's filter settings.

Built as part of my personal study on AI and LLMs.

---

## Problem Statement

I had thousands of emails piling up in Yahoo Mail and no easy way to bulk clean them. Yahoo's built-in tools are limited and manual deletion is painful. I wanted to see if an LLM could sit in the middle, understand what I want in plain English, and handle the technical side automatically.

This project is a working prototype that does exactly that. You describe what you want, the LLM translates it into an IMAP query, and the script connects to Yahoo and runs it.

Core things I was exploring:

- Can an LLM reliably convert natural language into structured IMAP queries?
- How do you build a safe-by-default tool where nothing gets deleted without confirmation?
- How do you support multiple LLM providers with the same interface?

---

## What It Can Do

- Move emails to a folder so you can review before deleting
- Bulk delete by sender, subject keyword, age, or read/unread status
- Archive emails to Yahoo archive
- Preview matching emails before any action runs (dry-run by default)
- Works with Claude, Groq, Gemini, or a local Ollama model

---

## How It Works

You type something like:

```
move all LinkedIn emails to a folder called To Review
```

The LLM converts that into:

```json
{
  "folder": "INBOX",
  "imap_criteria": "OR FROM \"@linkedin.com\" FROM \"@e.linkedin.com\"",
  "action": "move",
  "target_folder": "To Review",
  "description": "Move all LinkedIn emails to To Review folder"
}
```

The script connects to Yahoo via IMAP, searches for matching emails, shows you a sample preview, and waits for you to confirm before doing anything.

---

## Supported LLM Providers

| Provider | Cost | Model | Link |
|---|---|---|---|
| Groq | Free tier | Llama 3.3 70B | [console.groq.com](https://console.groq.com) |
| Gemini | Free tier | Gemini 1.5 Flash | [aistudio.google.com](https://aistudio.google.com) |
| Claude | Paid | Claude Sonnet | [console.anthropic.com](https://console.anthropic.com) |
| Ollama | Free, runs locally | Llama 3 | [ollama.ai](https://ollama.ai) |

Groq is recommended to start. It is free, fast, and does not require a credit card.

---

## Requirements

- Python 3.8 or higher
- Yahoo Mail account with IMAP enabled
- Yahoo App Password (different from your main Yahoo password)
- API key from one LLM provider

---

## Installation

**1. Clone the repo**

```bash
git clone https://github.com/YOUR_USERNAME/yahoo-inbox-cleaner.git
cd yahoo-inbox-cleaner
```

**2. Install dependencies**

```bash
pip install python-dotenv groq anthropic
```

**3. Enable IMAP in Yahoo Mail**

- Log into Yahoo Mail
- Go to Settings > More Settings > Mailboxes
- Turn on IMAP access

**4. Generate a Yahoo App Password**

Yahoo does not allow third-party apps to use your main password. You need to generate a separate app password.

- Go to [myaccount.yahoo.com/security](https://myaccount.yahoo.com/security)
- Click Generate app password
- Choose Other app and name it anything you like
- Copy the 16-character password that appears
- Remove the spaces before using it (e.g. `abcd efgh ijkl mnop` becomes `abcdefghijklmnop`)

**5. Get a free Groq API key**

- Sign up at [console.groq.com](https://console.groq.com)
- Go to API Keys and create a new key
- Copy it

**6. Create your .env file**

```bash
nano .env
```

Paste this and fill in your values:

```
YAHOO_EMAIL=yourname@yahoo.com
YAHOO_APP_PASSWORD=abcdefghijklmnop
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
```

Save with Ctrl+X, then Y, then Enter.

**7. Create the logs folder**

```bash
mkdir -p logs
```

---

## Running the Tool

**Interactive mode**

```bash
python main.py
```

This is the easiest way to use it. Type your request, see the preview, then type `confirm` to run it.

Example:

```
📬 What do you want to do?
> move all LinkedIn emails to To Review

🤖 Interpreting: "move all LinkedIn emails to To Review"
✅ Understood as: Move all LinkedIn emails to To Review folder

📬 Source  : INBOX
🔍 Filter  : OR FROM "@linkedin.com" FROM "@e.linkedin.com"
⚡ Action  : Move to 'To Review'

Found 47 emails matching your query.

Sample emails:
  1. From    : LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>
     Subject : 10 new jobs for you in Singapore
     Date    : Sat, 29 Mar 2026

[DRY RUN] Would move 47 emails.

Type 'confirm' to proceed, or press Enter to cancel: confirm
✅ Moved 47 emails to 'To Review'.
```

**Single query mode**

```bash
# Preview only (safe, nothing changes)
python main.py --query "delete all emails older than 1 year"

# Run immediately
python main.py --query "delete all emails older than 1 year" --confirm
```

**List your Yahoo folders**

```bash
python main.py --list-folders
```

---

## Example Queries

| Query | What it does |
|---|---|
| `move all LinkedIn emails to To Review` | Moves to a folder for you to check first |
| `move all Shopee emails to Shopee Cleanup` | Creates the folder if it does not exist |
| `delete all emails older than 1 year` | Bulk delete by age |
| `delete all newsletters older than 6 months` | Subject keyword plus age filter |
| `move all Facebook emails to Social` | Groups by sender into one folder |
| `delete emails with unsubscribe in the subject` | Subject keyword filter |
| `move emails from grab.com to review` | Filter by sender domain |
| `clean out my spam folder` | Empties Spam or Bulk Mail |

---

## Project Structure

```
yahoo-inbox-cleaner/
├── main.py              # CLI entry point
├── src/
│   ├── cleaner.py       # IMAP logic: connect, search, move, delete
│   └── llm_parser.py    # Converts natural language to IMAP JSON via LLM
├── logs/
│   └── cleaner.log      # Audit log of all actions
├── .env                 # Your credentials (gitignored)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Privacy and Safety

Nothing is deleted or moved without you typing `confirm`. Every run shows a preview of matched emails first.

The LLM only receives your plain-English query. Your actual emails, email addresses, subjects, and Yahoo credentials never get sent to any LLM provider. Everything runs locally except the query string.

Your `.env` file is blocked from git by `.gitignore` so credentials will not be pushed to GitHub by accident.

The Yahoo App Password can be revoked anytime from Yahoo security settings without affecting your main account.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `YAHOO_EMAIL not set` | Check your .env file exists and is filled in correctly |
| `IMAP login failed` | Regenerate your Yahoo App Password and update .env |
| `ModuleNotFoundError` | Run `pip install python-dotenv groq anthropic` |
| `No such file logs/` | Run `mkdir -p logs` |
| `LLM parsing failed` | Check your Groq API key is valid |

---

## Ideas for Future Work

- Schedule automated cleanup with cron or n8n
- Support Gmail and Outlook with the same interface
- Build a simple web UI for non-technical users
- Detect and handle unsubscribe links automatically
- Show analytics on which senders fill up your inbox the most

---

## About

Built by [Novianto](https://github.com/YOUR_USERNAME) as a hands-on prototype while studying AI and LLM applications. The goal was to build something practical that solves a real problem, not just a tutorial project.

---

## License

MIT
