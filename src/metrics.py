"""Explicit local scoring conventions. Replace with TA scorer when supplied."""
import re
import string
from collections import Counter


def normalized(text):
    text = str(text).lower()
    text = ''.join(c for c in text if c not in string.punctuation)
    return re.sub(r'\b(a|an|the)\b', ' ', text).split()


def f1(prediction, references):
    if not isinstance(references, list):
        references = [references]
    if not references:
        raise ValueError("references must contain at least one answer")
    p = normalized(prediction)
    def score(ref):
        r = normalized(ref)
        if not p or not r:
            return float(p == r)
        overlap = sum((Counter(p) & Counter(r)).values())
        return 2 * overlap / (len(p) + len(r)) if overlap else 0.0
    return max(score(ref) for ref in references)


def source_turns(values):
    # Real LoCoMo sometimes has "D8:6; D9:17" in one evidence string.
    return set(re.findall(r'D\d+:\d+', ' '.join(str(v) for v in values)))


def recall(predicted_turns, gold_evidence):
    gold = source_turns(gold_evidence)
    return len(set(predicted_turns) & gold) / len(gold) if gold else None


def relation_accuracy(predicted, gold):
    """Gold pairs use ordered from_turn/to_turn. Missing pairs count as incorrect."""
    if not gold:
        return None
    hits = 0
    for pair in gold:
        key = (pair["from_turn"], pair["to_turn"])
        hits += predicted.get(key) == pair["label"]
    return hits / len(gold)
