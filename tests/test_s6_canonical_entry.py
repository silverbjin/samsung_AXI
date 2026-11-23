"""The single official S6 document must name one active executable."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_single_official_entrypoint_document_contract():
    doc=(ROOT/'docs/S6_OFFICIAL_OWNER_ENTRY_KO.md').read_text()
    assert "ENTRY_SHA='6fc1ac685858cb075e56514e03f72ad3a504fd87'" in doc
    assert "9d402a991d1ee0a1c46027abe91a55266b69d9bd" in doc
    assert 'samsungaxi_s6_wslg_reaccept_once.sh' in doc
    assert 'YES-S5-LIVE-GOALS' in doc
    assert 'S6_WSLG_PREFLIGHT_PASS_NO_GOAL' in doc
    assert 'samsungaxi_s6_wsl2_l3_once.sh' in doc # historic only
def test_old_guides_redirect_instead_of_advertising_old_command():
    for path in ('docs/S6_WSL2_L3_OWNER_GUIDE_KO.md','docs/S6_WSLG_GUI_REACCEPT_GUIDE_KO.md'):
        txt=(ROOT/path).read_text()
        assert 'S6_OFFICIAL_OWNER_ENTRY_KO.md' in txt
        assert 'curl -fL' not in txt  # no conflicting old shell block
def test_main_readme_has_single_start():
    readme=(ROOT/'README.md').read_text()
    assert 'docs/S6_OFFICIAL_OWNER_ENTRY_KO.md' in readme.splitlines()[2]
