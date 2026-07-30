import nltk

try:
    nltk.data.find('corpora/wordnet')
    nltk.data.find('corpora/omw-1.4')
except LookupError:
    nltk.download('wordnet')
    nltk.download('omw-1.4')

from nltk.corpus import wordnet as wn

words = set()
for lang in wn.langs():
    for synset in wn.all_synsets(lang=lang):
        for lemma in synset.lemmas(lang=lang):
            words.add(lemma.name().lower())

print(f"Total unique words across all OMW languages: {len(words)}")
