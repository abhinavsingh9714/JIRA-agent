from __future__ import annotations
import statistics
from collections import Counter
from typing import List, Dict, Any, Sequence
import textwrap

def adf2text(adf: dict) -> str:
    out = []
    for node in adf.get("content", []):
        if node["type"] == "paragraph":
            out.append("".join(p.get("text", "") for p in node.get("content", [])))
        elif node["type"] == "heading":
            lvl = node["attrs"]["level"]
            title = "".join(p.get("text", "") for p in node.get("content", []))
            out.append(f"{'#' * lvl} {title}")
    return " ".join(out)

# try:
#     from epic_creator.services.llm_small import run_small_llm  # optional
# except ImportError:
#     def run_small_llm(prompt: str) -> str:  # type: ignore
#         return prompt


__all__ = ["ProjectStyleAnalyzer"]


class ProjectStyleAnalyzer:
    """
    Turn a list of issue dicts into a concise Jira-style guide string.

    Summary stats + examples are kept under ~4 KB.
    """

    MAX_EXAMPLES = 3
    EXAMPLE_CHAR_CAP = 200

    def summarize(self, issues: List[Dict[str, Any]]) -> str:
        if not issues:
            return "No prior issues found – follow standard Jira defaults."

        stats = self._stats_section(issues)
        examples = self._examples_section(issues)

        guide = f"""=== Jira Ticket Style Guide ===
{stats}

=== Representative Examples ===
{examples}"""

        # return self._compress(guide)
        return guide

    def _stats_section(self, issues: Sequence[Dict[str, Any]]) -> str:
        summaries = [i["summary"] for i in issues if i.get("summary")]
        avg_words = round(statistics.mean(len(s.split()) for s in summaries), 1)

        labels = Counter(l for i in issues for l in i.get("labels", []))
        label_line = ", ".join(f"{l} ({n})" for l, n in labels.most_common(5)) or "—"

        imperative_ratio = sum(
            1 for s in summaries if s.split()[0].istitle()  # basic guess
        ) / max(1, len(summaries))

        tone = "imperative-style summaries" if imperative_ratio > 0.5 else "mixed phrasing"

        return (
            f"• Avg summary length: {avg_words} words\n"
            f"• Top project labels: {label_line}\n"
            f"• Summary tone: {tone}"
        )

    def _examples_section(self, issues: Sequence[Dict[str, Any]]) -> str:
        epics = [i for i in issues if i.get("issuetype", "").lower() == "epic"]
        stories = [i for i in issues if i.get("issuetype", "").lower() == "story"]

        def top_n(items: List[dict], n: int) -> List[dict]:
            return sorted(items, key=lambda x: len(str(x.get("description", ""))), reverse=True)[:n]

        n_epics = min(len(epics), self.MAX_EXAMPLES)
        n_stories = min(len(stories), self.MAX_EXAMPLES)

        chosen = top_n(epics, n_epics) + top_n(stories, n_stories)

        lines = []
        for i in chosen:
            desc = i.get("description", "")
            if isinstance(desc, dict) and desc.get("type") == "doc":
                desc = adf2text(desc)
            elif isinstance(desc, str):
                desc = desc
            else:
                desc = "<no description>"

            # short_desc = desc.strip().replace("\n", " ")[: self.EXAMPLE_CHAR_CAP]
            short_desc = textwrap.shorten(desc, width=200, placeholder="…")
            lines.append(f"[{i['issuetype']}] {i['summary']}\n{short_desc}")

        return "\n\n".join(lines)

    # def _compress(self, text: str) -> str:
    #     prompt = (
    #         f"Compress the following Jira ticket style guide into ≤4 KB without losing essential content:\n\n{text}"
    #     )
    #     try:
    #         compressed = run_small_llm(prompt)
    #         return compressed if len(compressed) < len(text) else text
    #     except Exception:
    #         return text