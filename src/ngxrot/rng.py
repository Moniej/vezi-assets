"""Seed registry support: one construction path for every RNG in the system.

Any stochastic component (bootstrap, Monte Carlo, placebo shuffles) must get
its generator from make_rng(config) — never from an ad-hoc np.random call —
so the algorithm, seed, and iteration count land in the immutable experiment
record and a rerun with the same config reproduces bit-identical results.
"""

from __future__ import annotations

import numpy as np

_ALGORITHMS = {
    "PCG64": np.random.PCG64,
    "PCG64DXSM": np.random.PCG64DXSM,
    "Philox": np.random.Philox,
    "MT19937": np.random.MT19937,
}


def make_rng(rng_cfg: dict) -> np.random.Generator:
    """Build the experiment's Generator from its [rng] config section."""
    algo = rng_cfg.get("algorithm", "PCG64")
    if algo not in _ALGORITHMS:
        raise ValueError(f"unknown RNG algorithm {algo!r}; allowed: {sorted(_ALGORITHMS)}")
    seed = rng_cfg.get("seed")
    if seed is None:
        raise ValueError("[rng].seed is required for any stochastic component — "
                         "unseeded experiments are not reproducible and are refused")
    return np.random.Generator(_ALGORITHMS[algo](int(seed)))


def rng_record(rng_cfg: dict) -> dict:
    """Fields persisted to the experiment registry."""
    return {
        "rng_algorithm": rng_cfg.get("algorithm", "PCG64"),
        "rng_seed": rng_cfg.get("seed"),
        "rng_iterations": rng_cfg.get("iterations", 0),
    }
