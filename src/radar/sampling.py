"""Fixed-rate sampling of job offers and the weights that correct for it."""

import hashlib

_BUCKETS = 10_000


def _bucket(offer_key: str) -> int:
    """Map an offer key to one of 10,000 buckets, the same on every run."""
    return int(hashlib.sha256(offer_key.encode("utf-8")).hexdigest(), 16) % _BUCKETS


def in_sample(offer_key: str, rate: float) -> bool:
    """Tell whether an offer belongs to the fixed sample.

    The key (e.g. "source:<id>") decides, so an offer is either always in the sample
    or never. Samples are nested: raising the rate keeps every offer already in.
    """
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"rate must be between 0 and 1, got {rate}")
    # round() stops float error from adding a bucket: 0.07 * 10_000 == 700.0000000000001
    return _bucket(offer_key) < round(rate * _BUCKETS)


def sample_weight(n_keys: int, rate: float) -> float:
    """Weight of a sampled offer: 1 / the chance that any of its n_keys keys was drawn.

    An offer listed under several addresses (cities, sources) gets one draw per
    address, so it lands in the sample more often; the weight removes that bias.
    """
    if n_keys < 1:
        raise ValueError(f"n_keys must be at least 1, got {n_keys}")
    if not 0.0 < rate <= 1.0:
        raise ValueError(f"rate must be above 0 and at most 1, got {rate}")
    return 1.0 / (1.0 - (1.0 - rate) ** n_keys)
