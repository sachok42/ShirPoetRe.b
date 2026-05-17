class LineAnnotation:
    __slots__ = ("stress", "foot", "syllables", "rhyme_letter", "rhyme_word")

    def __init__(self, stress="", foot="", syllables=0,
                 rhyme_letter="", rhyme_word=""):
        self.stress       = stress
        self.foot         = foot
        self.syllables    = syllables
        self.rhyme_letter = rhyme_letter
        self.rhyme_word   = rhyme_word
