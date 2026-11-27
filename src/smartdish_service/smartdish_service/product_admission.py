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

# Owner authorizes ONE private model for internal Gazebo integration ONLY.
# Not commercial distribution, independent safety or performance certification.
E_OWNER_GAZEBO_MODEL_SHA256 = "6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c"
E_OWNER_GAZEBO_SCOPE = "WSL2_GAZEBO_MANUAL_STAFF_CONFIRMATION_ONLY"

_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _valid_sha(value):
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def approved_model_sha256(*, owner_gazebo_integration=False):
    """Only return an approved model digest if BOTH E and C pins agree.

    This is a conservative precondition, NOT an E release receipt verifier.
    An E-owned security/release design is still required before product GO.
    """
    if owner_gazebo_integration is True:
        try:
            from smartdish_ai.model_runtime import (
                OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256,
            )
        except ImportError:
            return None
        if (not _valid_sha(E_OWNER_GAZEBO_MODEL_SHA256)
                or not hmac.compare_digest(
                    E_OWNER_GAZEBO_MODEL_SHA256,
                    OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256)):
            return None
        return E_OWNER_GAZEBO_MODEL_SHA256
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


def product_ai_on_authorized(requested, *, owner_gazebo_integration=False):
    """Only explicit Owner Gazebo opt-in OR future independent product release."""
    return (requested is True and
            approved_model_sha256(
                owner_gazebo_integration=owner_gazebo_integration) is not None)
