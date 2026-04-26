"""One-time WordNet data builder.

Extracts WordNet synonym data from NLTK and writes to data/wordnet_synonyms.json.gz

This script is run ONCE at build time on a development machine with NLTK installed.
The resulting data file is committed to git and shipped with FAIM source.
At runtime, FAIM has ZERO dependency on NLTK — only loads the embedded JSON.

Usage:
    python -m nltk.downloader wordnet  # First time only
    python -m lexical.wordnet_builder
"""

import gzip
import json
from pathlib import Path


def build_wordnet_synonyms() -> dict:
    """
    Extract word→synonyms mapping from NLTK WordNet.

    Includes:
    - All lemma names per synset (direct synonyms)
    - All hypernym lemmas (generalization synonyms: car → vehicle → transport)
    - All hyponym lemmas (specialization synonyms: vehicle → car, truck, bus)

    Filters out:
    - Proper nouns (capitalized)
    - Multi-word phrases that are unlikely to appear in n-grams
    - Words < 2 chars

    Returns:
        dict: mapping word (str) → list of synonyms (sorted strings)
    """
    try:
        from nltk.corpus import wordnet as wn
    except ImportError as err:
        raise RuntimeError(
            "NLTK required for WordNet build.\n"
            "Install: pip install nltk\n"
            "Then: python -m nltk.downloader wordnet"
        ) from err

    synonyms: dict = {}

    # Iterate all synsets in WordNet
    for synset in wn.all_synsets():
        # Collect all lemmas at this level
        lemmas = [lem.name().lower().replace("_", " ") for lem in synset.lemmas()]

        # Add hypernym lemmas (broader concepts)
        for hypernym in synset.hypernyms():
            lemmas.extend(
                lem.name().lower().replace("_", " ") for lem in hypernym.lemmas()
            )

        # Add hyponym lemmas (narrower concepts)
        for hyponym in synset.hyponyms():
            lemmas.extend(
                lem.name().lower().replace("_", " ") for lem in hyponym.lemmas()
            )

        # For each lemma in this synset, record all others as synonyms
        for lemma in synset.lemmas():
            word = lemma.name().lower().replace("_", " ")

            # Skip: proper nouns (would have uppercase in source), too short, non-alpha
            if not word or len(word) < 2 or not word[0].isalpha():
                continue

            # Collect other lemmas as synonyms
            others = set(
                lem
                for lem in lemmas
                if lem != word and lem.isalpha() and len(lem) > 1 and " " not in lem
            )

            if others:
                if word not in synonyms:
                    synonyms[word] = set()
                synonyms[word].update(others)

    # Convert sets to sorted lists for JSON serialization
    return {word: sorted(list(syns)) for word, syns in synonyms.items() if syns}


def write_wordnet_data(output_path: Path) -> int:
    """
    Build and write WordNet data file.

    Args:
        output_path: Path to write gzip JSON data

    Returns:
        Number of word entries written
    """
    print("Building WordNet synonym data...")
    data = build_wordnet_synonyms()
    print(f"Extracted {len(data)} unique words with synonyms")

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write compressed JSON
    print(f"Writing to {output_path}...")
    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    # Check file size
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Written {len(data)} entries ({size_mb:.1f} MB compressed)")

    return len(data)


if __name__ == "__main__":
    out = Path(__file__).parent / "data" / "wordnet_synonyms.json.gz"
    n = write_wordnet_data(out)
    print(f"\n✓ WordNet build complete. Data ready at {out}")
