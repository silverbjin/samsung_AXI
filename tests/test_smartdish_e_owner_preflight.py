"""No-private-file Owner checkpoint preflight assertions."""
import hashlib
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"scripts/smartdish_e_owner_model_preflight.py"
spec=importlib.util.spec_from_file_location("owner_preflight",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_nonexistent_and_symlink_block(tmp_path):
    with pytest.raises(ValueError,match="E_OWNER_MODEL_NOT_REGULAR_FILE"):
        m.audit_model_file(tmp_path/"missing.pt")
    real=tmp_path/"underlying.pt";real.write_bytes(b"not-real")
    link=tmp_path/"symlink.pt";link.symlink_to(real)
    with pytest.raises(ValueError,match="E_OWNER_MODEL_NOT_REGULAR_FILE"):
        m.audit_model_file(link)

def test_wrong_sha_blocks_any_nonempty_fake(tmp_path):
    raw=tmp_path/"fake.pt";raw.write_bytes(b"synthetic test bytes only")
    with pytest.raises(PermissionError,match="E_OWNER_CHECKPOINT_SHA_MISMATCH"):
        m.audit_model_file(raw)

def test_exact_sha_fixture_proves_logic_without_real_weights(tmp_path,monkeypatch):
    raw=tmp_path/"mock.pt";contents=b"MOCK_ONLY_SAFE_STRING"
    raw.write_bytes(contents)
    monkeypatch.setattr(m,"EXPECTED_SHA",hashlib.sha256(contents).hexdigest())
    record=m.audit_model_file(raw)
    assert record["checkpoint_sha256"]==hashlib.sha256(contents).hexdigest()
    assert record["private_weights_disclosed"] is False
    assert record["model_performance_pass"] is False
    assert record["test4_opened"] is False
