from jinja2 import Environment, FileSystemLoader, Template

TEMPLATES_FOLDER = "beezle_bug/prompt_templates"

CHATML = "chatml"


def load(format: str) -> Template:
    env = Environment(loader=FileSystemLoader(TEMPLATES_FOLDER))
    return env.get_template(f"{format}.j2")
