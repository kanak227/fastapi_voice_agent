import os
import shutil


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOTS_DIR = os.path.join(BASE_DIR, "tekurious-chatbot-main", "bots")
HELPER_DIR = os.path.join(BASE_DIR, "bot-helper-data", "extracted")
BASE_BOT = os.path.join(BOTS_DIR, "education-ai")


BOT_CONFIGS = [
    {
        "slug": "digital-literacy-ai",
        "label": "Digital Literacy",
        "prompt_file": "prompts__AI and Digital Literacy.txt",
        "guardrail_file": "guardrails__AI and Digital Literacy.txt",
        "fallback": "Sorry, I can only help with AI and digital literacy topics.",
    },
    {
        "slug": "design-thinking-ai",
        "label": "Design Thinking",
        "prompt_file": "prompts__design thinking.txt",
        "guardrail_file": "guardrails__design thinking.txt",
        "fallback": "Sorry, I can only help with design thinking and innovation topics.",
    },
    {
        "slug": "wellbeing-ai",
        "label": "Well-being",
        "prompt_file": "prompts__Well being.txt",
        "guardrail_file": "guardrails__Well being.txt",
        "fallback": "Sorry, I can only help with well-being and healthy habits topics.",
    },
    {
        "slug": "sustainability-ai",
        "label": "Sustainability",
        "prompt_file": "prompts__Sustainability.txt",
        "guardrail_file": "guardrails__Sustainability.txt",
        "fallback": "Sorry, I can only help with sustainability and environmental topics.",
    },
    {
        "slug": "global-citizenship-ai",
        "label": "Global Citizenship",
        "prompt_file": "prompts__Global Citizenship.txt",
        "guardrail_file": "guardrails__Global Citizenship.txt",
        "fallback": "Sorry, I can only help with global citizenship topics.",
    },
    {
        "slug": "entrepreneurship-ai",
        "label": "Entrepreneurship",
        "prompt_file": "prompts__Entrepreneurship.txt",
        "guardrail_file": "guardrails__Entrepreneurship.txt",
        "fallback": "Sorry, I can only help with entrepreneurship and startup topics.",
    },
    {
        "slug": "emotional-intelligence-ai",
        "label": "Emotional Intelligence",
        "prompt_file": "prompts__emotional intelligence.txt",
        "guardrail_file": "guardrails__emotional intelligence.txt",
        "fallback": "Sorry, I can only help with emotional intelligence topics.",
    },
    {
        "slug": "financial-literacy-ai",
        "label": "Financial Literacy",
        "prompt_file": "prompts__financial literacy_.txt",
        "guardrail_file": "guardrails__Untitled document.txt",
        "fallback": "Sorry, I can only help with financial literacy topics.",
    },
]


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read().strip()


def build_prompt_yaml(topic_label: str, reference_text: str) -> str:
    lines = reference_text.splitlines()
    indented = "\n".join(f"  {line}" for line in lines)
    return (
        "_type: prompt\n"
        "input_variables: [query, format_instructions]\n"
        "template: |2\n\n"
        f"  You are SmartE, a {topic_label} mentor.\n"
        "  Use the guidance below for age-specific tone and depth. If the user does not share an age or grade, default to the 11 to 15 year old guidance.\n"
        "\n"
        "  Guidance Reference:\n"
        f"{indented}\n"
        "\n"
        "  Output\n"
        "  {format_instructions}\n"
        "\n"
        "template_format: f-string\n"
    )


def update_server_main(path: str, label: str, fallback: str) -> None:
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    content = content.replace(
        '"service": "tekurious-ai"',
        f'"service": "{label.lower().replace(" ", "-")}"',
    )
    content = content.replace(
        "Sorry, I can't respond. I can only help with Class 9 and Class 10 CBSE topics.",
        fallback,
    )

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def main() -> None:
    for bot in BOT_CONFIGS:
        target_dir = os.path.join(BOTS_DIR, bot["slug"])
        if not os.path.exists(target_dir):
            shutil.copytree(BASE_BOT, target_dir)

        prompt_path = os.path.join(HELPER_DIR, bot["prompt_file"])
        guardrail_path = os.path.join(HELPER_DIR, bot["guardrail_file"])

        prompt_text = read_text(prompt_path)
        guardrail_text = read_text(guardrail_path)

        analyze_yaml = build_prompt_yaml(bot["label"], prompt_text)
        guardrail_yaml = build_prompt_yaml(f"{bot['label']} safety", guardrail_text)

        prompt_out = os.path.join(target_dir, "src", "prompts", "analyze_query.yaml")
        guardrail_out = os.path.join(target_dir, "src", "prompts", "input_guardrails.yaml")

        with open(prompt_out, "w", encoding="utf-8") as fh:
            fh.write(analyze_yaml)

        with open(guardrail_out, "w", encoding="utf-8") as fh:
            fh.write(guardrail_yaml)

        main_py = os.path.join(target_dir, "src", "server", "main.py")
        update_server_main(main_py, bot["label"], bot["fallback"])

        print(f"Prepared bot: {bot['slug']}")


if __name__ == "__main__":
    main()
