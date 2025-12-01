from pathlib import Path
from typing import List
from jinja2 import Environment, FileSystemLoader, Template
import beezle_bug.constants as const


class TemplateLoader:
    def __init__(self, data_dir: Path):
        template_dir = data_dir / const.TEMPLATE_SUBFOLDER
        self._env = Environment(loader=FileSystemLoader(template_dir))
    
    def load(self, name: str) -> Template:
        return self._env.get_template(f"{name}.j2")
    
    def list_templates(self) -> List[str]:
        """Return list of available template names (without .j2 extension)."""
        templates = self._env.list_templates()
        return [t.replace('.j2', '') for t in templates if t.endswith('.j2')]
