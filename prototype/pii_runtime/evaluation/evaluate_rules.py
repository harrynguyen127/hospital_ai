"""Exposed development comparison only; no blind evaluation or model benchmark.

The legacy tuple API exposes no findings. Its substitution spans are obtained
by replaying its actual regex substitutions with a character-origin trace and
asserting exact equality to mask(). No approximate alignment is used.
"""

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import re

from features.pii_filter import pii
from features.pii_filter.engine import process_text
from features.pii_filter.schema import EntityType, PolicyAction, SourceSpan
from pii_runtime.evaluation.generate_synthetic import GENERATOR_VERSION, generate_development


@dataclass(frozen=True, slots=True)
class Prediction:
    span: SourceSpan
    entity_type: EntityType


def trace_legacy(text: str) -> tuple[str, tuple[Prediction, ...], frozenset[int]]:
    current = text
    origins = tuple(range(len(text)))
    predictions = []
    removed = set()
    count = 0
    kinds = (EntityType.PHONE, EntityType.NATIONAL_ID, EntityType.PERSON)
    if len(pii.PII) != len(kinds):
        raise ValueError("legacy trace requires review after prototype pattern changes")
    for (pattern, replacement), kind in zip(pii.PII, kinds):
        chunks, mapping = [], []
        cursor = 0
        for match in pattern.finditer(current):
            count += 1
            chunks.append(current[cursor:match.start()])
            mapping.extend(origins[cursor:match.start()])
            if replacement is None:
                targets = tuple((match.start() + item.start(), match.start() + item.end())
                                for item in re.finditer(re.escape(match.group(2)), match.group(0)))
                placeholder = "[TÊN]"
            else:
                targets = (match.span(),)
                placeholder = replacement
            local = match.start()
            for start, end in targets:
                chunks.extend((current[local:start], placeholder))
                mapping.extend(origins[local:start])
                mapping.extend([None] * len(placeholder))
                indices = sorted({item for item in origins[start:end] if item is not None})
                removed.update(indices)
                if indices:
                    first = previous = indices[0]
                    for index in indices[1:]:
                        if index != previous + 1:
                            predictions.append(Prediction(SourceSpan(start=first, end=previous + 1), kind))
                            first = index
                        previous = index
                    predictions.append(Prediction(SourceSpan(start=first, end=previous + 1), kind))
                local = end
            chunks.append(current[local:match.end()])
            mapping.extend(origins[local:match.end()])
            cursor = match.end()
        chunks.append(current[cursor:])
        mapping.extend(origins[cursor:])
        current, origins = "".join(chunks), tuple(mapping)
    if (current, count) != pii.mask(text):
        raise ValueError("legacy substitution trace differs from the unchanged prototype")
    return current, tuple(predictions), frozenset(removed)


def _overlap_count(predicted: tuple[Prediction, ...], gold: tuple) -> int:
    matched = {}

    def assign(index, visited):
        prediction = predicted[index]
        for target, annotation in enumerate(gold):
            if target in visited or prediction.entity_type is not annotation.entity_type:
                continue
            if prediction.span.start >= annotation.span.end or annotation.span.start >= prediction.span.end:
                continue
            visited.add(target)
            if target not in matched or assign(matched[target], visited):
                matched[target] = index
                return True
        return False

    return sum(assign(index, set()) for index in range(len(predicted)))


def _scores(tp: int, predicted: int, gold: int) -> dict:
    return {
        "tp": tp, "fp": predicted - tp, "fn": gold - tp,
        "precision": tp / predicted if predicted else None,
        "recall": tp / gold if gold else None,
        "f1": 2 * tp / (predicted + gold) if predicted + gold else None,
    }


def evaluate_development(seed: int = 17) -> dict:
    records = generate_development(seed)
    summaries = {}
    for system in ("new_rules", "team_regex"):
        counts = {kind: Counter() for kind in EntityType}
        protected_count = overredacted = failed = review = 0
        for record in records:
            if system == "new_rules":
                result = process_text(record.source)
                if result.external_egress_authorized:
                    raise ValueError("development engine unexpectedly authorized outbound use")
                predicted = tuple(Prediction(item.span, item.entity_type)
                                  for report in result.detector_reports for item in report.findings)
                removed = {index for decision in result.decisions if decision.action is PolicyAction.REDACT
                           for index in range(decision.span.start, decision.span.end)}
                failed += result.output_text is None
                review += result.assessment.status.value in ("review_required", "partial")
            else:
                _, predicted, removed = trace_legacy(record.source.text)
            protected = {index for annotation in record.clinical
                         for index in range(annotation.span.start, annotation.span.end)}
            protected_count += len(protected)
            overredacted += len(protected & removed)
            for kind in EntityType:
                gold = tuple(item for item in record.entities if item.entity_type is kind)
                candidates = tuple(item for item in predicted if item.entity_type is kind)
                exact = sum((Counter(item.span for item in candidates) & Counter(item.span for item in gold)).values())
                counts[kind].update(gold=len(gold), predicted=len(candidates), exact_tp=exact,
                                    overlap_tp=_overlap_count(candidates, gold))
                actions = {item.span: item.action for item in record.policies}
                for annotation in gold:
                    if actions[annotation.span] in (PolicyAction.REDACT, PolicyAction.PSEUDONYMIZE):
                        counts[kind]["redaction_required"] += 1
                        if all(index in removed for index in range(annotation.span.start, annotation.span.end)):
                            counts[kind]["fully_redacted"] += 1
        categories = {}
        for kind, count in counts.items():
            categories[kind.value] = {
                "gold": count["gold"], "predicted": count["predicted"],
                "exact": _scores(count["exact_tp"], count["predicted"], count["gold"]),
                "overlap": _scores(count["overlap_tp"], count["predicted"], count["gold"]),
                "redaction_required": count["redaction_required"],
                "fully_redacted": count["fully_redacted"],
            }
        summaries[system] = {
            "categories": categories, "protected_characters": protected_count,
            "overredacted_characters": overredacted,
            "clinical_overredaction_rate": overredacted / protected_count if protected_count else None,
            "failed_requests": failed if system == "new_rules" else None,
            "review_requests": review if system == "new_rules" else None,
        }
    return {
        "dataset": "exposed-development", "generator_version": GENERATOR_VERSION,
        "seed": seed, "records": len(records), "systems": summaries,
        "limitations": [
            "Small exposed synthetic corpus; no independent blind or production qualification.",
            "Legacy span scores describe traced substitutions, not a native findings API.",
            "Clinical character checks do not establish semantic correctness.",
            "Unsupported categories and review-policy entities remain in recognition scores.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Compare rules on exposed synthetic development data only.")
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    print(json.dumps(evaluate_development(args.seed), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
