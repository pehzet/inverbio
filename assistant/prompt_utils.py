from pathlib import Path
import os
def get_template_path() -> Path:
    # config folder later
    return Path(__file__).parent / "prompts" 

def get_prompt_template(name: str) -> str:
    template_path = get_template_path() / f"{name}.md"
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")
    with open(template_path, "r") as f:
        return f.read()

def get_prompt_template_with_placeholders(name: str, **kwargs) -> str:
    template = get_prompt_template(name)
    return template.format(**kwargs)