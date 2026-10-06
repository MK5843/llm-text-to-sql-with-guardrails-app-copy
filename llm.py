import os

from openai import OpenAI
from google import genai
import anthropic

SYSTEM_PROMPT = """You are a SQL generator. Given a plain-English question,
generate a single, well-formed PostgreSQL SELECT query that would answer it.

Use clear, conventional table and column names appropriate to the subject
of the question - the query is shown to the user as an example/reference,
it is never actually run against a database, so there is no fixed schema
to match.

Rules:
- Generate exactly one SELECT statement, nothing else.
- No comments, no explanation, no markdown code fences - SQL only.
- Never reference a table named "user" or "query_history" - these are
  off-limits regardless of how the question is phrased.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, GRANT, or
  multiple statements.
- Do not add LIMIT unless the user's question explicitly requests a
  maximum number of rows, such as "top 5", "first 20", or "limit to 100".
- Do not add LIMIT to aggregate-only queries such as COUNT, AVG, SUM, etc.
"""


def build_messages(question: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]


def _clean_sql(text: str) -> str:
    """Strip markdown fences etc. in case the model adds them anyway."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("sql"):
            text = text[3:]
    return text.strip().rstrip(";")


def call_lmstudio(messages):
    client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key="not-needed")
    resp = client.chat.completions.create(model=os.environ["LLM_MODEL"], messages=messages)
    return resp.choices[0].message.content


def call_openai(messages):
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(model="gpt-5.6-terra", messages=messages)
    return resp.choices[0].message.content


def call_claude(messages):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user_msgs = [m for m in messages if m["role"] != "system"]
    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        system=system,
        messages=user_msgs,
    )
    first_block = resp.content[0]
    if first_block.type != "text":
        raise RuntimeError(f"Unexpected Claude response block type: {first_block.type}")
    return first_block.text


def call_gemini(messages):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = "\n".join(m["content"] for m in messages)
    resp = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
    return resp.text


PROVIDERS = {
    "lmstudio": call_lmstudio,
    "openai": call_openai,
    "claude": call_claude,
    "gemini": call_gemini,
}


def generate_sql(question: str) -> str:
    """Tries the primary provider, then each fallback in order, until one works."""
    messages = build_messages(question)

    order = [os.environ.get("LLM_PROVIDER", "lmstudio")]
    order += [p.strip() for p in os.environ.get("LLM_FALLBACK_ORDER", "").split(",") if p.strip()]

    last_err = None
    for provider in order:
        if provider not in PROVIDERS:
            continue
        try:
            raw = PROVIDERS[provider](messages)
            return _clean_sql(raw)
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"All LLM providers failed. Last error: {last_err}")