# save as scripts/gen_longchat.py and run it
from pathlib import Path

N = 100000  # number of lines; adjust up to reach ~1M tokens
out_q = Path("Data/Benchmarks/longchat_queries.txt")
out_qa = Path("Data/Benchmarks/longchat_qa.txt")

with out_q.open("w", encoding="utf8") as fq, out_qa.open("w", encoding="utf8") as fqa:
    # Seed “needles”
    needles = [
        ("What was my first startup idea?", "memory engine for AI called FAIM"),
        ("What city did I say my sister lives in?", "Berlin"),
        ("Which GPU did I mention?", "RTX 4060"),
    ]
    for q, a in needles:
        fq.write(q + "\n")
        fqa.write(f"{q}\t{a}\n")

    # Lots of filler
    for i in range(N):
        msg = f"This is synthetic conversation line number {i} about random topic {i % 17}."
        fq.write(msg + "\n")
