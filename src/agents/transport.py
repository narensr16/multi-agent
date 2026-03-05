"""
transport.py — Transport Agent

Searches Tavily for transport options to the destination.
Uses strict mode-matching so each transport mode only gets content about that mode.
"""

import os
import re
import json
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_groq import ChatGroq

load_dotenv()

_TAVILY_KEY = os.getenv("TAVILY_API_KEY", "").strip()
_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Mode patterns — POSITIVE match for the mode AND NEGATIVE for other modes
_MODES = {
    "✈  By Air   ": {
        "pos": re.compile(
            r"\b(flight|fly|airport|airline|airways|air india|indigo|spicejet|vistara|akasa|terminal)\b",
            re.IGNORECASE,
        ),
        "neg": re.compile(r"\b(train|bus|road|highway)\b", re.IGNORECASE),
    },
    "🚆  By Train ": {
        "pos": re.compile(
            r"\b(train|railway|rail|irctc|express|superfast|shatabdi|rajdhani|junction|railway station)\b",
            re.IGNORECASE,
        ),
        "neg": re.compile(r"\b(flight|fly|airport|bus|cab)\b", re.IGNORECASE),
    },
    "🚌  By Bus   ": {
        "pos": re.compile(
            r"\b(bus|road|highway|nh\s*\d|national highway|drive|cab|ksrtc|msrtc|gsrtc|volvo|coach)\b",
            re.IGNORECASE,
        ),
        "neg": re.compile(r"\b(flight|fly|airport|train|rail)\b", re.IGNORECASE),
    },
}


def _clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\|", " - ", text)  # Replace | with -
    text = re.sub(r"[\s*]+", " ", text)
    return text.strip()


def _best_sentence(text: str, pos: re.Pattern, neg: re.Pattern, max_chars: int = 160) -> str:
    """Return first sentence that matches pos pattern AND doesn't match neg pattern."""
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    
    def is_personal(s):
        return re.search(r"\b(i|my|we|our|me|you)\b", s, re.IGNORECASE)

    for s in sentences:
        s = s.strip()
        if len(s) < 20 or is_personal(s):
            continue
        if pos.search(s) and not neg.search(s):
            return s[:max_chars] + ("…" if len(s) > max_chars else "")
    # Fallback: accept sentence even if neg matches, just needs pos
    for s in sentences:
        s = s.strip()
        if len(s) > 20 and pos.search(s) and not is_personal(s):
            return s[:max_chars] + ("…" if len(s) > max_chars else "")
    return ""


def transport_agent(state: dict) -> dict:
    destination = state.get("destination", "")

    if not destination or destination == "Unknown":
        return {"transport": "Transport search skipped: destination unknown."}
    if not _TAVILY_KEY:
        return {"transport": "Transport search skipped: TAVILY_API_KEY not configured."}

    try:
        client = TavilyClient(api_key=_TAVILY_KEY)

        # Run mode-specific queries for better precision
        all_text = {}
        for mode_label in _MODES:
            if "Air" in mode_label:
                q = f"how to reach {destination} by flight airport nearest airlines"
            elif "Train" in mode_label:
                q = f"how to reach {destination} by train railway station nearest"
            else:
                q = f"how to reach {destination} by bus road highway distance hours"

            res = client.search(q, max_results=3)
            parts = [_clean(res.get("answer") or "")]
            parts += [_clean(r.get("content") or "") for r in res.get("results") or []]
            all_text[mode_label] = " ".join(p for p in parts if p)

        # Extract one clean sentence per mode
        lines = []

        if _GROQ_KEY and _GROQ_KEY != "your_groq_api_key_here":
            try:
                llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama3-8b-8192", temperature=0)
                combined_text = "\n".join(f"--- {k} ---\n{v}" for k, v in all_text.items() if v)
                prompt = (
                    f"Read the text below and extract exactly one short, objective sentence explaining how to reach {destination} "
                    f"for each of these modes: By Air, By Train, and By Bus.\n"
                    f"Do NOT include personal pronouns (I, my, we). Keep it strictly factual.\n"
                    f"Return ONLY a JSON dictionary where the keys are exactly '✈  By Air   ', '🚆  By Train ', and '🚌  By Bus   ' "
                    f"and the values are the extracted sentences.\n"
                    f"If a mode is unavailable, return an empty string for that key.\n\nText: {combined_text}"
                )
                res = llm.invoke(prompt)
                content = res.content.strip()
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                
                parsed = json.loads(content.strip())
                for label in _MODES.keys():
                    if parsed.get(label):
                        lines.append(f"  {label}: {parsed[label]}")
            except Exception as e:
                print(f"Groq parsing failed: {e}")

        if not lines:
            for label, patterns in _MODES.items():
                text = all_text.get(label, "")
                sentence = _best_sentence(text, patterns["pos"], patterns["neg"])
                if sentence:
                    lines.append(f"  {label}: {sentence}")

        transport_text = "\n".join(lines) if lines else f"  Transport info not available for {destination}."

    except Exception as e:
        transport_text = f"  Transport search failed: {e}"

    return {"transport": transport_text}