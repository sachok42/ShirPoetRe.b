"""
poem_gap_fill.py
----------------
NLP function that proposes completions for a gap in a poem line,
constrained to rhyme with a target line and match style/grammar.

Usage:
    results = fill_gap(
        gap_line="The moon rose _____(3) and bright",
        rhyme_line="She vanished from my sight",
        n=4,
        context="...",          # optional: surrounding stanza for style context
        rhyme_scheme="ABAB",    # optional: hints near-rhyme tolerance
    )

Requires:
    pip install anthropic pronouncing
"""

import re
import json
import anthropic
import pronouncing  # CMU pronouncing dict for syllable counting & rhyme validation

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fill_gap(
    gap_line: str,
    rhyme_line: str,
    n: int = 4,
    context: str = "",
    rhyme_scheme: str = "",
) -> list[dict]:
    """
    Propose completions for a gap in a poem line.

    Parameters
    ----------
    gap_line : str
        The poem line with one gap marked as underscores, optionally with
        a syllable count hint in parentheses.
        Examples:
            "The moon rose _____ and bright"
            "The moon rose _____(3) and bright"
            "She walked _____(2) down the lane"
    rhyme_line : str
        A complete line that the filled line should rhyme with.
        The last word of this line is the rhyme target.
    n : int
        Number of suggestions to return (default 4).
    context : str
        Optional surrounding stanza or poem excerpt for style reference.
    rhyme_scheme : str
        Optional rhyme scheme label (e.g. "ABAB", "AABB") to guide how
        strict the rhyme match should be.

    Returns
    -------
    list[dict]  — each dict has:
        fill          str   the proposed word / phrase for the gap
        full_line     str   the complete line with fill inserted
        syllables     int   syllable count of the fill (0 if unknown)
        rhyme_score   str   "exact" | "near" | "family" | "unknown"
        rhyme_note    str   short explanation of the rhyme
        style_note    str   short explanation of stylistic fit
        grammar_note  str   short explanation of grammatical fit
    """
    gap_info = _parse_gap(gap_line)
    rhyme_target = _last_word(rhyme_line)

    raw_suggestions = _call_claude(
        gap_line=gap_line,
        rhyme_line=rhyme_line,
        rhyme_target=rhyme_target,
        syllable_hint=gap_info["syllable_hint"],
        n=n,
        context=context,
        rhyme_scheme=rhyme_scheme,
    )

    enriched = []
    for s in raw_suggestions:
        fill = s.get("fill", "")
        full_line = gap_info["template"].replace("{GAP}", fill, 1)
        syllables = _count_syllables(fill)
        rhyme_score = _rhyme_score(fill, rhyme_target)
        enriched.append({
            "fill": fill,
            "full_line": full_line,
            "syllables": syllables,
            "rhyme_score": rhyme_score,
            "rhyme_note": s.get("rhyme_note", ""),
            "style_note": s.get("style_note", ""),
            "grammar_note": s.get("grammar_note", ""),
        })

    return enriched


# ---------------------------------------------------------------------------
# Gap parsing
# ---------------------------------------------------------------------------

# Matches:  _____   or   _____(3)   or   ___(2)
_GAP_RE = re.compile(r"(_+)(?:\((\d+)\))?")


def _parse_gap(gap_line: str) -> dict:
    """
    Extract the syllable hint (if any) and return a template string where the
    gap is replaced with the placeholder {GAP}.
    """
    m = _GAP_RE.search(gap_line)
    if not m:
        raise ValueError(
            "No gap found in gap_line. Mark the gap with underscores, "
            "e.g. 'The moon rose _____ and bright' or 'rose _____(3) and'."
        )
    syllable_hint = int(m.group(2)) if m.group(2) else None
    template = gap_line[: m.start()] + "{GAP}" + gap_line[m.end() :]
    return {"template": template, "syllable_hint": syllable_hint}


def _last_word(line: str) -> str:
    words = re.findall(r"[a-zA-Z']+", line)
    return words[-1].lower() if words else ""


# ---------------------------------------------------------------------------
# Syllable counting via CMU dict, fallback to vowel heuristic
# ---------------------------------------------------------------------------

def _count_syllables(phrase: str) -> int:
    """Count syllables in a word or short phrase."""
    total = 0
    for word in phrase.lower().split():
        phones = pronouncing.phones_for_word(word)
        if phones:
            total += pronouncing.syllable_count(phones[0])
        else:
            total += _heuristic_syllables(word)
    return total


def _heuristic_syllables(word: str) -> int:
    word = word.lower().strip(".,!?;:")
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


# ---------------------------------------------------------------------------
# Rhyme scoring via CMU phones
# ---------------------------------------------------------------------------

def _rhyme_score(fill: str, target: str) -> str:
    """
    Return one of: "exact", "near", "family", "unknown".

    Exact  — identical final vowel+consonants phones
    Near   — identical final vowel, consonants differ slightly (1 phone off)
    Family — share the same vowel nucleus
    Unknown — no CMU entry for one or both words
    """
    fill_last = fill.lower().split()[-1] if fill.strip() else ""
    fill_phones_list = pronouncing.phones_for_word(fill_last)
    target_phones_list = pronouncing.phones_for_word(target)

    if not fill_phones_list or not target_phones_list:
        return "unknown"

    # Use the first pronunciation for each
    def rhyming_part(phones_str: str) -> list[str]:
        """Phones from the last stressed vowel onward."""
        phones = phones_str.split()
        for i in range(len(phones) - 1, -1, -1):
            if phones[i][-1].isdigit():  # stressed vowel has a digit
                return phones[i:]
        return phones

    fp = rhyming_part(fill_phones_list[0])
    tp = rhyming_part(target_phones_list[0])

    if fp == tp:
        return "exact"

    # Same vowel nucleus
    fill_vowel = fp[0] if fp else ""
    target_vowel = tp[0] if tp else ""

    if fill_vowel == target_vowel:
        # Near if only one phone differs in the tail
        if abs(len(fp) - len(tp)) <= 1 and sum(a != b for a, b in zip(fp, tp)) <= 1:
            return "near"
        return "family"

    return "unknown"


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

def _call_claude(
    gap_line: str,
    rhyme_line: str,
    rhyme_target: str,
    syllable_hint: int | None,
    n: int,
    context: str,
    rhyme_scheme: str,
) -> list[dict]:
    syllable_instruction = (
        f"The fill must be exactly {syllable_hint} syllable(s)."
        if syllable_hint
        else "Match a natural syllable count for the meter."
    )

    context_block = (
        f"\n\nSurrounding stanza for style reference:\n{context}"
        if context
        else ""
    )
    scheme_block = (
        f"\n\nRhyme scheme: {rhyme_scheme}. Calibrate rhyme strictness accordingly."
        if rhyme_scheme
        else ""
    )

    prompt = f"""You are an expert poetry editor filling a gap in a poem line.

Line with gap:
  {gap_line}
  (The underscores mark the missing syllables. {{GAP}} is where the fill goes.)

Rhyme target line (the filled line must rhyme with this):
  {rhyme_line}
  (Rhyme target word: "{rhyme_target}"){context_block}{scheme_block}

Instructions:
- Propose exactly {n} distinct fills for the gap.
- {syllable_instruction}
- Each fill must rhyme with "{rhyme_target}" (exact or near rhyme preferred).
- Each fill must match the stylistic register (archaic/lyrical/modern/etc.).
- Each fill should fit grammatically — match the part of speech and syntactic role implied by the surrounding words.
- Vary the options meaningfully (don't just rephrase the same idea).

Return ONLY a JSON array, no markdown fences, no extra text:
[
  {{
    "fill": "<word or short phrase>",
    "rhyme_note": "<one short sentence on how it rhymes>",
    "style_note": "<one short sentence on stylistic fit>",
    "grammar_note": "<one short sentence on grammatical fit>"
  }}
]"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    examples = [
        dict(
            gap_line="The moon rose _____(2) and bright",
            rhyme_line="She vanished from my sight",
        ),
        dict(
            gap_line="I heard the _____ call at dawn",
            rhyme_line="Before the mist had gone",
            context="The birds returned as spring began,\nAnd woke the sleeping land.",
            rhyme_scheme="ABAB",
        ),
        dict(
            gap_line="She walked the _____(3) road alone",
            rhyme_line="Her heart had turned to stone",
        ),
    ]

    for ex in examples:
        print("=" * 60)
        print(f"Gap line   : {ex['gap_line']}")
        print(f"Rhyme line : {ex['rhyme_line']}")
        print()
        results = fill_gap(**ex)
        for i, r in enumerate(results, 1):
            score_symbol = {"exact": "✓✓", "near": "✓~", "family": "~", "unknown": "?"}.get(r["rhyme_score"], "?")
            print(f"  [{i}] {score_symbol} \"{r['fill']}\"  ({r['syllables']} syl)")
            print(f"       → {r['full_line']}")
            print(f"       rhyme  : {r['rhyme_note']}")
            print(f"       style  : {r['style_note']}")
            print(f"       grammar: {r['grammar_note']}")
            print()