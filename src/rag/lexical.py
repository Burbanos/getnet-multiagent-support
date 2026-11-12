"""Lexical search (BM25 + NFKD accent folding) without regex dependencies."""
from __future__ import annotations

import math
import unicodedata
from collections import Counter
from collections.abc import Sequence


def fold(text: str) -> str:
    """Fold accents with NFKD decomposition, lowercase, and replace non-alnum chars with spaces."""
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    ).lower()
    return "".join(ch if ch.isalnum() else " " for ch in stripped)


def tokenize(text: str) -> list[str]:
    """Fold text and split on whitespace."""
    return fold(text).split()


class BM25Index:
    """Okapi BM25 lexical index over a list of documents."""

    def __init__(self, documents: Sequence[str], k1: float = 1.2, b: float = 0.75) -> None:
        self.k1 = float(k1)
        self.b = float(b)
        self.num_docs = len(documents)
        self._tfs: list[Counter[str]] = []
        self._doc_lens: list[int] = []
        df: Counter[str] = Counter()

        for doc in documents:
            toks = tokenize(doc)
            tf = Counter(toks)
            self._tfs.append(tf)
            self._doc_lens.append(len(toks))
            for term in tf:
                df[term] += 1

        self.avgdl: float = (
            math.fsum(self._doc_lens) / self.num_docs if self.num_docs > 0 else 0.0
        )
        self._idf: dict[str, float] = {
            term: math.log(1.0 + (self.num_docs - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def scores(self, query: str) -> list[float]:
        """Compute BM25 score for every document in corpus order."""
        if self.num_docs == 0:
            return []
        if self.avgdl <= 0.0:
            return [0.0] * self.num_docs

        q_terms = list(dict.fromkeys(tokenize(query)))
        if not q_terms:
            return [0.0] * self.num_docs

        out: list[float] = []
        for idx in range(self.num_docs):
            tf_doc = self._tfs[idx]
            dl = self._doc_lens[idx]
            if dl == 0:
                out.append(0.0)
                continue
            denom_base = self.k1 * (1.0 - self.b + self.b * (dl / self.avgdl))
            contribs: list[float] = []
            for term in q_terms:
                tf = tf_doc.get(term, 0)
                if tf <= 0:
                    continue
                idf = self._idf[term]
                contribs.append(idf * tf * (self.k1 + 1.0) / (tf + denom_base))
            out.append(math.fsum(contribs))
        return out

    def top(self, query: str, k: int) -> list[tuple[int, float]]:
        """Return up to k (doc_index, score) pairs with score > 0 sorted by (-score, doc_index)."""
        if k <= 0 or self.num_docs == 0:
            return []
        doc_scores = self.scores(query)
        scored = [(idx, s) for idx, s in enumerate(doc_scores) if s > 0.0]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:k]
