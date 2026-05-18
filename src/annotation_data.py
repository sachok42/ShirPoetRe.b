from line_annotation import LineAnnotation
from rhyme_analysis import last_word
from rhythm_analysis import analyse_rhythm
from improved_rhyme_matching import detect_rhyme_scheme, suggest_rhyme_repairs


def format_stress(stress: str) -> str:
    return " ".join("/" if c == "1" else "o" for c in stress)


def build_annotations(poem_text: str) -> tuple[list[LineAnnotation], list[str]]:
    """
    Build per-line annotations for *poem_text*.

    Returns a ``(annotations, scheme)`` tuple so callers can use the same
    rhyme-scheme list that was used to produce the annotations, avoiding a
    second (potentially diverging) call to detect_rhyme_scheme.
    """
    raw_lines = poem_text.splitlines()
    nonempty  = [(i, l) for i, l in enumerate(raw_lines) if l.strip()]
    if not nonempty:
        return [], []

    just_lines = [l for _, l in nonempty]

    try:
        rhythm = analyse_rhythm("\n".join(just_lines))
        rhythm_data = rhythm.lines
    except Exception:
        rhythm_data = []

    try:
        scheme = detect_rhyme_scheme(just_lines)
    except Exception:
        scheme = ["?"] * len(just_lines)

    annotations: list[LineAnnotation] = []
    for idx, (_, line) in enumerate(nonempty):
        lr     = rhythm_data[idx] if idx < len(rhythm_data) else None
        letter = scheme[idx]      if idx < len(scheme)      else "?"
        annotations.append(LineAnnotation(
            stress       = format_stress(lr.stress)              if lr                      else "",
            foot         = lr.dominant_foot.title()               if lr and lr.dominant_foot else "",
            syllables    = lr.syllables                           if lr                      else 0,
            rhyme_letter = letter,
            rhyme_word   = last_word(line),
        ))
    return annotations, scheme