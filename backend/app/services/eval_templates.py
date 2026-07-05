"""Pre-built eval benchmark templates by industry."""

EVAL_TEMPLATES: list[dict] = [
    {
        "id": "customer_support",
        "name": "Customer support",
        "industry": "Support",
        "description": "Refund, shipping, and account scenarios for support bots.",
        "cases": [
            {"input": "How do I request a refund?", "expected": "refund", "match_type": "contains"},
            {"input": "Where is my order #12345?", "expected": "track", "match_type": "contains"},
            {"input": "I forgot my password", "expected": "reset", "match_type": "contains"},
            {"input": "What are your business hours?", "expected": "hour", "match_type": "contains"},
        ],
    },
    {
        "id": "healthcare",
        "name": "Healthcare FAQ",
        "industry": "Healthcare",
        "description": "General health information boundaries and appointment flows.",
        "cases": [
            {"input": "Book a routine check-up", "expected": "appointment", "match_type": "contains"},
            {"input": "What are your clinic hours?", "expected": "hour", "match_type": "contains"},
            {"input": "Can you diagnose my chest pain?", "expected": "doctor", "match_type": "contains"},
            {"input": "How do I get my lab results?", "expected": "result", "match_type": "contains"},
        ],
    },
    {
        "id": "finance",
        "name": "Finance & banking",
        "industry": "Finance",
        "description": "Balances, transfers, and security questions.",
        "cases": [
            {"input": "Check my account balance", "expected": "balance", "match_type": "contains"},
            {"input": "How do I transfer money?", "expected": "transfer", "match_type": "contains"},
            {"input": "I see a suspicious charge", "expected": "fraud", "match_type": "contains"},
            {"input": "What is the savings interest rate?", "expected": "rate", "match_type": "contains"},
        ],
    },
    {
        "id": "ecommerce",
        "name": "E-commerce",
        "industry": "Retail",
        "description": "Product search, returns, and promotions.",
        "cases": [
            {"input": "Do you have wireless headphones under $100?", "expected": "headphone", "match_type": "contains"},
            {"input": "What is your return policy?", "expected": "return", "match_type": "contains"},
            {"input": "Apply discount code SAVE10", "expected": "discount", "match_type": "contains"},
            {"input": "When will this item ship?", "expected": "ship", "match_type": "contains"},
        ],
    },
    {
        "id": "general",
        "name": "General assistant",
        "industry": "General",
        "description": "Baseline helpfulness and safety checks.",
        "cases": [
            {"input": "Summarize quantum computing in one sentence", "expected": "quantum", "match_type": "contains"},
            {"input": "What is 15% of 240?", "expected": "36", "match_type": "contains"},
            {"input": "Write a polite decline email", "expected": "thank", "match_type": "contains"},
        ],
    },
]


def list_templates() -> list[dict]:
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "industry": t["industry"],
            "description": t["description"],
            "case_count": len(t["cases"]),
        }
        for t in EVAL_TEMPLATES
    ]


def get_template(template_id: str) -> dict | None:
    for t in EVAL_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
