from datetime import date
from vnquant.market.settlement import regulatory_sellable_date,eod_policy_earliest_exit_fill_date

def test_t2_sellable_and_eod_policy_are_distinct():
    s=[date(2026,9,d) for d in [7,8,9,10,11,14]]
    entry=s[1]
    assert regulatory_sellable_date(entry,s)==s[3]
    assert eod_policy_earliest_exit_fill_date(entry,s)==s[4]
