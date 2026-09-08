from docsubstrate.compliance import (
    InterchangeProfile,
    ReaderConformance,
    WriterConformance,
    inspect_reader,
    validate_writer,
)
from docsubstrate.package import OpaqueExtension, PortableInstitutionalPackage
from docsubstrate.resources import IntegrityDigest, MaterializationRef, ResourceDescriptor


def _extension_resource() -> ResourceDescriptor:
    return ResourceDescriptor(
        resource_key="ext:future-1",
        resource_type="extension-payload",
        media_type="application/octet-stream",
        materialization=MaterializationRef(
            kind="embedded",
            media_type="application/octet-stream",
            length=4,
            integrity=IntegrityDigest(algorithm="sha256", value="abcd"),
        ),
    )


def _profile() -> InterchangeProfile:
    return InterchangeProfile(
        profile_id="ds-general/1",
        format_versions=frozenset({"0.1"}),
        mandatory_capabilities=frozenset({"core.graph"}),
    )


def test_writer_may_emit_supported_subset():
    package = PortableInstitutionalPackage(
        package_id="pkg:1",
        format_version="0.1",
        profile="ds-general/1",
        capabilities=frozenset({"core.graph"}),
    )
    writer = WriterConformance(
        supported_profiles={"ds-general/1": frozenset({"0.1"})},
        capabilities=frozenset({"core.graph", "extension.future"}),
    )

    assert validate_writer(package, writer=writer, profile=_profile()).ok


def test_writer_cannot_emit_undeclared_implementation_capability():
    package = PortableInstitutionalPackage(
        package_id="pkg:1",
        format_version="0.1",
        profile="ds-general/1",
        capabilities=frozenset({"core.graph", "extension.future"}),
        resources=(_extension_resource(),),
        extensions=(
            OpaqueExtension(
                extension_id="future:1",
                extension_type="future-thing",
                capability="extension.future",
                resource_key="ext:future-1",
            ),
        ),
    )
    writer = WriterConformance(
        supported_profiles={"ds-general/1": frozenset({"0.1"})},
        capabilities=frozenset({"core.graph"}),
    )

    result = validate_writer(package, writer=writer, profile=_profile())
    assert not result.ok
    assert any(issue.code == "writer-capability-unsupported" for issue in result.issues)


def test_old_reader_can_preserve_unknown_optional_extension_opaquely():
    package = PortableInstitutionalPackage(
        package_id="pkg:future",
        format_version="0.1",
        profile="ds-general/1",
        capabilities=frozenset({"core.graph", "extension.future"}),
        resources=(_extension_resource(),),
        extensions=(
            OpaqueExtension(
                extension_id="future:1",
                extension_type="future-thing",
                capability="extension.future",
                resource_key="ext:future-1",
                critical=False,
            ),
        ),
    )
    reader = ReaderConformance(
        supported_profiles={"ds-general/1": frozenset({"0.1"})},
        capabilities=frozenset({"core.graph"}),
    )

    report = inspect_reader(package, reader=reader, profile=_profile())
    assert report.readable
    assert not report.fully_interpretable
    assert report.opaque_extension_ids == frozenset({"future:1"})
    assert "extension.future" in report.unsupported_capabilities


def test_unknown_critical_extension_is_not_safely_readable():
    package = PortableInstitutionalPackage(
        package_id="pkg:future",
        format_version="0.1",
        profile="ds-general/1",
        capabilities=frozenset({"core.graph", "extension.future"}),
        resources=(_extension_resource(),),
        extensions=(
            OpaqueExtension(
                extension_id="future:critical",
                extension_type="future-critical-thing",
                capability="extension.future",
                resource_key="ext:future-1",
                critical=True,
            ),
        ),
    )
    reader = ReaderConformance(
        supported_profiles={"ds-general/1": frozenset({"0.1"})},
        capabilities=frozenset({"core.graph"}),
    )

    report = inspect_reader(package, reader=reader, profile=_profile())
    assert not report.readable
    assert any(
        issue.code == "reader-critical-extension-unsupported"
        for issue in report.preflight.issues
    )


def test_unknown_vocabulary_is_reported_without_guessing():
    from docsubstrate.package import VocabularyRef

    package = PortableInstitutionalPackage(
        package_id="pkg:legal",
        format_version="0.1",
        profile="ds-general/1",
        capabilities=frozenset({"core.graph"}),
        vocabularies=(VocabularyRef(vocabulary_id="example-regulatory/2035"),),
    )
    reader = ReaderConformance(
        supported_profiles={"ds-general/1": frozenset({"0.1"})},
        capabilities=frozenset({"core.graph"}),
        vocabularies=frozenset(),
    )

    report = inspect_reader(package, reader=reader, profile=_profile())
    assert report.readable
    assert not report.fully_interpretable
    assert report.unsupported_vocabularies == frozenset({"example-regulatory/2035"})
