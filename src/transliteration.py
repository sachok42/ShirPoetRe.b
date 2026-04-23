import eng_to_ipa as ipa

vowels = ["a", "o", "e", "i", "u"]

rhyme_importance = 1
vowels_importance = 1

def convert(text):
    return ipa.convert(text)

def common_ending(text1, text2):
    return "".join(sound1 if sound1 == sound2 else " " for sound1, sound2 in zip(convert(text1), convert(text2))).strip()

def vowel_structure(text):
    res = []
    for char in text:
        if char in vowels:
            res.append(char)
    return res

def vowels_rhyme(text1, text2):
    irregularities = 0
    vowel_structures = zip(vowel_structure(text1)[-1::-1], vowel_structure(text2)[-1::-1])
    structure1, structure2 = vowel_structures
    for vowel1, vowel2 in vowel_structures:
        if vowel1 == vowel2:
            irregularities += 1
    return irregularities / min(len(structure1), len(structure2))

def ending_rhyme(text1, text2):
    res = 0
    for letter in common_ending(text1, text2):
        if letter in vowels:
            res += 1
    return res

def rate_candidate(candidate, rhyming_word):
    return ending_rhyme(candidate, rhyming_word) * rhyme_importance\
        + vowels_rhyme(candidate, rhyming_word) * vowels_importance