from utils import sentiment, word_sentiment
from rhyme_analysis import last_word, words_rhyme
from typing import Optional
from style_analysis import build_style_profile, rate_style_score
import string


# A small built-in vocabulary drawn from common poetic words.
# In a real IDE this would be backed by a word-list file.
_POETIC_WORDS: list[str] = [
    "light", "night", "bright", "flight", "sight", "right", "might", "white",
    "dark", "spark", "bark", "mark", "heart", "start", "art", "part",
    "dream", "stream", "gleam", "beam", "seem", "team",
    "love", "dove", "above", "shove", "glove",
    "sky", "fly", "cry", "by", "high", "sigh", "lie", "die", "try", "why",
    "rain", "pain", "gain", "plain", "vain", "chain", "lane", "flame",
    "sea", "free", "tree", "be", "me", "see", "thee",
    "stone", "alone", "bone", "tone", "moan", "groan", "known",
    "fire", "desire", "higher", "lyre", "entire",
    "wind", "mind", "find", "blind", "kind", "behind",
    "time", "rhyme", "climb", "chime", "sublime",
    "deep", "sleep", "keep", "weep", "leap", "sweep",
    "cold", "bold", "gold", "old", "told", "hold", "fold",
    "grace", "place", "face", "space", "trace", "embrace",
    "soul", "whole", "role", "toll", "bowl", "stroll",
    "breath", "death", "beneath", "wreath",
    "shore", "more", "before", "door", "floor", "core", "roar",
    "rose", "close", "flows", "glows", "knows", "goes",
    "blue", "true", "through", "dew", "new", "grew",
    "silence", "violence", "reliance", "alliance",
    "sorrow", "tomorrow", "borrow",
    "gentle", "mental", "central",
    "shadow", "meadow", "follow", "hollow",
]


def rhymes_with(word: str, vocabulary: list[str]) -> list[str]:
    """Return all words in *vocabulary* that rhyme with *word*."""
    return [w for w in vocabulary if w.lower() != word.lower() and words_rhyme(word, w)]


def sentiment_distance(text: str, word: str) -> float:
    """Absolute polarity difference between a text block and a single word."""
    pol_text, _ = sentiment(text)
    pol_word, _ = word_sentiment(word)
    return abs(pol_text - pol_word)


def suggest_rhyme_repairs(
    anchor_line: str,
    broken_line: str,
    extra_vocabulary: Optional[list[str]] = None,
    top_n: int = 5,
) -> list[dict]:
    """
    Suggest replacement *last words* for *broken_line* that:
      - rhyme with the last word of *anchor_line*
      - are as close in sentiment to *broken_line* as possible

    Returns up to *top_n* suggestions, each a dict with:
      'word'             – the suggested replacement
      'rhyme_with'       – the anchor word it rhymes with
      'sentiment_delta'  – how far its polarity is from the broken line's
      'style_score'      – how well it fits the broken line stylistically
      'example_line'     – broken_line with its last word swapped

    Example
    -------
    >>> suggest_rhyme_repairs(
    ...     "I wander under skies of blue",
    ...     "the clouds roll in and hide the sun"
    ... )
    [{'word': 'new', 'rhyme_with': 'blue', ...}, ...]
    """
    vocab = list(set(_POETIC_WORDS + (extra_vocabulary or [])))

    anchor_word = last_word(anchor_line)
    rhyming     = rhymes_with(anchor_word, vocab)

    if not rhyming:
        return []

    scored = []
    for candidate in rhyming:
        sent_delta  = sentiment_distance(broken_line, candidate)
        style_score = rate_style_score(candidate, build_style_profile(broken_line))
        example     = swap_last_word(broken_line, candidate)
        scored.append({
            "word":           candidate,
            "rhyme_with":     anchor_word,
            "sentiment_delta": round(sent_delta, 4),
            "style_score":    style_score,
            "example_line":   example,
        })

    # Sort by sentiment closeness first, then style fit
    scored.sort(key=lambda x: (x["sentiment_delta"], -x["style_score"]))
    return scored[:top_n]


def swap_last_word(line: str, new_word: str) -> str:
    """Replace the final word in *line* with *new_word*, preserving punctuation."""
    stripped = line.rstrip(string.punctuation + " ")
    trailing = line[len(stripped):]
    parts    = stripped.rsplit(None, 1)
    if len(parts) == 2:
        return parts[0] + " " + new_word + trailing
    return new_word + trailing
