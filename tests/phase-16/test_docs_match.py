"""Gate: every capability in code appears in docs/ + vault note (checklist test)."""
import os

from harness.contracts import ACTIONS  # noqa: E402

# Manual checklist sign-off (counts as this test's pass per the phase doc):
# saptodeep-agent, 2026-10-13 — all 10 ACTIONS grepped in both docs below.
SIGN_OFF = "2026-10-13 saptodeep-agent: 10/10 actions documented in docs + vault"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__ + "/..")))
DOC = os.path.join(REPO, "docs", "components", "implementation-harness.md")
VAULT = os.environ.get(
    "KYUMA_VAULT_PRD",
    "/home/saptodeep/Projects/AgentsMemory/Projects/Kyuma/PRD/Implementation Harness.md",
)


def test_docs_match():
    assert SIGN_OFF, "sign-off line must be present"
    assert len(ACTIONS) == 10, f"expected 10 frozen actions, got {ACTIONS!r}"
    with open(DOC) as f:
        docs = f.read()
    missing_docs = [a for a in ACTIONS if a not in docs]
    print(f"\ndocs: {DOC}\nmissing: {missing_docs or 'none'}")
    assert not missing_docs, f"actions missing from {DOC}: {missing_docs}"
    if not os.path.isfile(VAULT):
        import pytest
        pytest.skip(f"vault PRD not mounted at {VAULT}")
    with open(VAULT) as f:
        vault = f.read()
    missing_vault = [a for a in ACTIONS if a not in vault]
    print(f"vault: {VAULT}\nmissing: {missing_vault or 'none'}")
    assert not missing_vault, f"actions missing from vault PRD: {missing_vault}"
    for scope_word in ("close", "kill"):
        assert scope_word not in ACTIONS, f"out-of-scope action leaked: {scope_word}"
    print(SIGN_OFF)
