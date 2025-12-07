from pathlib import Path
from typing import List
from jinja2 import Environment, FileSystemLoader, Template
import beezle_bug.constants as const


class TemplateLoader:
    def __init__(self, data_dir: Path):
        self._template_dir = data_dir / const.TEMPLATE_SUBFOLDER
        self._env = Environment(loader=FileSystemLoader(self._template_dir))
    
    def load(self, name: str) -> Template:
        return self._env.get_template(f"{name}.j2")
    
    def list_templates(self) -> List[str]:
        """Return list of available template names (without .j2 extension)."""
        templates = self._env.list_templates()
        return [t.replace('.j2', '') for t in templates if t.endswith('.j2')]
    
    def get_content(self, name: str) -> str:
        """Read and return the raw content of a template file."""
        template_path = self._template_dir / f"{name}.j2"
        if not template_path.exists():
            raise FileNotFoundError(f"Template '{name}' not found")
        return template_path.read_text(encoding="utf-8")
    
    def save(self, name: str, content: str) -> None:
        """Create or update a template file."""
        template_path = self._template_dir / f"{name}.j2"
        template_path.write_text(content, encoding="utf-8")
        # Clear Jinja2 cache so it picks up the new content
        self._env = Environment(loader=FileSystemLoader(self._template_dir))
    
    def delete(self, name: str) -> None:
        """Delete a template file."""
        template_path = self._template_dir / f"{name}.j2"
        if not template_path.exists():
            raise FileNotFoundError(f"Template '{name}' not found")
        template_path.unlink()
