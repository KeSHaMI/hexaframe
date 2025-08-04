from __future__ import annotations

from typing import Any, Dict

from jinja2 import Environment, PackageLoader, select_autoescape

# Create a single Jinja2 environment that loads templates from package resources
_env = Environment(
    loader=PackageLoader("hexaframe_cli", "templates"),
    autoescape=select_autoescape(enabled_extensions=("j2",)),
    keep_trailing_newline=True,
)


def render_text(template_path: str, context: Dict[str, Any]) -> str:
    """
    Render a template from package resources at 'templates/{template_path}'.
    Example: render_text("project/README.md.j2", {"project_name": "myapp"})
    """
    template = _env.get_template(template_path)
    return template.render(**(context or {}))
