from __future__ import annotations
from pathlib import Path
import json, hashlib
import pandas as pd

class Warehouse:
    """Parquet + DuckDB local warehouse. Imports are lazy so hosted viewer need not install them."""
    def __init__(self, root: str | Path):
        self.root=Path(root); self.raw=self.root/"raw"; self.parquet=self.root/"parquet"
        self.raw.mkdir(parents=True,exist_ok=True); self.parquet.mkdir(parents=True,exist_ok=True)
        self.db_path=self.root/"vnquant.duckdb"
    def snapshot_payload(self, provider:str, name:str, payload:bytes)->Path:
        sha=hashlib.sha256(payload).hexdigest()
        p=self.raw/provider; p.mkdir(parents=True,exist_ok=True)
        out=p/f"{name}.{sha[:12]}.bin"; out.write_bytes(payload)
        meta={"provider":provider,"name":name,"sha256":sha}
        out.with_suffix(out.suffix+".json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
        return out
    def write_table(self, df:pd.DataFrame, name:str)->Path:
        import pyarrow as pa, pyarrow.parquet as pq
        out=self.parquet/f"{name}.parquet"
        out.parent.mkdir(parents=True,exist_ok=True)
        pq.write_table(pa.Table.from_pandas(df,preserve_index=False),out)
        return out
    def read_table(self,name:str)->pd.DataFrame:
        return pd.read_parquet(self.parquet/f"{name}.parquet")
    def write_bars(self, df:pd.DataFrame, symbol:str)->Path:
        import pyarrow as pa, pyarrow.parquet as pq
        p=self.parquet/"bars"; p.mkdir(parents=True,exist_ok=True)
        out=p/f"{symbol.upper()}.parquet"
        pq.write_table(pa.Table.from_pandas(df,preserve_index=False),out)
        return out
    def read_bars(self,symbol:str)->pd.DataFrame:
        return pd.read_parquet(self.parquet/"bars"/f"{symbol.upper()}.parquet")
    def build_duckdb_views(self):
        import duckdb
        con=duckdb.connect(str(self.db_path))
        glob=str((self.parquet/"bars"/"*.parquet").as_posix())
        if list((self.parquet/"bars").glob("*.parquet")):
            con.execute(f"CREATE OR REPLACE VIEW bars AS SELECT * FROM read_parquet('{glob}', union_by_name=true)")
        for table in ("security_master","universe_current","market_regimes","sector_scores","candidates"):
            p=self.parquet/f"{table}.parquet"
            if p.exists():
                con.execute(f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_parquet('{p.as_posix()}')")
        con.close()
