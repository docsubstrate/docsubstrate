from __future__ import annotations

import pytest

from docsubstrate.resource_catalog import ResourceCatalog
from docsubstrate.resources import MaterializationRef, ResourceDescriptor, ResourceRequirement


def test_catalog_reports_unresolved_required_resource() -> None:
    catalog = ResourceCatalog()

    result = catalog.validate_requirements(
        (ResourceRequirement("vocabulary:example", "interpretation"),),
        context={"object_id": "object:synthetic", "slot": "vocabulary"},
    )

    assert not result.ok
    assert result.errors[0].code == "unresolved-resource"
    assert result.errors[0].details == {
        "object_id": "object:synthetic",
        "purpose": "interpretation",
        "slot": "vocabulary",
    }


def test_optional_resource_may_remain_unresolved() -> None:
    catalog = ResourceCatalog()

    result = catalog.validate_requirements(
        (ResourceRequirement("index:preview", "discovery", required=False),)
    )

    assert result.ok


def test_resource_key_cannot_silently_rebind_to_different_materialization() -> None:
    catalog = ResourceCatalog()
    catalog.add(
        ResourceDescriptor(
            resource_key="schema:record",
            resource_type="schema",
            materialization=MaterializationRef(kind="external", locator="schema-v1.json"),
        )
    )

    with pytest.raises(ValueError, match="resource key collision"):
        catalog.add(
            ResourceDescriptor(
                resource_key="schema:record",
                resource_type="schema",
                materialization=MaterializationRef(
                    kind="external", locator="schema-v2.json"
                ),
            )
        )
