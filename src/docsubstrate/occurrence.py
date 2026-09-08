"""First-class record of a basis-qualified institutional occurrence.

Occurrence is a generic substrate query owner for claims or observations of
what happened, when, by whom, against which inputs, producing which outputs,
and on what source basis. An occurrence record is durable institutional truth
about the record and its basis; it is not an omniscient claim that the outside
world has been independently verified. Domain meanings remain vocabulary-defined.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

OccurrenceOutcome = Literal["succeeded", "failed", "unknown"]
OccurrenceBasis = Literal["asserted", "observed"]


@dataclass(frozen=True, slots=True)
class OccurrenceRecord:
    """Durable, basis-qualified record that an occurrence happened.

    ``basis="asserted"`` means an identified institutional source asserts that
    the occurrence happened. ``basis="observed"`` means the recording process
    directly observed the occurrence. Neither basis silently means independent
    verification; verification remains a separate fact/resource/occurrence.

    A plan, workflow state, or intended action is not an occurrence. Point-time
    events should use ``occurred_at``. ``started_at``/``ended_at`` are reserved
    for genuine interval/execution occurrences; producers must not manufacture
    intervals merely because the model supports them.
    """

    occurrence_id: str
    occurrence_type: str
    outcome: OccurrenceOutcome
    basis: OccurrenceBasis
    input_refs: Sequence[str] = field(default_factory=tuple)
    output_refs: Sequence[str] = field(default_factory=tuple)
    source_refs: Sequence[str] = field(default_factory=tuple)
    actor_ref: str | None = None
    action_ref: str | None = None
    occurred_at: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    details: Mapping[str, str | int | float | bool] = field(default_factory=dict)
    vocabulary_id: str | None = None
