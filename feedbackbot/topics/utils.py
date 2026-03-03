import re

TOPIC_NAME_MAX_LENGTH = 128
CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def sanitize_topic_name(full_name: str | None, username: str | None) -> str:
    name_part = (full_name or '').strip()
    username_part = f'{username}' if username else ''
    raw = f'{name_part} ({username_part})'.strip() if username_part else name_part
    raw = raw or 'Без имени'
    cleaned = CONTROL_CHARS_RE.sub('', raw)
    normalized = re.sub(r'\s+', ' ', cleaned).strip()
    return (normalized[:TOPIC_NAME_MAX_LENGTH]).strip() or 'Без имени'
