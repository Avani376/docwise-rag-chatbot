"""Retrieval benchmark for the included demo PDF or PDFs in a directory.

Run: python evaluate.py [pdf-directory] [--threshold 0.39]
Reports retrieval evidence coverage for answerable questions and abstention on
unanswerable questions. It deliberately does not claim to score LLM answer quality.
"""
from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path

# Keep benchmark indexing isolated from the app's persistent document library.
_evaluation_data = tempfile.TemporaryDirectory(prefix="docwise-eval-")
os.environ["VECTOR_DB_PATH"] = str(Path(_evaluation_data.name) / "vectors.sqlite3")

from rag import _extractive_answer, add_pdf, retrieve

BASE = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_directory", nargs="?", default=str(BASE / "documents"))
    parser.add_argument("--threshold", type=float, default=0.39)
    args = parser.parse_args()
    pdfs = list(Path(args.pdf_directory).glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {args.pdf_directory}")
    for pdf in pdfs:
        add_pdf(pdf.read_bytes(), pdf.name)
    cases = list(csv.DictReader((BASE / "evaluation" / "questions.csv").open(encoding="utf-8", newline="")))
    answerable = threshold_abstained = output_abstained = correct_retrieval = 0
    print(f"Indexed {len(pdfs)} PDF(s); evaluating {len(cases)} questions (threshold={args.threshold:.2f})")
    for case in cases:
        hits = retrieve(case["question"], top_k=5)
        confident = [h for h in hits if h["score"] >= args.threshold]
        expected = case["expected_terms"].casefold()
        context = " ".join(h["text"] for h in confident).casefold()
        answer = _extractive_answer(case["question"], confident) if confident else "I couldn't find this information in the indexed documents."
        if case["answerable"] == "true":
            answerable += 1
            passed = bool(confident) and expected in context
            correct_retrieval += passed
            label = "PASS" if passed else "MISS"
        else:
            threshold_abstained += not confident
            abstains = "couldn't find" in answer.casefold()
            output_abstained += abstains
            passed = abstains
            correct_retrieval += passed
            label = "ABSTAIN" if passed else "SHOULD ABSTAIN"
        score = hits[0]["score"] if hits else 0
        print(f"{case['id']:>2} {label:<14} top={score:.3f}  {case['question']}")
    total = len(cases)
    print(f"\nRetrieval evidence coverage: {sum(1 for c in cases if c['answerable']=='true' and any(c['expected_terms'].casefold() in h['text'].casefold() for h in retrieve(c['question']) if h['score'] >= args.threshold))}/{answerable}")
    unanswerable_count = len(cases) - answerable
    print(f"Similarity threshold abstentions: {threshold_abstained}/{unanswerable_count}")
    print(f"Local answer abstentions: {output_abstained}/{unanswerable_count}")
    print(f"Combined retrieval and abstention pass rate: {correct_retrieval}/{total} ({correct_retrieval/total:.0%})")
    print("This measures retrieval evidence and local extractive abstention; review generated answers against the PDFs for real use.")


if __name__ == "__main__":
    main()
