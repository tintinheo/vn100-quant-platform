from __future__ import annotations
import os
from datetime import date
import pandas as pd
from .base import MarketDataProvider, CANONICAL_COLUMNS

class SSIConfigurationError(RuntimeError): pass
class SSIProviderError(RuntimeError): pass

class SSIFastConnectV3Provider(MarketDataProvider):
    """SSI FastConnect v3 market-data-only adapter.

    Security boundary: authenticates WITHOUT OTP and never imports/uses Trading.
    The official Python SDK is pinned in requirements-local.txt.
    """
    name = "ssi_fastconnect_v3"

    def __init__(self, client_id: str | None = None, api_key: str | None = None,
                 api_secret: str | None = None):
        self.client_id = client_id or os.getenv("SSI_CLIENT_ID")
        self.api_key = api_key or os.getenv("SSI_API_KEY")
        self.api_secret = api_secret or os.getenv("SSI_API_SECRET")
        missing = [k for k,v in {"SSI_CLIENT_ID":self.client_id,"SSI_API_KEY":self.api_key,
                                  "SSI_API_SECRET":self.api_secret}.items() if not v]
        if missing:
            raise SSIConfigurationError("Missing market-data credentials: " + ", ".join(missing))
        try:
            from ssi_sdk import Auth, Data, Config
        except ImportError as e:
            raise SSIConfigurationError("Install local dependencies: pip install -r requirements-local.txt") from e
        self._Auth, self._Data, self._Config = Auth, Data, Config
        self._auth = None
        self._data = None

    def __enter__(self):
        cfg = self._Config(client_id=self.client_id, api_key=self.api_key, api_secret=self.api_secret)
        self._auth = self._Auth(cfg)
        self._auth.__enter__()
        # No OTP => market-data token only.
        self._auth.authenticate()
        self._data = self._Data(self._auth)
        self._data.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        if self._data is not None:
            self._data.__exit__(None, None, None)
            self._data = None
        if self._auth is not None:
            self._auth.__exit__(None, None, None)
            self._auth = None

    def _service(self):
        if self._data is None:
            raise SSIProviderError("Provider must be used as a context manager: `with SSIFastConnectV3Provider() as p:`")
        return self._data.market_data

    def current_index_securities(self, index_code: str = "VN100") -> pd.DataFrame:
        rows = self._service().get_securities_info_by_index(index_code)
        records=[]
        for x in rows:
            symbol=str(getattr(x,"symbol","") or "").upper().strip()
            if not symbol:
                continue
            records.append({
                "symbol":symbol,
                "board":str(getattr(x,"board","") or ""),
                "index_code":index_code,
                "symbol_name_vi":getattr(x,"symbol_name_vi",None),
                "symbol_name_en":getattr(x,"symbol_name_en",None),
                "lot_size":getattr(x,"lot_size",None),
                "listed_shares":getattr(x,"listed_shares",None),
                "icb_code":str(getattr(x,"icb_code","") or ""),
                "icb_name":str(getattr(x,"icb_name","") or "UNKNOWN"),
                "first_trading_date":getattr(x,"first_trading_date",None),
                "last_trading_date":getattr(x,"last_trading_date",None),
                "provider":self.name,
            })
        out=pd.DataFrame(records)
        if out.empty:
            raise SSIProviderError(f"SSI returned no members for {index_code}")
        return out.sort_values("symbol").reset_index(drop=True)

    def current_index_members(self, index_code: str = "VN100") -> list[str]:
        return self.current_index_securities(index_code).symbol.tolist()

    def daily_history(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        svc = self._service()
        page, size, all_rows = 1, 1000, []
        while True:
            rows = svc.get_ohlc_1day_historical(
                symbol=symbol.upper(),
                from_date=f"{start:%Y/%m/%d} 00:00:00",
                to_date=f"{end:%Y/%m/%d} 23:59:59",
                page=page,
                size=size,
            )
            all_rows.extend(rows)
            if len(rows) < size:
                break
            page += 1
            if page > 100:
                raise SSIProviderError(f"Pagination guard triggered for {symbol}")
        records = []
        for r in all_rows:
            td = pd.to_datetime(getattr(r, "trading_date"), dayfirst=False, errors="coerce")
            if pd.isna(td):
                td = pd.to_datetime(getattr(r, "trading_date"), dayfirst=True, errors="raise")
            records.append({
                "symbol": symbol.upper(), "trading_date": td.date(),
                "open": float(getattr(r,"open_price")), "high": float(getattr(r,"high_price")),
                "low": float(getattr(r,"low_price")), "close": float(getattr(r,"close_price")),
                "volume": int(getattr(r,"volume")), "value": float(getattr(r,"value",0) or 0),
                "provider": self.name,
            })
        return pd.DataFrame(records, columns=CANONICAL_COLUMNS).sort_values("trading_date").reset_index(drop=True)
