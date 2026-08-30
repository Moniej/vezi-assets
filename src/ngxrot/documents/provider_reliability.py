"""Provider Reliability layer (2026-08-14, AI Provider Reliability +
Decision Layer). Tracks live, mutable per-(provider, model_id) health
state in `provider_reliability_state` -- separate from `benchmark_calls`
(an append-only log) because "is this provider currently safe to call"
needs a cheap current-state lookup, not a log replay, before every call.

Deliberately does NOT sleep-and-retry in a loop. Per this session's
standing "do not repeatedly poll a blocked provider" discipline: this
module computes WHEN a retry would be legitimate (cooldown_until) and
WHETHER a provider should be attempted at all (disabled), but the actual
decision to make another attempt belongs to a separate invocation of the
orchestrating script (a future benchmark round), never a tight in-process
retry loop. `call_with_reliability_guard` makes exactly ONE call attempt;
it does not retry internally.

Two distinct failure classes, tracked separately (this is the core
insight this module encodes): a RATE LIMIT (429, "tokens per minute
exceeded", a daily quota) is TRANSIENT -- retrying later can work. A
STRUCTURAL failure (413 "request too large", 402 "payment required", a
nonexistent model_id) will NEVER succeed no matter how long you wait --
retrying it is pure waste and should disable the identity much faster.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

RATE_LIMIT_BASE_BACKOFF_S = 30.0
RATE_LIMIT_MAX_BACKOFF_S = 900.0  # 15 minutes -- a cap, not a promise the
                                  # provider will actually be ready by then
MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE = 5       # any failure class, combined
MAX_CONSECUTIVE_STRUCTURAL_FAILURES_BEFORE_DISABLE = 2  # structural failures
                                                        # repeat identically --
                                                        # disable fast


class ProviderInCooldownError(RuntimeError):
    """Raised by call_with_reliability_guard when the provider is in an
    active cooldown window -- the caller should not retry until
    cooldown_until, and must not busy-loop waiting for it."""


class ProviderDisabledError(RuntimeError):
    """Raised when the provider has been marked disabled (exceeded its
    consecutive-failure budget). Requires an explicit reset_provider()
    call to clear -- a later success does NOT auto-clear this state,
    because 'operationally unsuitable' should be a deliberate
    re-evaluation, not something that silently heals on the next lucky
    call."""


def classify_failure(error_message: str, exception_type: str) -> str:
    """'rate_limit' | 'structural' | 'other'. Pure string classification,
    no network dependency -- fully deterministic and testable offline.
    Order matters: a Groq 413 message ALSO mentions "tokens per minute"
    (it's TPM-denominated), so structural markers (413, "request too
    large", "payment_required", "model_not_found"/"does not exist") are
    checked FIRST -- an HTTP 413 means the request itself can never fit,
    regardless of timing, even though the error text references a
    per-minute quantity."""
    msg = (error_message or "").lower()
    structural_markers = ("413", "request too large", "payment_required",
                          "payment required", "model_not_found", "does not exist",
                          "model does not exist")
    if any(m in msg for m in structural_markers):
        return "structural"
    rate_limit_markers = ("429", "rate_limit", "rate limit", "resource_exhausted",
                          "quota", "tokens per minute", "too_many_tokens")
    if exception_type == "QuotaExceededError" or any(m in msg for m in rate_limit_markers):
        return "rate_limit"
    return "other"


@dataclass(frozen=True)
class HealthState:
    provider: str
    model_id: str
    state: str  # 'healthy' | 'cooldown' | 'disabled' | (no row yet -> 'healthy', known=False)
    known: bool
    consecutive_failures: int
    consecutive_structural_failures: int
    cooldown_until: str | None
    disabled_reason: str | None
    last_failure_reason: str | None
    last_failure_class: str | None


def health_state(con, provider: str, model_id: str) -> HealthState:
    row = con.execute(
        "SELECT state, consecutive_failures, consecutive_structural_failures, "
        "cooldown_until, disabled_reason, last_failure_reason, last_failure_class "
        "FROM provider_reliability_state WHERE provider=? AND model_id=?",
        (provider, model_id)).fetchone()
    if row is None:
        return HealthState(provider, model_id, "healthy", False, 0, 0, None, None, None, None)
    return HealthState(provider, model_id, row[0], True, row[1], row[2], row[3], row[4], row[5], row[6])


def can_call_now(con, provider: str, model_id: str, now: datetime | None = None) -> tuple[bool, str | None]:
    """Returns (allowed, reason_if_not). Does NOT sleep or retry -- a pure
    state check the caller uses to decide whether THIS invocation should
    attempt a call at all."""
    now = now or datetime.now()
    st = health_state(con, provider, model_id)
    if st.state == "disabled":
        return False, f"disabled: {st.disabled_reason}"
    if st.state == "cooldown" and st.cooldown_until:
        if datetime.fromisoformat(st.cooldown_until) > now:
            return False, f"in cooldown until {st.cooldown_until} ({st.last_failure_reason})"
    return True, None


def _upsert(con, provider, model_id, *, state, consecutive_failures,
           consecutive_structural_failures, last_failure_at, last_failure_reason,
           last_failure_class, cooldown_until, disabled_at, disabled_reason, updated_at):
    con.execute(
        "INSERT INTO provider_reliability_state (provider, model_id, state, "
        "consecutive_failures, consecutive_structural_failures, last_failure_at, "
        "last_failure_reason, last_failure_class, cooldown_until, disabled_at, "
        "disabled_reason, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(provider, model_id) DO UPDATE SET "
        "state=excluded.state, consecutive_failures=excluded.consecutive_failures, "
        "consecutive_structural_failures=excluded.consecutive_structural_failures, "
        "last_failure_at=excluded.last_failure_at, last_failure_reason=excluded.last_failure_reason, "
        "last_failure_class=excluded.last_failure_class, cooldown_until=excluded.cooldown_until, "
        "disabled_at=excluded.disabled_at, disabled_reason=excluded.disabled_reason, "
        "updated_at=excluded.updated_at",
        (provider, model_id, state, consecutive_failures, consecutive_structural_failures,
         last_failure_at, last_failure_reason, last_failure_class, cooldown_until,
         disabled_at, disabled_reason, updated_at))
    con.commit()


def record_failure(con, provider: str, model_id: str, error_message: str,
                   exception_type: str, *, retry_after_s: float | None = None,
                   now: datetime | None = None) -> str:
    """Records one failure, updates cooldown/disable state, returns the
    resulting state ('cooldown' | 'disabled'). retry_after_s, when the
    provider supplied one (e.g. QuotaExceededError.retry_delay_seconds or
    an HTTP Retry-After header), is honored over the computed exponential
    backoff -- the provider's own stated delay is better information than
    our guess."""
    now = now or datetime.now()
    prior = health_state(con, provider, model_id)
    failure_class = classify_failure(error_message, exception_type)
    cf = prior.consecutive_failures + 1
    csf = prior.consecutive_structural_failures + 1 if failure_class == "structural" else 0

    if failure_class == "structural" and csf >= MAX_CONSECUTIVE_STRUCTURAL_FAILURES_BEFORE_DISABLE:
        state = "disabled"
        disabled_reason = (f"{csf} consecutive structural failures -- this request shape "
                          f"cannot succeed regardless of timing (last: {error_message[:200]})")
        disabled_at, cooldown_until = now.isoformat(), None
    elif cf >= MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE:
        state = "disabled"
        disabled_reason = f"{cf} consecutive failures (any class) -- exceeded max retry budget"
        disabled_at, cooldown_until = now.isoformat(), None
    else:
        state = "cooldown"
        disabled_reason, disabled_at = None, None
        if retry_after_s is not None:
            backoff = max(retry_after_s, 0.0)
        else:
            backoff = min(RATE_LIMIT_BASE_BACKOFF_S * (2 ** (cf - 1)), RATE_LIMIT_MAX_BACKOFF_S)
        cooldown_until = (now + timedelta(seconds=backoff)).isoformat()

    _upsert(con, provider, model_id, state=state, consecutive_failures=cf,
           consecutive_structural_failures=csf, last_failure_at=now.isoformat(),
           last_failure_reason=error_message[:500], last_failure_class=failure_class,
           cooldown_until=cooldown_until, disabled_at=disabled_at,
           disabled_reason=disabled_reason, updated_at=now.isoformat())
    return state


def record_success(con, provider: str, model_id: str, now: datetime | None = None) -> str:
    """A success resets the failure counters and clears cooldown, but
    deliberately does NOT clear a 'disabled' state -- see
    ProviderDisabledError's docstring. Returns the resulting state."""
    now = now or datetime.now()
    prior = health_state(con, provider, model_id)
    if prior.state == "disabled":
        return "disabled"
    _upsert(con, provider, model_id, state="healthy", consecutive_failures=0,
           consecutive_structural_failures=0, last_failure_at=None, last_failure_reason=None,
           last_failure_class=None, cooldown_until=None, disabled_at=None, disabled_reason=None,
           updated_at=now.isoformat())
    return "healthy"


def reset_provider(con, provider: str, model_id: str, reason: str, now: datetime | None = None) -> None:
    """Explicit manual reset out of 'disabled' -- e.g. after confirming a
    Cerebras 402 was resolved by enabling billing, or after upgrading a
    Groq account tier. Requires a stated reason (recorded, not silently
    cleared) so the reset itself is auditable."""
    now = now or datetime.now()
    _upsert(con, provider, model_id, state="healthy", consecutive_failures=0,
           consecutive_structural_failures=0, last_failure_at=now.isoformat(),
           last_failure_reason=f"MANUAL RESET: {reason}", last_failure_class=None,
           cooldown_until=None, disabled_at=None, disabled_reason=None, updated_at=now.isoformat())


def retry_budget_remaining(con, provider: str, model_id: str) -> int:
    """How many more consecutive failures this identity can absorb before
    auto-disabling (any-class budget). Purely informational -- does not
    gate calls itself; can_call_now() does that via the 'disabled' state."""
    st = health_state(con, provider, model_id)
    if st.state == "disabled":
        return 0
    return max(MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE - st.consecutive_failures, 0)


def call_with_reliability_guard(con, call_fn, *, provider: str, model_id: str):
    """Makes EXACTLY ONE call attempt (never an internal retry loop).
    Checks can_call_now() first and raises ProviderInCooldownError /
    ProviderDisabledError without attempting the call if not allowed.
    On success, records it. On failure, records it (with retry_after_s
    read off the exception if present) and re-raises the original
    exception unchanged."""
    ok, reason = can_call_now(con, provider, model_id)
    if not ok:
        if reason and reason.startswith("disabled"):
            raise ProviderDisabledError(reason)
        raise ProviderInCooldownError(reason)
    try:
        result = call_fn()
    except Exception as e:
        retry_after = getattr(e, "retry_delay_seconds", None)
        record_failure(con, provider, model_id, str(e), type(e).__name__, retry_after_s=retry_after)
        raise
    record_success(con, provider, model_id)
    return result
