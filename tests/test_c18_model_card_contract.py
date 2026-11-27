"""C18 reproducible public model-card QA; no private data or torch needed."""
from pathlib import Path

CARD = Path(__file__).resolve().parents[1] / "ai/docs/C_V1_FROZEN_RESNET18_NEGATIVE_RESULT_MODEL_CARD_KO.md"


def test_card_is_technically_final_but_explicitly_not_a_product():
    text = CARD.read_text(encoding="utf8")
    for item in (
        "C_RESEARCH_PILOT_ACCEPTED=false",
        "E_AI_ON=HOLD",
        "P3_TEST_OPEN_NOT_APPROVED",
        "NOT_OPENED / NOT_EVALUATED / NOT_AUTHORIZED",
        "Train", "Validation", "33.3%", "66.7%",
        "0.7452", "0.80", "P2", "SHA",
        "UNSTABLE", "UNKNOWN", "C20",
        "CHANGE REQUEST",
    ):
        assert item in text, item


def test_card_does_not_claim_test_performance_or_model_certification():
    text = CARD.read_text(encoding="utf8")
    assert "C_RESEARCH_PILOT_ACCEPTED=true" not in text
    assert "E_AI_ON=PASS" not in text
    assert "Test 정확도 100%" not in text
    assert "A19=AUTHORIZED" not in text
    assert "TRAINING_REPEATED" not in text
    assert "Test 원본·개별 예측은 개봉하지 않음" in text
