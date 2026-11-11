"""Security controls for authorization scope validation.

Nothing in this package performs network requests.  The validator is a
fail-closed policy engine intended to be called before any future scanner.
"""

from security.scope_validator import AccessDecision, ScopeValidator

__all__ = ["AccessDecision", "ScopeValidator"]
