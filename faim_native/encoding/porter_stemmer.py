"""Porter Stemmer (1980) — Pure Python implementation.

Algorithm: Porter, M. "An algorithm for suffix stripping." Program 14.3 (1980): 130-137.

This is a deterministic, dependency-free implementation of the Porter stemming algorithm,
commonly used in information retrieval to normalize inflected words to their root form.

Examples:
  - "running", "runs", "runner" → "run"
  - "user", "users" → "user"
  - "connected", "connecting" → "connect"
  - "relational", "relate" → "relat"
"""

STOP_WORDS = frozenset(
    {
        "the",
        "is",
        "at",
        "which",
        "on",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "for",
        "with",
        "that",
        "this",
        "it",
        "be",
        "as",
        "by",
        "from",
        "are",
        "was",
        "were",
    }
)


def _is_vowel(char: str) -> bool:
    """Check if character is a vowel (a, e, i, o, u, y)."""
    return char in "aeiouy"


def _measure(word: str) -> int:
    """
    Compute the measure (vc-count) of the word.

    VC-count is the number of VC (vowel-consonant) patterns.
    - C = consonant, V = vowel
    - measure = number of VC pairs
    - Measure of 0: consonant-only or vowel-only
    - Measure of 1: CVC or VCV, etc.

    Examples:
      - "tr" (cc) → 0
      - "tree" (ccvv) → 1
      - "troubles" (ccvccvv) → 2
    """
    if len(word) < 2:
        return 0

    vc_count = 0
    prev_is_vowel = _is_vowel(word[0])
    for i in range(1, len(word)):
        curr_is_vowel = _is_vowel(word[i])
        # Transition from consonant to vowel is a VC pattern
        if not prev_is_vowel and curr_is_vowel:
            vc_count += 1
        prev_is_vowel = curr_is_vowel

    return vc_count


def _ends_with_double(word: str) -> bool:
    """Check if word ends with a double consonant."""
    if len(word) < 2:
        return False
    return word[-1] == word[-2] and not _is_vowel(word[-1])


def _is_cvc(word: str) -> bool:
    """
    Check if word ends in CVC pattern where:
    - C is consonant
    - V is vowel
    - final C is not w, x, or y
    """
    if len(word) < 3:
        return False
    return (
        not _is_vowel(word[-3])
        and _is_vowel(word[-2])
        and not _is_vowel(word[-1])
        and word[-1] not in "wxy"
    )


def _step1a(word: str) -> str:
    """Step 1a: plurals and past tense."""
    if word.endswith("sses"):
        return word[:-2]  # "caresses" → "caress"
    elif word.endswith("ies"):
        return word[:-3] + "i"  # "ponies" → "poni"
    elif word.endswith("ss"):
        return word  # "caress" → "caress"
    elif word.endswith("s"):
        return word[:-1]  # "cats" → "cat"
    return word


def _step1b(word: str) -> str:
    """Step 1b: -eed, -ed, -ing."""
    if word.endswith("eed"):
        stem = word[:-3]
        if _measure(stem) > 0:
            return stem + "ee"
        return word
    elif word.endswith("ed") or word.endswith("ing"):
        stem = word[:-2] if word.endswith("ed") else word[:-3]
        if any(_is_vowel(c) for c in stem):
            # Apply step 1b rules
            if stem.endswith("at") or stem.endswith("bl") or stem.endswith("iz"):
                return stem + "e"
            elif _ends_with_double(stem) and stem[-1] not in "lsz":
                return stem[:-1]
            elif _measure(stem) == 1 and _is_cvc(stem):
                return stem + "e"
            return stem
    return word


def _step1c(word: str) -> str:
    """Step 1c: -y to -i."""
    if len(word) > 1 and word.endswith("y"):
        stem = word[:-1]
        if any(_is_vowel(c) for c in stem[:-1]):
            return stem + "i"
    return word


def _step2(word: str) -> str:
    """Step 2: convert longer suffixes to shorter forms."""
    rules = [
        ("ational", "ate"),
        ("tional", "tion"),
        ("enci", "ence"),
        ("anci", "ance"),
        ("izer", "ize"),
        ("bli", "ble"),
        ("alli", "al"),
        ("entli", "ent"),
        ("eli", "e"),
        ("ousli", "ous"),
        ("ization", "ize"),
        ("ation", "ate"),
        ("ator", "ate"),
        ("alism", "al"),
        ("iveness", "ive"),
        ("fulness", "ful"),
        ("ousness", "ous"),
        ("aliti", "al"),
        ("iviti", "ive"),
        ("biliti", "ble"),
    ]
    for suffix, replacement in rules:
        if word.endswith(suffix):
            stem = word[: -len(suffix)]
            if _measure(stem) > 0:
                return stem + replacement
    return word


def _step3(word: str) -> str:
    """Step 3: further suffix removal."""
    rules = [
        ("icate", "ic"),
        ("ative", ""),
        ("alize", "al"),
        ("iciti", "ic"),
        ("ical", "ic"),
        ("ful", ""),
        ("ness", ""),
    ]
    for suffix, replacement in rules:
        if word.endswith(suffix):
            stem = word[: -len(suffix)]
            if _measure(stem) > 0:
                return stem + replacement
    return word


def _step4(word: str) -> str:
    """Step 4: remove suffixes from words with measure > 1."""
    suffixes = [
        "al",
        "ance",
        "ence",
        "er",
        "ic",
        "able",
        "ible",
        "ant",
        "ement",
        "ment",
        "ent",
        "ou",
        "ion",
        "ou",
    ]
    for suffix in suffixes:
        if word.endswith(suffix):
            stem = word[: -len(suffix)]
            if _measure(stem) > 1:
                if suffix == "ion":
                    if len(stem) > 0 and stem[-1] in "st":
                        return stem
                else:
                    return stem
    return word


def _step5a(word: str) -> str:
    """Step 5a: remove 'e'."""
    if word.endswith("e"):
        stem = word[:-1]
        m = _measure(stem)
        if m > 1:
            return stem
        elif m == 1 and not _is_cvc(stem):
            return stem
    return word


def _step5b(word: str) -> str:
    """Step 5b: remove 'll' if measure > 1."""
    if word.endswith("ll") and _measure(word[:-1]) > 1:
        return word[:-1]
    return word


def stem(word: str) -> str:
    """
    Apply Porter stemming algorithm to a single word.

    Input should be lowercase. Returns the stemmed form.

    Examples:
      >>> stem("running")
      'run'
      >>> stem("troubles")
      'troubl'
      >>> stem("user")
      'user'
    """
    if len(word) <= 2:
        return word

    word = _step1a(word)
    word = _step1b(word)
    word = _step1c(word)
    word = _step2(word)
    word = _step3(word)
    word = _step4(word)
    word = _step5a(word)
    word = _step5b(word)

    return word


def stem_text(text: str) -> str:
    """
    Stem all non-stopword tokens in text.

    Input must be pre-lowercased.
    Stopwords are kept as-is (they affect n-gram boundaries).

    Returns the stemmed text.

    Examples:
      >>> stem_text("the user is running")
      'the user is run'
    """
    tokens = text.split()
    result = []
    for token in tokens:
        if token in STOP_WORDS:
            result.append(token)
        else:
            result.append(stem(token))
    return " ".join(result)
