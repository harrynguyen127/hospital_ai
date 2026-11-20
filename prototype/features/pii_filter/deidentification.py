"""Explicit policy decisions and one-pass original-source redaction; no aliases."""

from features.pii_filter.aggregation import EntityGroup
from features.pii_filter.normalization import build_view
from features.pii_filter.schema import (
    EntityType, PolicyAction, ReasonCode, ReplacementDecision, SourceSpan,
    TextInput, require_tuple,
)


POLICY_VERSION = "text-pii-redaction/1.0"
REPLACEMENT = "[PII]"
REDACT_TYPES = frozenset({
    EntityType.PERSON, EntityType.PHONE, EntityType.EMAIL, EntityType.NATIONAL_ID,
    EntityType.PASSPORT, EntityType.HEALTH_INSURANCE_ID, EntityType.PATIENT_ID,
    EntityType.ENCOUNTER_ID, EntityType.DATE_OF_BIRTH, EntityType.ADDRESS,
    EntityType.GEO_COORDINATE, EntityType.ACCOUNT_ID, EntityType.FINANCIAL_ID,
    EntityType.CONTACT_URL,
})


def plan_redactions(source: TextInput, groups: tuple[EntityGroup, ...]) -> tuple[ReplacementDecision, ...]:
    require_tuple(groups, EntityGroup)
    view = build_view(source)
    for group in groups:
        group.validate_for(source, view)
    decisions = []
    for group in sorted(groups, key=lambda item: (item.span.start, item.span.end)):
        reasons = group.reason_codes
        if set(group.entity_types) <= REDACT_TYPES and ReasonCode.AMBIGUOUS_ENTITY not in reasons:
            action = PolicyAction.REDACT
        else:
            action = PolicyAction.REVIEW
            reasons = tuple(dict.fromkeys((*reasons, ReasonCode.AMBIGUOUS_ENTITY)))
        decisions.append(ReplacementDecision(
            source=source, span=group.span, action=action,
            policy_version=POLICY_VERSION, reason_codes=reasons,
        ))
    return tuple(decisions)


def render(source: TextInput, decisions: tuple[ReplacementDecision, ...]) -> str:
    """Preserve every source character outside REDACT spans exactly.

    REVIEW spans remain visible in the local review draft. Overlapping equal
    actions may merge; different actions fail instead of guessing precedence.
    """
    require_tuple(decisions, ReplacementDecision)
    view = build_view(source)
    for decision in decisions:
        decision.validate_for(source)
        if decision.policy_version != POLICY_VERSION:
            raise ValueError("unsupported redaction policy version")
        if decision.action is PolicyAction.PSEUDONYMIZE:
            raise ValueError("pseudonymization is not implemented")
        if view.expand_span(decision.span) != decision.span:
            raise ValueError("replacement span splits a normalization cluster")
    merged = []
    for decision in sorted(decisions, key=lambda item: (item.span.start, item.span.end, item.action.value)):
        if merged and decision.span.start < merged[-1][0].end:
            previous, action = merged[-1]
            if decision.action is not action:
                raise ValueError("contradictory overlapping replacement decisions")
            merged[-1] = (SourceSpan(start=previous.start, end=max(previous.end, decision.span.end)), action)
        else:
            merged.append((decision.span, decision.action))
    chunks = []
    cursor = 0
    for span, action in merged:
        if action is PolicyAction.REDACT:
            chunks.extend((source.text[cursor:span.start], REPLACEMENT))
            cursor = span.end
    chunks.append(source.text[cursor:])
    return "".join(chunks)
