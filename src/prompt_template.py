from jinja2 import Environment, FileSystemLoader, Template

TEMPLATES_FOLDER = "/home/ruben/Code/beezle-bug/src/prompt_templates"

CHATML = "chatml"


def load(format: str) -> Template:
    env = Environment(loader=FileSystemLoader(TEMPLATES_FOLDER))
    return env.get_template(f"{format}.j2")