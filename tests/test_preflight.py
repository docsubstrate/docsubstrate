from docsubstrate.preflight import PreflightIssue, PreflightResult


def test_preflight_result_separates_errors_and_warnings() -> None:
    warning = PreflightIssue("future-context", "context unavailable", severity="warning")
    error = PreflightIssue("missing-reference", "reference unavailable")

    result = PreflightResult((warning,)).extend(PreflightResult((error,)))

    assert result.ok is False
    assert result.warnings == (warning,)
    assert result.errors == (error,)


def test_empty_preflight_result_is_ok() -> None:
    assert PreflightResult().ok is True


def test_generic_issue_uses_context_details_without_renderer_coordinates() -> None:
    issue = PreflightIssue(
        "unresolved-resource",
        "resource unavailable",
        details={"object_id": "object:synthetic"},
    )

    assert issue.details["object_id"] == "object:synthetic"
    assert not hasattr(issue, "page_index")
    assert not hasattr(issue, "command_index")
    assert not hasattr(issue, "feature")
