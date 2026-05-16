import re
import eng_to_ipa as ipa
from difflib import SequenceMatcher
import nltk
from nltk.corpus import words
from nltk import pos_tag

from sqlalchemy import create_engine, Column, Integer, String, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import contextmanager

# --- DATABASE SCHEMA ---
Base = declarative_base()


class PhoneticWord(Base):
    __tablename__ = 'phonetic_words'

    id = Column(Integer, primary_key=True)
    word = Column(String, unique=True, index=True)
    ipa_str = Column(String)
    syllables = Column(Integer, index=True)
    stress_idx = Column(Integer, index=True)
    suffix = Column(String, index=True)
    vowels_only = Column(String)
    pos_tag = Column(String, index=True)  # Added PoS Tag column

    __table_args__ = (
        Index('idx_filter_core', 'syllables', 'stress_idx', 'suffix', 'pos_tag'),
    )


class PhoneticEngine:
    VOWELS = "aeiouæɑɒɔəɛɪʊʌ"

    def __init__(self, db_url="sqlite:///phonetic_dictionary.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    @contextmanager
    def session_scope(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _extract_features(self, text):
        trans = ipa.convert(text)
        if "*" in trans or not trans: return None

        syllable_parts = re.findall(f"[{self.VOWELS}]+", trans)
        num_syl = len(syllable_parts)

        stress_idx = 0
        if "ˈ" in trans:
            pre_stress = trans.split("ˈ")[0]
            stress_idx = len(re.findall(f"[{self.VOWELS}]+", pre_stress))

        suffix = trans[-3:]
        v_only = "".join(re.findall(f"[{self.VOWELS}]", trans))

        # Get Part of Speech tag (NLTK returns a list of tuples)
        # We take the tag from the first result
        tag = pos_tag([text])[0][1]

        return {
            "ipa_str": trans,
            "syllables": num_syl,
            "stress_idx": stress_idx,
            "suffix": suffix,
            "vowels_only": v_only,
            "pos_tag": tag
        }

    def populate(self, limit=10000):
        nltk.download('words', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        word_list = sorted(list(set(w.lower() for w in words.words()[:limit])))

        with self.session_scope() as session:
            print(f"Analyzing {len(word_list)} words with PoS tagging...")
            for w in word_list:
                if session.query(PhoneticWord).filter_by(word=w).first():
                    continue
                feats = self._extract_features(w)
                if feats:
                    session.add(PhoneticWord(word=w, **feats))

    def search(self, syllables, stress, suffix, pos=None, target_vowels=None, poem_context=None):
        with self.session_scope() as session:
            query = session.query(PhoneticWord).filter(
                PhoneticWord.syllables == syllables,
                PhoneticWord.stress_idx == stress,
                PhoneticWord.suffix.like(f"%{suffix}")
            )

            # Optional PoS Filter (e.g., 'NN' for Nouns, 'VB' for Verbs)
            if pos:
                query = query.filter(PhoneticWord.pos_tag.startswith(pos))

            results = []
            for p_word in query.all():
                score = 0
                if target_vowels and p_word.vowels_only == target_vowels:
                    score += 50
                if poem_context:
                    ratio = SequenceMatcher(None, p_word.ipa_str, poem_context).ratio()
                    score += (ratio * 100)

                results.append({
                    "word": p_word.word,
                    "ipa": p_word.ipa_str,
                    "pos": p_word.pos_tag,
                    "score": round(score, 2)
                })

        return sorted(results, key=lambda x: x['score'], reverse=True)


if __name__ == "__main__":
    engine = PhoneticEngine()
    engine.populate(limit=5000)

    # Example: Searching for a 2-syllable NOUN (NN), 1st syllable stress, ending in 'i'
    search_results = engine.search(
        syllables=2,
        stress=0,
        suffix="i",
        pos="NN",  # Only Nouns
        target_vowels="æi",
        poem_context="ˈhæpi"
    )

    print("\n--- TOP RECOMMENDATIONS (NOUNS) ---")
    for res in search_results[:10]:
        print(f"{res['word']:<15} | IPA: {res['ipa']:<12} | PoS: {res['pos']:<5} | Score: {res['score']}")