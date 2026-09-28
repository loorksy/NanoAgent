"""Locate the TradingView charting library shipped with the repo."""

from __future__ import annotations

import os

_SCRIPT = 'charting_library.standalone.js'


def charting_library_dir(anchor: str | None = None) -> str | None:
    """Directory that contains ``charting_library.standalone.js``, if it is present.

    ``anchor`` is this module's file when omitted. The UI package lives under
    ``mokli-ui/backend``, and the library lives at the repo's
    ``mokli-assets/public/charting_library``.
    """
    configured = os.environ.get('MOKLI_CHARTING_LIBRARY', '').strip()
    candidates = [configured] if configured else []
    here = os.path.dirname(anchor or os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, '..', '..', '..'))
    ui_root = os.path.abspath(os.path.join(here, '..', '..'))
    candidates.extend(
        [
            os.path.join(repo_root, 'mokli-assets', 'public', 'charting_library'),
            os.path.join(repo_root, 'mokli', 'public', 'charting_library'),
            os.path.join(ui_root, 'mokli', 'public', 'charting_library'),
            os.path.join(ui_root, 'mokli', 'web', 'dist', 'charting_library'),
        ]
    )
    for path in candidates:
        script = os.path.join(path, _SCRIPT)
        if path and os.path.isdir(path) and os.path.isfile(script):
            return path
    return None
