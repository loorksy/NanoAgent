"""Hatch build hook that used to bundle the legacy React client.

The React client is removed. Mokli is the browser. This hook stays so
existing `MOKLI_SKIP_MOKLI_BUILD` installs and sdists keep building, and it
no-ops when `mokli/package.json` is absent.

Behavior:

- Skips for editable installs (`pip install -e .`). Editable mode is for Python
  development; mokli contributors use `cd mokli && bun run dev` (Vite HMR) and
  do not need a packaged `dist/`.
- No-op when `mokli/package.json` is absent (e.g. installing from an sdist that
  already contains a prebuilt `mokli/web/dist/`).
- Skips when `MOKLI_SKIP_MOKLI_BUILD=1` is set.
- Reuses `mokli/web/dist/` only when it is already fresh, unless
  `MOKLI_FORCE_MOKLI_BUILD=1` is set.
- Uses `bun` when available, otherwise falls back to `npm`. The chosen tool
  performs `install` followed by `run build`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _load_mokli_build_module() -> ModuleType:
    from mokli.mokli import build as mokli_build

    return mokli_build


class MokliBuildHook(BuildHookInterface):
    PLUGIN_NAME = "mokli-build"

    def initialize(self, version: str, build_data: dict) -> None:  # noqa: D401
        root = Path(self.root)
        mokli_dir = root / "mokli"
        package_json = mokli_dir / "package.json"
        dist_dir = root / "mokli" / "web" / "dist"
        index_html = dist_dir / "index.html"

        # `pip install -e .` builds an editable wheel; skip the (slow) mokli
        # bundle since editable installs target Python development and mokli
        # work uses `bun run dev` instead.
        if self.target_name == "wheel" and version == "editable":
            self.app.display_info(
                "[mokli-build] skipped for editable install "
                "(use `cd mokli && bun run build` to bundle mokli manually)"
            )
            return

        if os.environ.get("MOKLI_SKIP_MOKLI_BUILD") == "1":
            self.app.display_info("[mokli-build] skipped via MOKLI_SKIP_MOKLI_BUILD=1")
            return

        if not package_json.is_file():
            self.app.display_info(
                "[mokli-build] legacy React client removed; Mokli is the browser"
            )
            return

        mokli_build = _load_mokli_build_module()
        status = mokli_build.inspect_mokli_bundle(source_dir=mokli_dir, dist_dir=dist_dir)
        force = os.environ.get("MOKLI_FORCE_MOKLI_BUILD") == "1"
        if not status.needs_build and not force:
            self.app.display_info(
                f"[mokli-build] reusing existing build at {dist_dir} "
                "(already fresh; set MOKLI_FORCE_MOKLI_BUILD=1 to rebuild)"
            )
            return

        if status.needs_build and not force:
            self.app.display_info(
                f"[mokli-build] {mokli_build.describe_mokli_bundle_status(status)}"
            )

        try:
            mokli_build.build_mokli_bundle(
                source_dir=mokli_dir,
                dist_dir=dist_dir,
                output=self.app.display_info,
            )
        except mokli_build.MokliBuildError as exc:
            raise RuntimeError(
                "[mokli-build] "
                f"{exc}. Install `bun` or `npm`, or set MOKLI_SKIP_MOKLI_BUILD=1 to bypass."
            ) from exc

        if not index_html.is_file():
            raise RuntimeError(
                f"[mokli-build] build finished but {index_html} is missing; "
                "check mokli/vite.config.ts outDir."
            )
        self.app.display_info(f"[mokli-build] mokli ready at {dist_dir}")
