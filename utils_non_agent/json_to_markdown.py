import json

# === Configuration ===
INPUT_FILE = "produkte_deutsch.json"
OUTPUT_FILE = "products.md"

def to_markdown(product):
    lines = []

    # Use 'title' as H1 separator
    title = product.get("Titel", "Unnamed Product")
    lines.append(f"# {title}\n")

    # Go through each field except title
    for key, value in product.items():
        if key == "Titel":
            continue

        # Format lists and dicts nicely
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)

        lines.append(f"**{key.replace('_', ' ').capitalize()}:** {value}\n")

    return "\n".join(lines)

def generate_markdown():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    md_sections = [to_markdown(product) for product in products]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(md_sections))

    print(f"{len(md_sections)} Markdown entries saved to '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    generate_markdown()
