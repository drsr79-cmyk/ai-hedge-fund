"""Where API keys live, and how they get there.

Secrets live in ``~/.hedge-fund/.env`` (see paths.py), loaded by
``python-dotenv`` at every entry point — this module writes to that same file
rather than inventing a second store. Two rules follow from it:

1. **Safe profile drops inherited secrets.** Network profile loads only
   ``~/.hedge-fund/.env``, and only when ``AIHF_LOAD_DOTENV=1``. A key
   already in the environment is kept in that case; a working-directory
   ``.env`` is never read.
2. **Edits are surgical.** Saving a key rewrites exactly the one line that
   defines it and leaves every other line — other keys, comments, blanks —
   byte-for-byte intact. A settings screen must never eat a file it did not
   write.

Textual-free on purpose, like shared.py — the CLI can use this too.
"""

from __future__ import annotations

import os
import re
import stat

from hedge_fund.llm import PROVIDER_ENV_VARS, env_var_for  # noqa: F401  (re-export)
from hedge_fund.paths import ENV_PATH


def apply_credentials() -> None:
    """Apply the process profile's credential rules.

    Safe profile (the default) drops inherited provider secrets and does not
    read dotenv files. Network profile loads ``~/.hedge-fund/.env`` only when
    ``AIHF_LOAD_DOTENV=1``. A ``.env`` in the working directory is never read,
    including when a paper runner is started with the fund directory as cwd.
    """
    from hedge_fund.safety.profile import apply_profile_credentials

    apply_profile_credentials()


def save_credential(env_var: str, value: str) -> Path:
    """Write one key into .env, replacing its line if present and appending
    otherwise, then export it for this process. Returns the file it wrote.

    Everything else in the file survives untouched — this is a line edit, not
    a regenerate.
    """
    line = f"{env_var}={_quote(value)}"
    if ENV_PATH.exists():
        original = ENV_PATH.read_text()
        # Match an assignment at the start of a line, optionally exported and
        # optionally commented-out, so re-saving a disabled key revives it.
        pattern = re.compile(
            rf"^[ \t]*#?[ \t]*(?:export[ \t]+)?{re.escape(env_var)}[ \t]*=.*$",
            re.MULTILINE)
        updated, count = pattern.subn(lambda _: line, original, count=1)
        if count == 0:
            sep = "" if not original or original.endswith("\n") else "\n"
            updated = f"{original}{sep}{line}\n"
    else:
        updated = f"{line}\n"

    ENV_PATH.write_text(updated)
    ENV_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600 — secrets are not world-readable
    os.environ[env_var] = value
    return ENV_PATH


def missing_key(provider: str) -> str | None:
    """The env var this provider needs, if it is not set — otherwise None.
    Named as a question so it reads at the call site: `if missing_key(p):`."""
    name = env_var_for(provider)
    if name is None or os.environ.get(name):
        return None
    return name


def masked(value: str) -> str:
    """A key as it should appear on screen: enough to recognise, not enough
    to use. Short strings are hidden outright rather than half-revealed."""
    if len(value) <= 12:
        return "•" * len(value)
    return f"{value[:6]}{'•' * 8}{value[-4:]}"


def _quote(value: str) -> str:
    """Quote only when the value would not survive unquoted. Most API keys are
    bare tokens, and quoting those would look wrong next to hand-written lines.
    """
    if value and not re.search(r"[\s#'\"\\]", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
