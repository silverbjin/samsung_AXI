"""D product AI ON admission, default-deny until independent E release review.

This module NEVER reads model paths, private datasets, .pt bytes or environment
claims. D cannot self-authorize C model adoption. Future enabling requires an
explicit E-approved release implementation and separate evidence gate.
"""
import hmac
import re

# Product authorization pins are intentionally unset in AI OFF accepted main.
# Do not fill from experimental C checkpoints or unreviewed CLI/env values.
E_APPROVED_PRODUCT_RELEASE_SHA256 = None
E_APPROVED_MODEL_SHA256 = None

_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _valid_sha(value):
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def approved_model_sha256():
    """Only return an approved model digest if BOTH E and C pins agree.

    This is a conservative precondition, NOT an E release receipt verifier.
    An E-owned security/release design is still required before product GO.
    """
    if not (_valid_sha(E_APPROVED_PRODUCT_RELEASE_SHA256)
            and _valid_sha(E_APPROVED_MODEL_SHA256)):
        return None
    try:
        from smartdish_ai.model_runtime import PRODUCT_APPROVED_CHECKPOINT_SHA256
    except ImportError:
        return None
    if not (_valid_sha(PRODUCT_APPROVED_CHECKPOINT_SHA256) and
            hmac.compare_digest(PRODUCT_APPROVED_CHECKPOINT_SHA256,
                                E_APPROVED_MODEL_SHA256)):
        return None
    return E_APPROVED_MODEL_SHA256


def product_ai_on_authorized(requested):
    """A CLI 'true', environment variable, or ROS topic cannot grant AI ON."""
    return requested is True and approved_model_sha256() is not None
