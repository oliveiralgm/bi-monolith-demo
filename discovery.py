"""Auto-discover dashboard modules and mount each as a Dash app on Flask."""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

import dash
import dashboards


@dataclass(frozen=True)
class DashboardSpec:
    slug: str
    title: str
    summary: str
    source_topic: str
    order: int
    layout: Callable[[], Any]
    register_callbacks: Optional[Callable[[Any], None]] = None


REQUIRED_KEYS = ("slug", "title", "summary", "layout")


def discover_dashboards() -> List[DashboardSpec]:
    """Scan the dashboards package for modules that expose a DASHBOARD dict."""
    found: List[DashboardSpec] = []

    for module_info in pkgutil.iter_modules(dashboards.__path__, dashboards.__name__ + "."):
        short = module_info.name.rsplit(".", 1)[-1]
        if short.startswith("_"):
            continue

        module = importlib.import_module(module_info.name)
        meta = getattr(module, "DASHBOARD", None)
        if not isinstance(meta, dict):
            continue

        missing = [k for k in REQUIRED_KEYS if k not in meta]
        if missing:
            raise RuntimeError(f"{module_info.name} DASHBOARD missing keys: {missing}")

        found.append(
            DashboardSpec(
                slug=str(meta["slug"]),
                title=str(meta["title"]),
                summary=str(meta["summary"]),
                source_topic=str(meta.get("source_topic", "portfolio")),
                order=int(meta.get("order", 100)),
                layout=meta["layout"],
                register_callbacks=meta.get("register_callbacks"),
            )
        )

    found.sort(key=lambda d: (d.order, d.title.lower()))
    slugs = [d.slug for d in found]
    if len(slugs) != len(set(slugs)):
        raise RuntimeError(f"Duplicate dashboard slugs: {slugs}")
    return found


def mount_dashboards(flask_server: Any, specs: List[DashboardSpec]) -> List[dash.Dash]:
    """
    Mount one Dash application per discovered module.

    Pattern: drop a module in dashboards/, expose DASHBOARD metadata, restart.
    The monolith picks it up and serves it at /d/<slug>/.
    """
    apps: List[dash.Dash] = []
    for spec in specs:
        dash_app = dash.Dash(
            name=f"bi_demo_{spec.slug}",
            server=flask_server,
            url_base_pathname=f"/d/{spec.slug}/",
            suppress_callback_exceptions=True,
            title=spec.title,
            update_title=None,
            assets_folder="assets",
        )
        dash_app.layout = spec.layout
        if spec.register_callbacks:
            spec.register_callbacks(dash_app)
        apps.append(dash_app)
    return apps
