import os
import shutil


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UI_DIR = os.path.join(BASE_DIR, "tekurious-chatbot-main", "tekurious-chatbot-ui")

PAGE_BASE = os.path.join(UI_DIR, "app", "dashboard", "ReligiousAI", "page.js")
API_BASE = os.path.join(UI_DIR, "app", "api", "ReligiousAI", "route.js")

BOTS = [
    {
        "id": "DigitalLiteracy",
        "label": "Digital Literacy",
        "domain": "digital-literacy",
        "welcome": "Hello! I'm SmartE for Digital Literacy. Ask me about AI, online safety, and smart internet habits.",
        "fallback": "I can only help with AI and digital literacy topics. Please ask something related.",
        "fallback_const": "DIGITAL_LITERACY_FALLBACK",
    },
    {
        "id": "DesignThinking",
        "label": "Design Thinking",
        "domain": "design-thinking",
        "welcome": "Hello! I'm SmartE for Design Thinking. Ask me about empathy, ideation, and prototyping.",
        "fallback": "I can only help with design thinking and innovation topics. Please ask something related.",
        "fallback_const": "DESIGN_THINKING_FALLBACK",
    },
    {
        "id": "Wellbeing",
        "label": "Well-being",
        "domain": "wellbeing",
        "welcome": "Hello! I'm SmartE for Well-being. Ask me about emotions, habits, and healthy routines.",
        "fallback": "I can only help with well-being topics. Please ask something related.",
        "fallback_const": "WELLBEING_FALLBACK",
    },
    {
        "id": "Sustainability",
        "label": "Sustainability",
        "domain": "sustainability",
        "welcome": "Hello! I'm SmartE for Sustainability. Ask me about climate, recycling, and green habits.",
        "fallback": "I can only help with sustainability topics. Please ask something related.",
        "fallback_const": "SUSTAINABILITY_FALLBACK",
    },
    {
        "id": "GlobalCitizenship",
        "label": "Global Citizenship",
        "domain": "global-citizenship",
        "welcome": "Hello! I'm SmartE for Global Citizenship. Ask me about cultures, SDGs, and human rights.",
        "fallback": "I can only help with global citizenship topics. Please ask something related.",
        "fallback_const": "GLOBAL_CITIZENSHIP_FALLBACK",
    },
    {
        "id": "Entrepreneurship",
        "label": "Entrepreneurship",
        "domain": "entrepreneurship",
        "welcome": "Hello! I'm SmartE for Entrepreneurship. Ask me about ideas, startups, and business basics.",
        "fallback": "I can only help with entrepreneurship topics. Please ask something related.",
        "fallback_const": "ENTREPRENEURSHIP_FALLBACK",
    },
    {
        "id": "EmotionalIntelligence",
        "label": "Emotional Intelligence",
        "domain": "emotional-intelligence",
        "welcome": "Hello! I'm SmartE for Emotional Intelligence. Ask me about empathy, EQ, and self-awareness.",
        "fallback": "I can only help with emotional intelligence topics. Please ask something related.",
        "fallback_const": "EMOTIONAL_INTELLIGENCE_FALLBACK",
    },
    {
        "id": "FinancialLiteracy",
        "label": "Financial Literacy",
        "domain": "financial-literacy",
        "welcome": "Hello! I'm SmartE for Financial Literacy. Ask me about saving, budgeting, and money basics.",
        "fallback": "I can only help with financial literacy topics. Please ask something related.",
        "fallback_const": "FINANCIAL_LITERACY_FALLBACK",
    },
]


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def create_page(bot: dict) -> None:
    content = read_file(PAGE_BASE)
    content = content.replace("Darshan AI", bot["label"])
    content = content.replace("religious-session-", f"{bot['domain']}-session-")
    content = content.replace("domain: 'religious'", f"domain: '{bot['domain']}'")
    content = content.replace("/api/ReligiousAI", f"/api/{bot['id']}")
    content = content.replace(
        "Hello! I'm Darshan AI. How can I help you today?",
        bot["welcome"],
    )
    content = content.replace("/dashboard/ReligiousAI", f"/dashboard/{bot['id']}")
    path = os.path.join(UI_DIR, "app", "dashboard", bot["id"], "page.js")
    write_file(path, content)


def create_api_route(bot: dict) -> None:
    content = read_file(API_BASE)
    content = content.replace("ReligiousAI", bot["id"])
    content = content.replace("RELIGIOUS_FALLBACK", bot["fallback_const"])
    content = content.replace(
        "isReligiousTopicAllowedByIntent",
        f"is{bot['id']}TopicAllowedByIntent",
    )
    content = content.replace("religious", bot["domain"])
    content = content.replace("religious-", f"{bot['domain']}-")
    content = content.replace(
        "I can only help with Indian religion and spirituality. Please ask a related question.",
        bot["fallback"],
    )
    path = os.path.join(UI_DIR, "app", "api", bot["id"], "route.js")
    write_file(path, content)


def main() -> None:
    for bot in BOTS:
        create_page(bot)
        create_api_route(bot)
        print(f"Created UI bot: {bot['id']}")


if __name__ == "__main__":
    main()
