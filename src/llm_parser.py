import os
import json
import re

SYSTEM_PROMPT = """You are an email cleanup assistant. The user will describe in plain English which emails they want to manage.

Your job is to convert their request into a structured JSON object with these fields:
- "folder": source IMAP folder to search in (usually "INBOX")
- "imap_criteria": valid IMAP search string
- "action": one of "delete", "move", or "archive"
- "target_folder": only needed when action is "move" — the destination folder name (e.g. "To Review", "Cleanup")
- "description": short human-readable summary of what will happen

IMAP criteria reference:
- By sender email:    FROM "newsletter@company.com"
- By sender domain:   FROM "@linkedin.com"
- By subject keyword: SUBJECT "newsletter"
- By age (seconds):   OLDER 2592000  (30d=2592000, 90d=7776000, 180d=15552000, 1yr=31536000)
- By date:            BEFORE 01-Jan-2024
- Unread only:        UNSEEN
- Read only:          SEEN
- Combine (AND):      FROM "@linkedin.com" OLDER 2592000
- OR two senders:     OR FROM "@linkedin.com" FROM "@e.linkedin.com"

Common sender patterns:
- LinkedIn:   FROM "@linkedin.com" OR FROM "@e.linkedin.com"  → use: OR FROM "@linkedin.com" FROM "@e.linkedin.com"
- Facebook:   FROM "@facebookmail.com"
- Twitter/X:  OR FROM "@twitter.com" FROM "@x.com"
- Google:     FROM "@google.com"
- Grab:       FROM "@grab.com"
- Shopee:     FROM "@shopee.com"
- Lazada:     FROM "@lazada.com"
- Stripe:     FROM "@stripe.com"

Action rules:
- "move to [folder]", "put in [folder]", "review first", "let me check first" → action = "move", set target_folder
- "delete", "remove", "clean out", "get rid of" → action = "delete"
- "archive" → action = "archive"
- When unsure or user wants to review → default action = "move", target_folder = "To Review"

Yahoo built-in folders: INBOX, Sent, Trash, Draft, Spam, Bulk Mail
Custom folders: use the exact name the user says, or "To Review" as the safe default

Reply ONLY with a raw JSON object. No explanation, no markdown fences, no backticks.

Examples:
{"folder":"INBOX","imap_criteria":"OR FROM \\"@linkedin.com\\" FROM \\"@e.linkedin.com\\"","action":"move","target_folder":"To Review","description":"Move all LinkedIn emails to To Review folder"}
{"folder":"INBOX","imap_criteria":"FROM \\"@grab.com\\" OLDER 7776000","action":"delete","target_folder":null,"description":"Delete Grab emails older than 90 days"}
{"folder":"INBOX","imap_criteria":"FROM \\"@shopee.com\\"","action":"move","target_folder":"Shopee Cleanup","description":"Move all Shopee emails to Shopee Cleanup folder"}
"""


def parse_query_with_llm(user_query: str) -> dict:
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    if provider == "claude":
        return _query_claude(user_query)
    elif provider == "groq":
        return _query_groq(user_query)
    elif provider == "gemini":
        return _query_gemini(user_query)
    elif provider == "ollama":
        return _query_ollama(user_query)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Choose: claude, groq, gemini, ollama")


def _query_claude(user_query: str) -> dict:
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run: pip install anthropic")
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_query}]
    )
    return _parse_json_response(response.content[0].text)


def _query_groq(user_query: str) -> dict:
    try:
        from groq import Groq
    except ImportError:
        raise ImportError("Run: pip install groq")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ],
        max_tokens=300,
        temperature=0
    )
    return _parse_json_response(response.choices[0].message.content)


def _query_gemini(user_query: str) -> dict:
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("Run: pip install google-generativeai")
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(
        model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        system_instruction=SYSTEM_PROMPT
    )
    response = model.generate_content(user_query)
    return _parse_json_response(response.text)


def _query_ollama(user_query: str) -> dict:
    try:
        import requests
    except ImportError:
        raise ImportError("Run: pip install requests")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ],
        "stream": False
    }
    resp = requests.post(f"{base_url}/api/chat", json=payload, timeout=60)
    resp.raise_for_status()
    return _parse_json_response(resp.json()["message"]["content"])


def _parse_json_response(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        result = json.loads(cleaned)
        for key in ("folder", "imap_criteria", "action", "description"):
            if key not in result:
                raise ValueError(f"Missing key in LLM response: {key}")
        if result["action"] not in ("delete", "move", "archive"):
            raise ValueError(f"Invalid action: {result['action']}")
        return result
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"LLM returned invalid JSON:\n{raw}\nError: {e}")
