from style_analysis import rank_words_by_style
from rhyme_repair import suggest_rhyme_repairs
from rhyme_analysis import check_rhyme
from rhythm_analysis import analyse_rhythm

if __name__ == "__main__":
    print("=" * 60)
    print("1. STYLE FIT")
    print("=" * 60)
    text = "the silent moon drifts through pale and hollow skies"
    candidates = ["gloom", "happy", "luminous", "swift", "gentle", "darkness", "bright"]
    ranked = rank_words_by_style(text, candidates)
    for word, score in ranked:
        print(f"  {word:<12} {score}")

    print()
    print("=" * 60)
    print("2. RHYTHM")
    print("=" * 60)
    poem = (
        "Shall I compare thee to a summer's day\n"
        "Thou art more lovely and more temperate\n"
        "Rough winds do shake the darling buds of May\n"
        "And summer's lease hath all too short a date"
    )
    rhythm = analyse_rhythm(poem)
    print(f"  Overall metre   : {rhythm.overall_metre}")
    print(f"  Regularity score: {rhythm.regularity_score}")
    for lr in rhythm.lines:
        print(f"  [{lr.syllables:2d} syl | {lr.dominant_foot}] {lr.stress}  '{lr.line}'")

    print()
    print("=" * 60)
    print("3. RHYME CHECK")
    print("=" * 60)
    for a, b in [
        ("the moon shines bright tonight", "the stars give off their light"),
        ("I love the golden light", "the river runs below"),
    ]:
        r = check_rhyme(a, b)
        print(f"  '{r.word_a}' / '{r.word_b}' → rhymes={r.rhymes}, distance={r.distance}")
        for opt in r.repair_options[:2]:
            print(f"    repair: {opt}")

    print()
    print("=" * 60)
    print("4. RHYME REPAIR")
    print("=" * 60)
    suggestions = suggest_rhyme_repairs(
        "I wander under skies of blue",
        "the clouds roll in and hide the sun",
    )
    for s in suggestions:
        print(f"  '{s['word']}' (Δsentiment={s['sentiment_delta']}, style={s['style_score']})")
        print(f"    → {s['example_line']}")