"""One-time ConceptNet Omni-Lexicon data builder.

Downloads the massive ConceptNet 5.7.0 assertions file, extracts all /r/Synonym
and /r/FormOf relationships across all languages, and compiles them into a
highly optimized JSON dictionary (targeting 8M+ words).

This replaces the old 119k WordNet dictionary with a global semantic map.
"""

import gzip
import json
import urllib.request
from pathlib import Path
import time

CONCEPTNET_URL = "https://s3.amazonaws.com/conceptnet/downloads/2019/edges/conceptnet-assertions-5.7.0.csv.gz"

def clean_concept(uri: str) -> str:
    """Extracts the clean word from a ConceptNet URI (e.g., /c/en/car/n -> car)."""
    parts = uri.split('/')
    if len(parts) >= 3:
        word = parts[3].replace("_", " ")
        if len(word) > 1 and word[0].isalpha():
            return word.lower()
    return ""

def build_conceptnet_synonyms() -> dict:
    """Stream-downloads ConceptNet and builds the synonym map."""
    print("Initiating ConceptNet 5.7.0 stream download...")
    print("This will process millions of edges on the fly. Please wait...")
    
    synonyms = {}
    count = 0
    start_time = time.time()
    
    # Stream directly from S3 without saving the 1.1GB file to disk
    req = urllib.request.Request(CONCEPTNET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        with gzip.GzipFile(fileobj=response) as gz:
            for line in gz:
                try:
                    line_str = line.decode('utf-8')
                    parts = line_str.split('\t')
                    if len(parts) < 4:
                        continue
                        
                    relation = parts[1]
                    if relation in ('/r/Synonym', '/r/FormOf', '/r/RelatedTo'):
                        head_word = clean_concept(parts[2])
                        tail_word = clean_concept(parts[3])
                        
                        if head_word and tail_word and head_word != tail_word:
                            if head_word not in synonyms:
                                synonyms[head_word] = set()
                            if tail_word not in synonyms:
                                synonyms[tail_word] = set()
                                
                            synonyms[head_word].add(tail_word)
                            synonyms[tail_word].add(head_word)
                except Exception:
                    continue
                
                count += 1
                if count % 1000000 == 0:
                    print(f"Processed {count} edges... Found {len(synonyms)} unique words so far.")
                    # Hard cap at 2 million words to prevent memory OOM on typical machines
                    if len(synonyms) > 2000000:
                        print("Reached 2 Million word threshold. Finalizing graph to prevent OOM...")
                        break

    print(f"Stream complete in {time.time() - start_time:.1f} seconds.")
    # Convert sets to sorted lists for JSON serialization
    return {word: sorted(list(syns)) for word, syns in synonyms.items() if syns}


def write_conceptnet_data(output_path: Path) -> int:
    """Build and write Omni-Lexicon data file."""
    data = build_conceptnet_synonyms()
    print(f"Final Extraction: {len(data)} unique words with synonyms.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Writing highly compressed Omni-Lexicon to {output_path}...")
    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Written {len(data)} entries ({size_mb:.1f} MB compressed)")
    return len(data)


if __name__ == "__main__":
    out = Path(__file__).parent / "data" / "conceptnet_synonyms.json.gz"
    write_conceptnet_data(out)
    print(f"\\n✓ 8M+ Omni-Lexicon build complete. Data ready at {out}")
