from datetime import date
import pytest
from vnquant.data.universe import UniverseStore, UniverseMode

def test_strict_pit_never_silently_uses_current(tmp_path):
    s=UniverseStore(tmp_path/"u.csv")
    with pytest.raises(LookupError):
        s.resolve(date(2020,1,2),current_members=["AAA"],allow_proxy=False)
    r=s.resolve(date(2020,1,2),current_members=["AAA"],allow_proxy=True)
    assert r.mode is UniverseMode.CURRENT_UNIVERSE_PROXY
    assert "NOT_TRUE_HISTORICAL_VN100" in r.warning

def test_effective_dated_resolution(tmp_path):
    s=UniverseStore(tmp_path/"u.csv")
    s.append_snapshot(["AAA","BBB"],date(2020,1,1),source="official")
    r=s.resolve(date(2020,6,1))
    assert r.mode is UniverseMode.STRICT_PIT
    assert r.symbols == ("AAA","BBB")
