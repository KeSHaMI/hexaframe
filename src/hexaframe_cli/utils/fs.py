from __future__ import annotations

from pathlib import Path


def write_file(
    path: Path, content: str, *, exist_ok: bool = True, overwrite: bool = False
) -> None:
    """
    Write a text file, creating parent dirs.
    If exist_ok is False and file exists, raise.
    If exist_ok is True and overwrite is False, keep existing file intact.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite and not exist_ok:
        raise FileExistsError(str(path))
    if path.exists() and not overwrite and exist_ok:
        # Keep existing content
        return
    path.write_text(content, encoding="utf-8")
