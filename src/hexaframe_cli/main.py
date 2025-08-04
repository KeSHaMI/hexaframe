# Thin shim that imports the refactored CLI app.
from __future__ import annotations

from hexaframe_cli.cli import app, main  # re-export for backwards compatibility
from hexaframe_cli.commands.new import (
    new_cmd as new,  # maintain backward-compatible symbol
)

__all__ = ["main", "app", "new"]

if __name__ == "__main__":
    main()
