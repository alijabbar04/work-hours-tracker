"""Optional, explicit Anthropic note summarisation and OS credential storage."""

import os

import requests

from .config import KEYRING_SERVICE, KEYRING_USER

try:
    import keyring
except Exception:
    keyring = None

MODEL = os.environ.get("WORK_HOURS_TRACKER_AI_MODEL", "claude-haiku-4-5-20251001")


def get_api_key():
    if _secure_keyring():
        try:
            k = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
            if k:
                return k
        except Exception:
            pass
    return os.environ.get("ANTHROPIC_API_KEY")


def save_api_key(k):
    if not _secure_keyring():
        raise RuntimeError("Secure OS credential storage is unavailable. "
                           "Use ANTHROPIC_API_KEY for this session, or keep AI disabled.")
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, k.strip())
    except Exception:
        raise RuntimeError("Could not save the key in the OS credential store.") from None


def _secure_keyring():
    """Accept OS-backed stores only; refuse third-party plaintext fallbacks."""
    if keyring is None:
        return False
    try:
        backend = keyring.get_keyring()
        module = type(backend).__module__
        return any(module.startswith(prefix) for prefix in (
            "keyring.backends.Windows", "keyring.backends.macOS",
            "keyring.backends.SecretService", "keyring.backends.kwallet",
        )) and backend.priority > 0
    except Exception:
        return False


def claude_bullets(api_key, raw):
    if not api_key or not str(raw).strip():
        raise ValueError("An API key and work notes are required.")
    prompt = (
        "Turn the following rough work notes into 2-5 concise, past-tense "
        "bullet points summarising what was done that day. Start each bullet "
        "with '• '. Be specific but brief. Output ONLY the bullets, with "
        "no preamble, headings or closing text.\n\nNOTES:\n" + raw
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
    except requests.RequestException:
        raise RuntimeError("Could not reach Anthropic. Check your connection and try again.") from None
    if not r.ok:
        # Do not expose response bodies or request/exception objects: they can
        # contain notes, tokens or other private data.
        raise RuntimeError(f"Anthropic returned HTTP {r.status_code}. "
                           "Check your key, billing and API access.")
    try:
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", [])).strip()
    except (ValueError, TypeError, AttributeError):
        raise RuntimeError("Anthropic returned an unexpected response. Try again later.") from None
