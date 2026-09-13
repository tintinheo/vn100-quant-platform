from __future__ import annotations
import pandas as pd
from .models import AdjustmentAnomaly

def detect_adjustment_factor_jumps(symbol: str, raw_close: pd.Series, adjusted_close: pd.Series,
                                   dates: pd.Series, min_jump: float = 0.005) -> list[AdjustmentAnomaly]:
    """Detect potential adjustment events; NEVER infers legal action type.
    Official VSDC/HOSE/issuer disclosure must supply action_type.
    """
    factor=adjusted_close.astype(float)/raw_close.astype(float)
    ratio=factor/factor.shift(1)
    out=[]
    for i,r in ratio.items():
        if pd.notna(r) and abs(float(r)-1.0)>=min_jump:
            out.append(AdjustmentAnomaly(symbol, pd.Timestamp(dates.loc[i]).date(), float(r)))
    return out
