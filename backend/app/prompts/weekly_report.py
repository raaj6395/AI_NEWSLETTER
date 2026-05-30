"""Prompt construction for the weekly AI report (Milestone 10)."""

# Required report sections, in order. Also used to nudge the model and to
# sanity-check generated output.
REPORT_SECTIONS = [
    "Major Headlines",
    "Research",
    "Funding",
    "New Models",
    "Outlook",
]

SYSTEM_PROMPT = (
    "You are an expert AI-industry analyst writing a concise, factual weekly "
    "report for a technical audience. Base every statement strictly on the "
    "provided stories — do not invent facts, numbers, or companies. Write in "
    "clear Markdown."
)


def _format_stories(grouped: dict[str, list[dict]]) -> str:
    """Render the grouped story context as a compact Markdown list."""
    lines: list[str] = []
    for category, stories in grouped.items():
        if not stories:
            continue
        lines.append(f"### {category}")
        for s in stories:
            sources = ", ".join(s.get("sources", [])) or "unknown"
            summary = (s.get("summary") or "").strip().replace("\n", " ")
            if len(summary) > 300:
                summary = summary[:300] + "…"
            lines.append(f"- **{s['title']}** (sources: {sources})")
            if summary:
                lines.append(f"  {summary}")
        lines.append("")
    return "\n".join(lines).strip()


def build_user_prompt(
    grouped: dict[str, list[dict]], week_start: str, week_end: str
) -> str:
    """Build the user prompt instructing the model to produce the report."""
    sections = "\n".join(f"## {name}" for name in REPORT_SECTIONS)
    context = _format_stories(grouped)
    return f"""\
Write the **AI Weekly Report** covering {week_start} to {week_end}.

Use EXACTLY these Markdown sections, in this order, each as an H2 heading:

{sections}

Guidance:
- "Major Headlines": the 3–6 most important developments of the week.
- "Research": notable papers, studies, benchmarks, or technical breakthroughs.
- "Funding": funding rounds, investments, acquisitions, valuations.
- "New Models": newly announced or released AI models/products.
- "Outlook": a short forward-looking synthesis (2–4 sentences).
If a section has no relevant stories, write "No notable items this week."
Keep it concise and group related items. Do not add sections beyond those listed.

Here are this week's deduplicated stories, grouped by topic:

{context}
"""
