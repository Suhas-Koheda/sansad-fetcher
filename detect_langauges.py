import regex as re
from pathlib import Path
from collections import Counter

scripts = {
    "Latin": r"\p{Latin}",
    "Devanagari": r"\p{Devanagari}",
    "Telugu": r"\p{Telugu}",
    "Tamil": r"\p{Tamil}",
    "Kannada": r"\p{Kannada}",
    "Malayalam": r"\p{Malayalam}",
    "Bengali": r"\p{Bengali}",
    "Gujarati": r"\p{Gujarati}",
    "Gurmukhi": r"\p{Gurmukhi}",
    "Oriya": r"\p{Oriya}",
}

counts = Counter()

for file in Path("corpus/raw_text").glob("**/*.txt"):
    text = file.read_text(errors="ignore")

    for script, pattern in scripts.items():
        counts[script] += len(re.findall(pattern, text))

print("\nScript distribution:")
for script, count in counts.most_common():
    print(f"{script}: {count:,}")