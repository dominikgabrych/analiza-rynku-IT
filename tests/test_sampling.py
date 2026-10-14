import itertools
import math

import pytest

from radar.sampling import _bucket, in_sample, sample_weight

KEYS = [f"test:{i}" for i in range(10_000)]


def test_bucket_assignment_never_changes():
    # A different hash would silently reshuffle the sample and break comparisons
    # with earlier runs.
    assert [_bucket(f"test:{i}") for i in range(5)] == [6949, 9949, 1323, 4233, 673]


def test_rate_zero_takes_nothing_and_rate_one_takes_everything():
    assert not any(in_sample(k, 0.0) for k in KEYS)
    assert all(in_sample(k, 1.0) for k in KEYS)


@pytest.mark.parametrize("rate", [0.07, 0.2, 0.5])
def test_sample_share_matches_rate(rate):
    share = sum(in_sample(k, rate) for k in KEYS) / len(KEYS)
    assert share == pytest.approx(rate, abs=0.015)


def test_samples_are_nested():
    # Raising the rate in the config must keep every offer that was already sampled.
    assert all(in_sample(k, 0.2) for k in KEYS if in_sample(k, 0.1))


def test_rate_threshold_has_no_float_error():
    # 0.07 * 10_000 == 700.0000000000001, which would let bucket 700 into a 7% sample.
    key = next(k for k in (f"test:{i}" for i in itertools.count()) if _bucket(k) == 700)
    assert not in_sample(key, 0.07)
    assert in_sample(key, 0.0701)


@pytest.mark.parametrize("rate", [-0.1, 1.5, math.nan])
def test_in_sample_rejects_invalid_rate(rate):
    with pytest.raises(ValueError):
        in_sample("test:0", rate)


def test_sample_weight_is_inverse_chance_of_being_drawn():
    assert sample_weight(1, 0.2) == pytest.approx(5.0)
    assert sample_weight(17, 0.2) == pytest.approx(1.023, abs=1e-3)
    assert sample_weight(3, 1.0) == 1.0


@pytest.mark.parametrize(("n_keys", "rate"), [(0, 0.2), (1, 0.0), (1, 1.5)])
def test_sample_weight_rejects_invalid_input(n_keys, rate):
    with pytest.raises(ValueError):
        sample_weight(n_keys, rate)


def test_weights_remove_multi_address_bias():
    # Half the offers have one address, half have 17 (e.g. remote plus many cities).
    # An offer is sampled when any of its addresses is.
    offers = [[f"single:{i}"] for i in range(5_000)]
    offers += [[f"multi:{i}:{j}" for j in range(17)] for i in range(5_000)]
    sampled = [keys for keys in offers if any(in_sample(k, 0.2) for k in keys)]
    is_multi = [len(keys) > 1 for keys in sampled]
    weights = [sample_weight(len(keys), 0.2) for keys in sampled]

    raw_share = sum(is_multi) / len(sampled)
    weighted_multi = sum(w for w, m in zip(weights, is_multi, strict=True) if m)
    weighted_share = weighted_multi / sum(weights)

    assert raw_share > 0.75  # the true share is 0.5
    assert weighted_share == pytest.approx(0.5, abs=0.03)
