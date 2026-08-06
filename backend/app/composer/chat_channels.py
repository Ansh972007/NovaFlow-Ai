"""Universal channel registry — any automation goal maps to caps, vault, NL paste, titles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChannelSpec:
    id: str
    friendly_name: str
    aliases: tuple[str, ...]
    cap: str
    category: str
    kind: str
    missing_labels: tuple[str, ...]
    paste_hint: str
    notify_channel: str | None = None
    node_type: str | None = None
    title_templates: tuple[str, ...] = ()
    secret_field_keys: tuple[str, ...] = ()


CHANNELS: list[ChannelSpec] = [
    ChannelSpec(
        id="email",
        friendly_name="Email (Gmail / SMTP)",
        aliases=("email", "e-mail", "gmail", "smtp", "mail"),
        cap="cap_smtp",
        category="email",
        kind="gmail_smtp",
        missing_labels=("smtp_password",),
        paste_hint="Paste: my email is you@gmail.com and password is xxxx xxxx xxxx xxxx",
        notify_channel="email",
        title_templates=("Daily email", "Email automation"),
        secret_field_keys=("smtp_password",),
    ),
    ChannelSpec(
        id="outlook",
        friendly_name="Outlook / Microsoft 365",
        aliases=("outlook", "microsoft 365", "office 365", "ms graph", "microsoft graph",
                 "outlook calendar", "microsoft calendar", "excel online", "onedrive", "sharepoint"),
        cap="cap_outlook",
        category="outlook",
        kind="microsoft_graph",
        missing_labels=("outlook_client_id", "outlook_client_secret", "outlook_refresh_token"),
        paste_hint="Paste Outlook: client_id: … client_secret: … refresh_token: …",
        notify_channel="email",
        node_type="http",
        title_templates=("Outlook mail automation",),
        secret_field_keys=("client_secret", "refresh_token", "access_token"),
    ),
    ChannelSpec(
        id="google",
        friendly_name="Google Auth / APIs",
        aliases=(
            "google auth", "google oauth", "google api", "google sheets", "google drive", "gdrive",
            "excel", "spreadsheet", "google calendar", "gcal", "google cal",
        ),
        cap="cap_google",
        category="google",
        kind="google_oauth",
        missing_labels=("google_client_id", "google_client_secret", "google_refresh_token"),
        paste_hint="Paste Google OAuth: client_id: … client_secret: … refresh_token: …",
        node_type="http",
        title_templates=("Google API automation",),
        secret_field_keys=("client_secret", "refresh_token", "access_token", "api_key"),
    ),
    ChannelSpec(
        id="shopify",
        friendly_name="Shopify",
        aliases=("shopify", "shop store", "ecommerce store"),
        cap="cap_shopify",
        category="shopify",
        kind="shopify_admin",
        missing_labels=("shopify_shop", "shopify_access_token"),
        paste_hint="Paste: shopify shop is mystore.myshopify.com and access token is shpat_…",
        node_type="http",
        title_templates=("Shopify automation",),
        secret_field_keys=("access_token", "api_key"),
    ),
    ChannelSpec(
        id="telegram",
        friendly_name="Telegram",
        aliases=("telegram",),
        cap="cap_telegram",
        category="telegram",
        kind="telegram_bot",
        missing_labels=("telegram_bot_token",),
        paste_hint="Paste: telegram token is 123456:ABC…",
        notify_channel="telegram",
        title_templates=("Telegram bot",),
        secret_field_keys=("bot_token",),
    ),
    ChannelSpec(
        id="slack",
        friendly_name="Slack",
        aliases=("slack",),
        cap="cap_slack",
        category="slack",
        kind="slack_webhook",
        missing_labels=("slack_webhook_url",),
        paste_hint="Paste: slack webhook https://hooks.slack.com/…",
        notify_channel="slack",
        title_templates=("Slack notifier",),
        secret_field_keys=("webhook_url", "bot_token"),
    ),
    ChannelSpec(
        id="discord",
        friendly_name="Discord",
        aliases=("discord",),
        cap="cap_discord",
        category="discord",
        kind="discord_webhook",
        missing_labels=("discord_webhook_url",),
        paste_hint="Paste: discord webhook https://discord.com/api/webhooks/…",
        notify_channel="discord",
        title_templates=("Discord notifier",),
        secret_field_keys=("webhook_url",),
    ),
    ChannelSpec(
        id="whatsapp",
        friendly_name="WhatsApp",
        aliases=("whatsapp", "whats app", "wa business"),
        cap="cap_whatsapp",
        category="whatsapp",
        kind="whatsapp_cloud",
        missing_labels=("whatsapp_access_token", "whatsapp_phone_number_id"),
        paste_hint="Paste: whatsapp token is … and phone number id is …",
        notify_channel="whatsapp",
        node_type="http",
        title_templates=("WhatsApp alerts",),
        secret_field_keys=("access_token",),
    ),
    ChannelSpec(
        id="youtube",
        friendly_name="YouTube",
        aliases=("youtube", "yt channel", "yt"),
        cap="cap_youtube",
        category="youtube",
        kind="youtube_api",
        missing_labels=("youtube_api_key",),
        paste_hint="Paste: youtube api key is AIza…",
        node_type="http",
        title_templates=("YouTube digest",),
        secret_field_keys=("api_key", "refresh_token"),
    ),
    ChannelSpec(
        id="jira",
        friendly_name="Jira",
        aliases=("jira",),
        cap="cap_jira",
        category="jira",
        kind="jira_cloud",
        missing_labels=("jira_api_token",),
        paste_hint="Paste: jira token is … (and jira email / site URL if needed)",
        node_type="jira",
        title_templates=("Jira triage",),
        secret_field_keys=("api_key",),
    ),
    ChannelSpec(
        id="github",
        friendly_name="GitHub",
        aliases=("github",),
        cap="cap_github",
        category="github",
        kind="github_pat",
        missing_labels=("github_token",),
        paste_hint="Paste: github token is ghp_…",
        node_type="github",
        title_templates=("GitHub triage",),
        secret_field_keys=("token",),
    ),
    ChannelSpec(
        id="linear",
        friendly_name="Linear",
        aliases=("linear",),
        cap="cap_linear",
        category="linear",
        kind="linear_api",
        missing_labels=("linear_api_key",),
        paste_hint="Paste: linear key is lin_api_…",
        node_type="linear",
        title_templates=("Linear triage",),
        secret_field_keys=("api_key",),
    ),
    ChannelSpec(
        id="webhook",
        friendly_name="Webhook / HTTP",
        aliases=("webhook", "http call", "call api"),
        cap="cap_http",
        category="webhook",
        kind="generic_webhook",
        missing_labels=("webhook_url",),
        paste_hint="Paste: webhook url is https://…",
        node_type="http",
        title_templates=("Webhook automation",),
        secret_field_keys=("webhook_url",),
    ),
    ChannelSpec(
        id="custom",
        friendly_name="Custom API / SaaS",
        aliases=(
            "hubspot",
            "stripe",
            "notion",
            "salesforce",
            "airtable",
            "zendesk",
            "intercom",
            "asana",
            "trello",
            "pipedrive",
            "mailchimp",
            "sendgrid",
            "twilio",
            "custom api",
            "third party api",
        ),
        cap="cap_http",
        category="custom",
        kind="custom",
        missing_labels=("custom_api_key",),
        paste_hint="Paste: api_key: … and base_url: https://… for this integration",
        node_type="http",
        title_templates=("Custom API automation",),
        secret_field_keys=("api_key", "token"),
    ),
    ChannelSpec(
        id="llm",
        friendly_name="LLM API",
        aliases=("openai", "openrouter", "llm api", "model provider"),
        cap="cap_llm",
        category="llm",
        kind="openai",
        missing_labels=("openai_api_key",),
        paste_hint="Paste: llm api key is sk-…",
        secret_field_keys=("api_key",),
    ),
]

_BY_ID = {c.id: c for c in CHANNELS}
# Prefer first registration when multiple channels share a cap (webhook before custom)
_BY_CAP: dict[str, ChannelSpec] = {}
for _c in CHANNELS:
    _BY_CAP.setdefault(_c.cap, _c)
_BY_MISSING = {lab: c for c in CHANNELS for lab in c.missing_labels}

_CUSTOM_VERBS = re.compile(
    r"\b(automate|automation|sync|connect|integrate|pull from|post to|call|invoke)\b",
    re.I,
)
_CUSTOM_API_HINT = re.compile(r"\b(api|webhook|saas|crm|endpoint|integration)\b", re.I)

_TELEGRAM_TOKEN = re.compile(r"\b(\d{8,12}:[A-Za-z0-9_-]{30,})\b")
_SLACK_HOOK = re.compile(r"(https://hooks\.slack\.com/\S+)", re.I)
_DISCORD_HOOK = re.compile(r"(https://(?:discord(?:app)?\.com)/api/webhooks/\S+)", re.I)
_GITHUB_TOKEN = re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
_SHOPIFY_TOKEN = re.compile(r"\b(shpat_[A-Za-z0-9]{20,})\b")
_YOUTUBE_KEY = re.compile(r"\b(AIza[0-9A-Za-z\-_]{20,})\b")
_LLM_KEY = re.compile(r"\b(sk-or-v1-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,})\b")
_GMAIL_APP = re.compile(r"\b([a-z]{4}(?:\s+[a-z]{4}){3})\b", re.I)
_EMAIL = re.compile(r"\b([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})\b", re.I)


def get_channel(channel_id: str) -> ChannelSpec | None:
    return _BY_ID.get(channel_id)


def get_channel_by_cap(cap: str) -> ChannelSpec | None:
    return _BY_CAP.get(cap)


def detect_channels(goal: str) -> list[ChannelSpec]:
    t = (goal or "").lower()
    found: list[ChannelSpec] = []
    for ch in CHANNELS:
        if ch.id == "custom":
            continue  # handled after named channels
        if any(a in t for a in ch.aliases):
            found.append(ch)
    # Bot without telegram still often means telegram in this product
    if not any(c.id == "telegram" for c in found) and re.search(r"\bbot\b", t) and "robot" not in t:
        if "whatsapp" not in t and "slack" not in t and "discord" not in t:
            found.append(_BY_ID["telegram"])
    # Named custom SaaS aliases
    custom = _BY_ID.get("custom")
    if custom and any(a in t for a in custom.aliases):
        found.append(custom)
    # Unknown product + automate/sync/API → custom catch-all
    elif custom and not found and _CUSTOM_VERBS.search(t) and _CUSTOM_API_HINT.search(t):
        found.append(custom)
    elif custom and not found and re.search(
        r"\b(hubspot|stripe|notion|salesforce|airtable|zendesk|intercom|asana|trello|"
        r"pipedrive|mailchimp|sendgrid|twilio|crm)\b",
        t,
    ):
        found.append(custom)
    return found


def caps_from_goal(goal: str) -> list[str]:
    return list(dict.fromkeys(c.cap for c in detect_channels(goal)))


def friendly_title_for_goal(goal: str) -> str:
    channels = detect_channels(goal)
    t = (goal or "").lower()
    email = _EMAIL.search(goal or "")
    schedule = bool(re.search(r"\b(daily|every day|weekly|schedule)\b", t))
    if re.search(r"\byoutube\b|\byt\s+channel\b", t):
        yt = next((c for c in channels if c.id == "youtube"), None)
        if yt and yt.title_templates:
            return yt.title_templates[0]
        return "YouTube channel workflow"
    if channels:
        priority = ("youtube", "telegram", "shopify", "google", "github", "slack", "discord", "email", "outlook")
        primary = None
        for pid in priority:
            primary = next((c for c in channels if c.id == pid), None)
            if primary:
                break
        primary = primary or channels[0]
        if primary.id == "email" and email:
            return f"{'Daily email' if schedule else 'Email'} to {email.group(1)}"
        if primary.id == "custom":
            for brand in (
                "hubspot",
                "stripe",
                "notion",
                "salesforce",
                "airtable",
                "zendesk",
                "intercom",
                "asana",
                "trello",
                "pipedrive",
                "mailchimp",
                "sendgrid",
                "twilio",
            ):
                if brand in t:
                    return f"{brand.title()} automation"
            return "Custom API automation"
        if primary.title_templates:
            return primary.title_templates[0]
        return f"{primary.friendly_name} automation"
    if schedule:
        return "Scheduled automation"
    return "Your automation plan"


def friendly_missing_name(label: str) -> str:
    ch = _BY_MISSING.get(label)
    if ch:
        return {
            "smtp_password": "email password (SMTP app password)",
            "telegram_bot_token": "Telegram bot token",
            "slack_webhook_url": "Slack webhook URL",
            "discord_webhook_url": "Discord webhook URL",
            "jira_api_token": "Jira API token",
            "github_token": "GitHub token",
            "linear_api_key": "Linear API key",
            "webhook_url": "webhook URL",
            "openai_api_key": "LLM API key",
            "whatsapp_access_token": "WhatsApp access token",
            "whatsapp_phone_number_id": "WhatsApp phone number ID",
            "youtube_api_key": "YouTube API key",
            "shopify_shop": "Shopify shop domain",
            "shopify_access_token": "Shopify Admin API token",
            "google_client_id": "Google OAuth client ID",
            "google_client_secret": "Google OAuth client secret",
            "google_refresh_token": "Google OAuth refresh token",
            "outlook_client_id": "Outlook / Microsoft client ID",
            "outlook_client_secret": "Outlook / Microsoft client secret",
            "outlook_refresh_token": "Outlook refresh token",
            "custom_api_key": "API key for this integration",
        }.get(label, label.replace("_", " "))
    return (label or "").replace("_", " ")


def paste_hints_for_missing(missing: list[str]) -> list[str]:
    hints: list[str] = []
    seen: set[str] = set()
    for lab in missing or []:
        ch = _BY_MISSING.get(lab)
        if ch and ch.paste_hint not in seen:
            hints.append(ch.paste_hint)
            seen.add(ch.paste_hint)
    return hints[:4]


def looks_like_channel_secret(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if _TELEGRAM_TOKEN.search(t) or _SLACK_HOOK.search(t) or _DISCORD_HOOK.search(t):
        return True
    if _GITHUB_TOKEN.search(t) or _SHOPIFY_TOKEN.search(t) or _YOUTUBE_KEY.search(t) or _LLM_KEY.search(t):
        return True
    if _GMAIL_APP.search(t) and re.search(r"\b(pass|password|smtp|gmail|email|app\s*password)\b", t, re.I):
        return True
    if re.search(
        r"\b(telegram token|slack webhook|discord webhook|jira token|github token|"
        r"whatsapp token|youtube api key|shopify (?:shop|token|access)|"
        r"(?:google|outlook|microsoft|azure)\s+client[_ ]?(?:id|secret)|"
        r"(?:google|outlook|microsoft)\s+refresh[_ ]?token|"
        r"client_secret\s*[:=]|refresh_token\s*[:=]|"
        r"linear key|base_url\s*[:=]|shpat_)\b",
        t,
        re.I,
    ):
        return True
    return False


def _slot(
    bucket: dict[tuple[str, str, str], dict[str, Any]],
    *,
    category: str,
    kind: str,
    label: str = "default",
) -> dict[str, Any]:
    return bucket.setdefault(
        (category, kind, label),
        {"category": category, "kind": kind, "label": label, "fields": {}},
    )


def extract_channel_credentials(text: str) -> list[dict[str, Any]]:
    """Parse NL / labeled secrets for any registered channel into vault upsert items."""
    t = (text or "").strip()
    if not t:
        return []
    bucket: dict[tuple[str, str, str], dict[str, Any]] = {}
    raw_secrets: list[str] = []

    def add_secret(val: str) -> None:
        if val and val not in raw_secrets:
            raw_secrets.append(val)

    # --- Email / Gmail ---
    em = re.search(r"(?:(?:my|the)\s+)?(?:email|gmail)\s+is\s+(" + _EMAIL.pattern + r")", t, re.I)
    if not em:
        em = re.search(r"(?:email|gmail)\s*[:=]\s*(" + _EMAIL.pattern + r")", t, re.I)
    if em:
        email = em.group(1)
        slot = _slot(bucket, category="email", kind="gmail_smtp")
        slot["fields"]["smtp_user"] = email
        slot["fields"]["smtp_from"] = email
        if "gmail" in email.lower():
            slot["fields"].setdefault("smtp_host", "smtp.gmail.com")
            slot["fields"].setdefault("smtp_port", "587")

    pm = re.search(
        r"(?:(?:its|the|my)\s+)?(?:pass(?:word)?|app\s*password|smtp_password)\s*(?:is\s+)?[:\-]?\s*"
        r"([a-z]{4}(?:\s+[a-z]{4}){3}|[^\s,]{8,64})",
        t,
        re.I,
    )
    if pm:
        raw = pm.group(1).strip()
        add_secret(raw)
        val = re.sub(r"\s+", "", raw) if _GMAIL_APP.search(raw) else raw
        _slot(bucket, category="email", kind="gmail_smtp")["fields"]["smtp_password"] = val
    elif re.fullmatch(r"\s*([a-z]{4}(?:\s+[a-z]{4}){3})\s*", t, re.I):
        raw = re.fullmatch(r"\s*([a-z]{4}(?:\s+[a-z]{4}){3})\s*", t, re.I).group(1)
        add_secret(raw)
        _slot(bucket, category="email", kind="gmail_smtp")["fields"]["smtp_password"] = re.sub(r"\s+", "", raw)

    # --- Telegram ---
    tm = re.search(r"(?:telegram(?:\s+bot)?\s*token|bot_token)\s*(?:is\s+)?[:\-]?\s*([^\s]+)", t, re.I)
    tok = tm.group(1).strip() if tm else None
    if not tok:
        m = _TELEGRAM_TOKEN.search(t)
        tok = m.group(1) if m else None
    if tok:
        add_secret(tok)
        _slot(bucket, category="telegram", kind="telegram_bot")["fields"]["bot_token"] = tok

    # --- Slack ---
    sm = re.search(r"(?:slack\s+webhook(?:\s+url)?)\s*(?:is\s+)?[:\-]?\s*(https?://\S+)", t, re.I)
    hook = sm.group(1).strip() if sm else None
    if not hook:
        m = _SLACK_HOOK.search(t)
        hook = m.group(1).rstrip(").,") if m else None
    if hook:
        add_secret(hook)
        _slot(bucket, category="slack", kind="slack_webhook")["fields"]["webhook_url"] = hook
    sb = re.search(r"(?:slack\s+bot\s*token|xoxb-)\s*(?:is\s+)?[:\-]?\s*(xox[baprs]-[^\s]+)", t, re.I)
    if sb:
        add_secret(sb.group(1))
        _slot(bucket, category="slack", kind="slack_bot")["fields"]["bot_token"] = sb.group(1)

    # --- Discord ---
    dm = re.search(r"(?:discord\s+webhook(?:\s+url)?)\s*(?:is\s+)?[:\-]?\s*(https?://\S+)", t, re.I)
    dhook = dm.group(1).strip() if dm else None
    if not dhook:
        m = _DISCORD_HOOK.search(t)
        dhook = m.group(1).rstrip(").,") if m else None
    if dhook:
        add_secret(dhook)
        _slot(bucket, category="discord", kind="discord_webhook")["fields"]["webhook_url"] = dhook

    # --- GitHub ---
    gm = re.search(r"(?:github(?:\s+(?:pat|token))?)\s*(?:is\s+)?[:\-]?\s*([^\s]+)", t, re.I)
    gtok = None
    if gm and re.match(r"gh[pousr]_|github_pat_", gm.group(1)):
        gtok = gm.group(1)
    if not gtok:
        m = _GITHUB_TOKEN.search(t)
        gtok = m.group(1) if m else None
    if gtok:
        add_secret(gtok)
        _slot(bucket, category="github", kind="github_pat")["fields"]["token"] = gtok

    # --- Jira ---
    jm = re.search(r"(?:jira(?:\s+api)?\s*token|jira_api_token)\s*(?:is\s+)?[:\-]?\s*([^\s]+)", t, re.I)
    if jm:
        add_secret(jm.group(1))
        slot = _slot(bucket, category="jira", kind="jira_cloud")
        slot["fields"]["api_key"] = jm.group(1)
    jurl = re.search(r"(?:jira\s+(?:site|url|base_url))\s*(?:is\s+)?[:\-]?\s*(https?://\S+)", t, re.I)
    if jurl:
        _slot(bucket, category="jira", kind="jira_cloud")["fields"]["base_url"] = jurl.group(1).rstrip(").,")
    jem = re.search(r"(?:jira\s+email)\s*(?:is\s+)?[:\-]?\s*(" + _EMAIL.pattern + r")", t, re.I)
    if jem:
        _slot(bucket, category="jira", kind="jira_cloud")["fields"]["email"] = jem.group(1)

    # --- Linear ---
    lm = re.search(r"(?:linear(?:\s+api)?\s*key|linear_api_key)\s*(?:is\s+)?[:\-]?\s*([^\s]+)", t, re.I)
    if lm:
        add_secret(lm.group(1))
        _slot(bucket, category="linear", kind="linear_api")["fields"]["api_key"] = lm.group(1)

    # --- WhatsApp ---
    wm = re.search(r"(?:whatsapp(?:\s+access)?\s*token)\s*(?:is\s+)?[:\-]?\s*([^\s]+)", t, re.I)
    if wm:
        add_secret(wm.group(1))
        _slot(bucket, category="whatsapp", kind="whatsapp_cloud")["fields"]["access_token"] = wm.group(1)
    wp = re.search(r"(?:whatsapp\s+)?phone(?:\s+number)?\s*id\s*(?:is\s+)?[:\-]?\s*([0-9]{6,})", t, re.I)
    if wp:
        _slot(bucket, category="whatsapp", kind="whatsapp_cloud")["fields"]["phone_number_id"] = wp.group(1)

    # --- YouTube ---
    ym = re.search(r"(?:youtube(?:\s+api)?\s*key)\s*(?:is\s+)?[:\-]?\s*([^\s]+)", t, re.I)
    ykey = ym.group(1) if ym else None
    if not ykey:
        m = _YOUTUBE_KEY.search(t)
        ykey = m.group(1) if m else None
    if ykey:
        add_secret(ykey)
        _slot(bucket, category="youtube", kind="youtube_api")["fields"]["api_key"] = ykey

    # --- Shopify ---
    shop = re.search(
        r"(?:shopify\s+shop(?:\s+domain)?|\bshop\s+domain)\s*(?:is\s+)?[:\-]?\s*"
        r"([a-z0-9\-]+(?:\.myshopify\.com)?)",
        t,
        re.I,
    )
    if not shop:
        shop = re.search(
            r"\bshop\s*(?:is\s+)?[:\-]?\s*([a-z0-9\-]+\.myshopify\.com)\b",
            t,
            re.I,
        )
    if shop:
        domain = shop.group(1)
        if ".myshopify.com" not in domain.lower():
            domain = f"{domain}.myshopify.com"
        _slot(bucket, category="shopify", kind="shopify_admin")["fields"]["shop"] = domain
    stok = None
    m = _SHOPIFY_TOKEN.search(t)
    if m:
        stok = m.group(1)
    if not stok:
        st = re.search(
            r"(?:shopify(?:\s+access)?\s*token)\s*(?:is\s+)?[:\-]?\s*(shpat_[A-Za-z0-9]+|[^\s]+)",
            t,
            re.I,
        )
        if st:
            stok = st.group(1)
    if stok:
        add_secret(stok)
        _slot(bucket, category="shopify", kind="shopify_admin")["fields"]["access_token"] = stok

    # --- Google OAuth / API ---
    for key, field in (
        (r"google\s+client[_ ]?id", "client_id"),
        (r"google\s+client[_ ]?secret", "client_secret"),
        (r"google\s+refresh[_ ]?token", "refresh_token"),
        (r"google\s+access[_ ]?token", "access_token"),
        (r"google\s+api[_ ]?key", "api_key"),
    ):
        m = re.search(rf"(?:{key})\s*(?:is\s+)?[:\-]?\s*([^\s]+)", t, re.I)
        if m:
            val = m.group(1).strip()
            if field in ("client_secret", "refresh_token", "access_token", "api_key"):
                add_secret(val)
            _slot(bucket, category="google", kind="google_oauth")["fields"][field] = val

    # --- Outlook / Microsoft ---
    for key, field in (
        (r"(?:outlook|microsoft|azure)\s+client[_ ]?id", "client_id"),
        (r"(?:outlook|microsoft|azure)\s+client[_ ]?secret", "client_secret"),
        (r"(?:outlook|microsoft)\s+refresh[_ ]?token", "refresh_token"),
        (r"(?:outlook|microsoft)\s+tenant[_ ]?id", "tenant_id"),
    ):
        m = re.search(rf"(?:{key})\s*(?:is\s+)?[:\-]?\s*([^\s]+)", t, re.I)
        if m:
            val = m.group(1).strip()
            if field in ("client_secret", "refresh_token"):
                add_secret(val)
            _slot(bucket, category="outlook", kind="microsoft_graph")["fields"][field] = val

    # --- Webhook ---
    wh = re.search(r"(?:webhook(?:\s+url)?)\s*(?:is\s+)?[:\-]?\s*(https?://\S+)", t, re.I)
    if wh and "slack.com" not in wh.group(1) and "discord" not in wh.group(1).lower():
        add_secret(wh.group(1))
        _slot(bucket, category="webhook", kind="generic_webhook")["fields"]["webhook_url"] = wh.group(1).rstrip(").,")

    # --- Custom SaaS / generic API ---
    bu = re.search(r"(?:base[_ ]?url)\s*(?:is\s+)?[:\-]?\s*(https?://\S+)", t, re.I)
    if bu:
        _slot(bucket, category="custom", kind="custom")["fields"]["base_url"] = bu.group(1).rstrip(").,")
    # Generic api_key / access token when talking about custom integrations (not sk- LLM)
    cam = re.search(
        r"(?:(?:custom|hubspot|stripe|notion|salesforce|zendesk)\s+)?(?:api[_ ]?key|access[_ ]?token)\s*"
        r"(?:is\s+)?[:\-]?\s*([A-Za-z0-9_\-]{12,})",
        t,
        re.I,
    )
    if cam:
        val = cam.group(1).strip()
        if not val.startswith("sk-") and not val.startswith("shpat_") and not val.startswith("AIza"):
            add_secret(val)
            _slot(bucket, category="custom", kind="custom")["fields"]["api_key"] = val

    # --- LLM ---
    km = re.search(
        r"(?:(?:llm|openai|openrouter)\s+api[_ ]?key|api[_ ]?key)\s*(?:is\s+)?[:\-]?\s*([^\s]+)",
        t,
        re.I,
    )
    kval = km.group(1) if km and km.group(1).startswith("sk-") else None
    if not kval:
        m = _LLM_KEY.search(t)
        kval = m.group(1) if m else None
    if kval:
        add_secret(kval)
        slot = _slot(bucket, category="llm", kind="openai")
        slot["fields"]["api_key"] = kval
        if kval.startswith("sk-or-"):
            slot["fields"].setdefault("base_url", "https://openrouter.ai/api/v1")

    out: list[dict[str, Any]] = []
    for item in bucket.values():
        if not item.get("fields"):
            continue
        item["raw_secrets"] = list(
            dict.fromkeys(raw_secrets + [str(v) for v in item["fields"].values() if isinstance(v, str) and len(v) >= 6])
        )
        out.append(item)
    return out


def solution_blurb_for_goal(goal: str, *, missing: list[str] | None = None) -> str:
    title = friendly_title_for_goal(goal)
    channels = detect_channels(goal)
    if channels:
        head = f"I drafted a plan for **{title}** ({channels[0].friendly_name})."
    else:
        head = f"I drafted a plan for **{title}**."
    bits = [head]
    if missing:
        names = ", ".join(friendly_missing_name(m) for m in missing[:4])
        bits.append(f"To go live I need: {names}. Paste them here or open **Credentials**.")
        bits.append("Then tap **Approve** when you’re ready.")
    else:
        bits.append("Tap **Approve** when this looks right — I’ll test it next.")
    return " ".join(bits)
