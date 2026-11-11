"""Topic tags for a monitored Telegram chat.

The live download used to stamp every new chat with the same three tags.
Tags are chosen from the chat title so stance and the Sources view can
tell a jobs channel from a conflict channel. Unrecognised titles stay on
a neutral current-affairs tag.
"""

from __future__ import annotations

import re
import unicodedata

# Checked in order. A title may collect more than one group, up to four tags.
_RULES: list[tuple[re.Pattern[str], list[str]]] = [
    (re.compile(r"politic|election|governance|panchayat|municipal|parliament|assembly|minister", re.I), ["politics", "governance"]),
    (re.compile(r"develop|infrastructure|civic|welfare|scheme", re.I), ["development", "governance"]),
    (re.compile(r"\blocal\b|district|constituency|\bnews\b", re.I), ["politics", "development"]),
    (re.compile(r"job|naukri|sarkari|career", re.I), ["employment", "india"]),
    (re.compile(r"e[\s-]?book|library|novel", re.I), ["education", "books"]),
    (re.compile(r"cyber|hack", re.I), ["cybersecurity", "osint"]),
    (re.compile(r"space|isro|satellite|gaganyaan", re.I), ["space", "technology"]),
    (re.compile(r"geo-?politic|\bgeo\b|diplom|strategic|foreign policy", re.I), ["geopolitics", "strategy"]),
    (re.compile(r"\bwar\b|conflict|military|\barmy\b|defence|defense|\bnavy\b|air force|weapon|insurgenc|ghatak|\brifles?\b|\bforces\b", re.I), ["conflict", "defense"]),
    (re.compile(r"osint|\bintel\b|\bint\b|sentinel|\bsignal\b|predator|specops|info[\s-]?ops", re.I), ["osint", "intelligence"]),
    (re.compile(r"middle\s*east|south\s*bloc|north\s*east|\bkashmir\b|\bjammu\b", re.I), ["geopolitics", "strategy"]),
    (re.compile(r"market|finance|stock|crypto", re.I), ["economy"]),
    (re.compile(r"tech|semiconductor|quantum|ai\b", re.I), ["technology"]),
]

_GENERIC = ["osint", "defense", "geopolitics"]
_FALLBACK = ["current_affairs"]
_BLOCK = re.compile(
    r"e[\s-]?book|\bjobs?\b|naukri|sarkari|career|movie|film|\bsongs?\b|"
    r"music|cricket|joke|meme|gaming|\bshop\b|cracked|software|warez|"
    r"\bmod\b|toon|\bsport|academy|tuition|tution|\bpdf\b|\bgore\b",
    re.I,
)
# Named first when a Middle East download is requested. Substrings, after Unicode folding.
_ME_PRIORITY = (
    "mediterranean man",
    "middle east spectator",
    "middleeast gc",
)
_ME_TITLE = re.compile(
    r"mediterr|middle\s*east|middleeast|\blevant\b|\bgaza\b|\bisrael\b|\biran\b|"
    r"\blebanon\b|\bsyria\b|\byemen\b|\biraq\b|palestin|\bgulf\b|"
    r"hamas|hezbollah|houthi|\bjordan\b|\begypt\b|\bsaudi\b|\bqatar\b|"
    r"\bemirates\b|\buae\b|jerusalem|tehran|\bbeirut\b|damascus|\bwest bank\b",
    re.I,
)
_NOT_MIDDLE_EAST = re.compile(r"north\s*east", re.I)

_RELATED_TAGS = {
    "geopolitics",
    "strategy",
    "conflict",
    "defense",
    "osint",
    "intelligence",
    "space",
    "cybersecurity",
    "politics",
    "governance",
    "development",
}


def _fold(name: str) -> str:
    """Turn styled Unicode letters into plain text so '𝐈𝐍𝐓𝐄𝐋' matches intel."""
    chars: list[str] = []
    for char in name or "":
        label = unicodedata.name(char, "")
        piece = label.split()[-1] if label else ""
        if len(piece) == 1 and piece.isalpha() and ("LETTER" in label or "CAPITAL" in label or "SMALL" in label):
            chars.append(piece.lower())
        else:
            chars.append(char.lower())
    return "".join(chars)


def topic_tags_for(name: str) -> list[str]:
    """Return up to four topic tags inferred from a chat title."""
    title = _fold(name)
    tags: list[str] = []
    for pattern, group in _RULES:
        if pattern.search(title):
            for tag in group:
                if tag not in tags:
                    tags.append(tag)
        if len(tags) >= 4:
            break
    return tags[:4] or list(_FALLBACK)


def is_generic_topic_list(tags: list[str] | None) -> bool:
    """True when a chat still has the old identical three-tag default."""
    return list(tags or []) == _GENERIC


# Explicitly requested from the numbered chat list, even when the topic filter skips them.
_FORCE_INCLUDE_RAW = (
    "Clown(🤡) vibes",
    "Telegram",
    "MiddleEast GC",
    "Middle East Spectator — MES",
    "Mediterranean Man",
    "𝐓𝐡𝐞 𝐍𝐢𝐠𝐡𝐭 𝐇𝐮𝐧𝐭𝐞𝐫𝐬",
    "Sports Zone",
    "Sumit Raj",
    "PORK - ARCHIVE 🇵🇰",
    "VidurNeeti 🇮🇳",
    "Russians With Attitude",
    "Rootsec",
)


def is_middle_east(name: str) -> bool:
    """True when the chat title is about the Middle East, not India's North East."""
    title = _fold(name)
    if _NOT_MIDDLE_EAST.search(title):
        return False
    if any(key in title for key in _ME_PRIORITY):
        return True
    return _ME_TITLE.search(title) is not None


def middle_east_rank(name: str) -> int:
    """Lower numbers are downloaded first. Named channels beat a keyword match."""
    title = _fold(name)
    for index, key in enumerate(_ME_PRIORITY):
        if key in title:
            return index
    return len(_ME_PRIORITY)


def is_project_related(name: str) -> bool:
    """True for the project topics, plus the numbered chats the user asked to include.

    Jobs, e-books, and entertainment titles are rejected even if another word matches,
    unless that exact chat is in the requested include list.
    """
    title = _fold(name)
    if title in {_fold(item) for item in _FORCE_INCLUDE_RAW}:
        return True
    if _BLOCK.search(title):
        return False
    return any(tag in _RELATED_TAGS for tag in topic_tags_for(title))
