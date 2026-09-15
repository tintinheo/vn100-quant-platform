from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, os
import pandas as pd

from dataclasses import asdict, is_dataclass

from .models import CanonicalBar, IndexBar, RawSnapshot
from .quality import DataQualityService

class Warehouse:
    """Parquet + DuckDB local warehouse. Imports are lazy so hosted viewer need not install them."""
    def __init__(self, root: str | Path):
        self.root=Path(root); self.raw=self.root/"raw"; self.parquet=self.root/"parquet"
        self.raw.mkdir(parents=True,exist_ok=True); self.parquet.mkdir(parents=True,exist_ok=True)
        self.db_path=self.root/"vnquant.duckdb"
    def snapshot_payload(self, provider:str, name:str, payload:bytes)->Path:
        sha=hashlib.sha256(payload).hexdigest()
        p=self.raw/provider; p.mkdir(parents=True,exist_ok=True)
        out=p/f"{name}.{sha[:12]}.bin"
        # Content-addressing plus read-only permissions makes raw evidence append-only.
        # An existing digest is verified, never overwritten with different bytes.
        if out.exists() and out.read_bytes() != payload:
            raise RuntimeError("immutable raw snapshot collision")
        if not out.exists():
            out.write_bytes(payload)
        os.chmod(out, 0o444)
        meta_path=out.with_suffix(out.suffix+".json")
        if not meta_path.exists():
            meta={"provider":provider,"name":name,"sha256":sha,
                  "ingested_at":datetime.now(timezone.utc).isoformat()}
            meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
        return out

    def append_canonical_bars(self, bars: list[CanonicalBar]) -> Path:
        """Append validated observations; conflicting providers remain separate rows."""
        evaluation=DataQualityService().evaluate(bars)
        issues=list(evaluation.results)
        failures=[issue for issue in issues if issue.code == "DUPLICATE_BAR"]
        if failures:
            raise ValueError("DUPLICATE_BAR: duplicate canonical observations in batch")
        for bar in bars:
            matches=list((self.raw/bar.provider).glob(f"{bar.raw_snapshot_id}.*.bin"))
            if not matches:
                raise ValueError(f"unknown raw_snapshot_id: {bar.raw_snapshot_id}")
            metadata=json.loads(matches[0].with_suffix(matches[0].suffix+".json").read_text("utf-8"))
            expected={"payload_sha256":bar.payload_sha256,"adapter_version":bar.adapter_version,
                      "trust_tier":bar.trust_tier,"raw_price_unit":bar.raw_price_unit,
                      "price_semantics":bar.price_semantics,"source_reference":bar.source_reference}
            if any(metadata.get(key) != value for key,value in expected.items()
                   if value != "unknown"):
                raise ValueError(f"canonical lineage does not match raw snapshot: {bar.raw_snapshot_id}")
            if bar.request_parameters != "{}" and metadata.get("request_parameters") != json.loads(bar.request_parameters):
                raise ValueError(f"canonical request metadata does not match raw snapshot: {bar.raw_snapshot_id}")
        table=self.parquet/"canonical_bars.parquet"
        incoming=pd.DataFrame([{**_record_dict(bar), "canonical_revision": evaluation.canonical_revision}
                               for bar in bars])
        if table.exists():
            existing=pd.read_parquet(table)
            keys=["symbol","timestamp","provider"]
            overlap=incoming.merge(existing[keys],on=keys,how="inner")
            if not overlap.empty:
                raise ValueError("DUPLICATE_BAR: observation already stored")
            incoming=pd.concat([existing,incoming],ignore_index=True)
        output=self.write_table(incoming,"canonical_bars")
        self._append_table(pd.DataFrame([{
            "canonical_revision": evaluation.canonical_revision,
            "evaluation_id": evaluation.evaluation_id,
            "created_at": evaluation.checked_at,
            "row_count": len(bars), "dq_score": evaluation.score,
            "dq_status": evaluation.status.value, "actionable": evaluation.actionable,
        }]), "canonical_revisions")
        if issues:
            self._append_table(pd.DataFrame([_record_dict(issue) for issue in issues]),
                               "data_quality_results")
        return output

    def append_index_bars(self, bars: list[IndexBar]) -> Path:
        """Persist official index observations without mixing them with equities."""
        if not bars:
            raise ValueError("index bars must not be empty")
        for bar in bars:
            matches = list((self.raw/bar.provider).glob(f"{bar.raw_snapshot_id}.*.bin"))
            if not matches:
                raise ValueError(f"unknown raw_snapshot_id: {bar.raw_snapshot_id}")
            metadata = json.loads(matches[0].with_suffix(matches[0].suffix+".json").read_text("utf-8"))
            if bar.payload_sha256 != "unknown" and metadata.get("payload_sha256") != bar.payload_sha256:
                raise ValueError(f"index lineage does not match raw snapshot: {bar.raw_snapshot_id}")
        incoming = pd.DataFrame([_record_dict(bar) for bar in bars])
        table = self.parquet/"index_bars.parquet"
        if table.exists():
            existing = pd.read_parquet(table)
            overlap = incoming.merge(existing[["index_code", "timestamp", "provider"]],
                                     on=["index_code", "timestamp", "provider"], how="inner")
            if not overlap.empty:
                raise ValueError("DUPLICATE_INDEX_BAR: observation already stored")
            incoming = pd.concat([existing, incoming], ignore_index=True)
        return self.write_table(incoming, "index_bars")

    def persist_dq_evaluation(self, evaluation, *, sync_run_id: str | None = None) -> None:
        """Append an auditable DQ evaluation tied to a canonical revision/sync."""
        summary = pd.DataFrame([{
            "evaluation_id": evaluation.evaluation_id,
            "canonical_revision": evaluation.canonical_revision,
            "sync_run_id": sync_run_id, "checked_at": evaluation.checked_at,
            "score": evaluation.score, "status": evaluation.status.value,
            "confidence_capped": evaluation.confidence_capped,
            "actionable": evaluation.actionable,
        }])
        self._append_table(summary, "dq_evaluations")
        if evaluation.results:
            rows = pd.DataFrame([{**_record_dict(result), "sync_run_id": sync_run_id}
                                 for result in evaluation.results])
            self._append_table(rows, "data_quality_results")

    def persist_sync_report(self, report) -> None:
        """Append every synchronization outcome instead of retaining only latest JSON."""
        record = asdict(report) if is_dataclass(report) else dict(report)
        for key, value in tuple(record.items()):
            if isinstance(value, (dict, list, tuple)):
                record[key] = json.dumps(value, sort_keys=True)
        self._append_table(pd.DataFrame([record]), "sync_reports")

    def persist_portfolio_risk_decisions(self, decisions: pd.DataFrame) -> Path | None:
        """Append the complete accepted/resized/rejected pre-publication audit."""
        if decisions.empty:
            return None
        required = {"decision_id", "status", "binding_constraint", "configuration_version"}
        if not required.issubset(decisions.columns):
            raise ValueError(f"risk decisions missing columns: {sorted(required - set(decisions.columns))}")
        return self._append_table(decisions, "portfolio_risk_decisions")

    def write_records(self, name: str, records: list[object]) -> Path:
        """Persist one of the canonical metadata/event tables with stable columns."""
        if not records or any(not is_dataclass(record) for record in records):
            raise ValueError("records must be a non-empty list of dataclass instances")
        return self.write_table(pd.DataFrame([_record_dict(record) for record in records]),name)

    def _append_table(self, incoming: pd.DataFrame, name: str) -> Path:
        table=self.parquet/f"{name}.parquet"
        if table.exists():
            incoming=pd.concat([pd.read_parquet(table),incoming],ignore_index=True)
        return self.write_table(incoming,name)

    def store_raw_snapshot(self, snapshot: RawSnapshot) -> Path:
        """Persist a pre-built snapshot without allowing its evidence to mutate."""
        p=self.raw/snapshot.provider; p.mkdir(parents=True,exist_ok=True)
        out=p/f"{snapshot.snapshot_id}.{snapshot.payload_sha256[:12]}.bin"
        if out.exists():
            if out.read_bytes() != snapshot.payload:
                raise RuntimeError("immutable raw snapshot already exists with different payload")
            return out
        out.write_bytes(snapshot.payload); os.chmod(out,0o444)
        metadata={"snapshot_id":snapshot.snapshot_id,"provider":snapshot.provider,
                  "ingested_at":snapshot.ingested_at.isoformat(),
                  "payload_sha256":snapshot.payload_sha256,
                  "source_reference":snapshot.source_reference,
                  "request_parameters":snapshot.request_parameters,
                  "adapter_version":snapshot.adapter_version,
                  "trust_tier":snapshot.trust_tier,
                  "raw_price_unit":snapshot.raw_price_unit,
                  "price_semantics":snapshot.price_semantics}
        out.with_suffix(out.suffix+".json").write_text(
            json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
        return out
    def write_table(self, df:pd.DataFrame, name:str)->Path:
        import pyarrow as pa, pyarrow.parquet as pq
        out=self.parquet/f"{name}.parquet"
        out.parent.mkdir(parents=True,exist_ok=True)
        temporary=out.with_name(f".{out.name}.{os.getpid()}.tmp")
        pq.write_table(pa.Table.from_pandas(df,preserve_index=False),temporary)
        temporary.replace(out)
        return out
    def read_table(self,name:str)->pd.DataFrame:
        return pd.read_parquet(self.parquet/f"{name}.parquet")
    def write_bars(self, df:pd.DataFrame, symbol:str)->Path:
        import pyarrow as pa, pyarrow.parquet as pq
        p=self.parquet/"bars"; p.mkdir(parents=True,exist_ok=True)
        out=p/f"{symbol.upper()}.parquet"
        temporary=out.with_name(f".{out.name}.{os.getpid()}.tmp")
        pq.write_table(pa.Table.from_pandas(df,preserve_index=False),temporary)
        temporary.replace(out)
        return out
    def read_bars(self,symbol:str)->pd.DataFrame:
        return pd.read_parquet(self.parquet/"bars"/f"{symbol.upper()}.parquet")
    def build_duckdb_views(self):
        import duckdb
        con=duckdb.connect(str(self.db_path))
        glob=str((self.parquet/"bars"/"*.parquet").as_posix())
        if list((self.parquet/"bars").glob("*.parquet")):
            con.execute(f"CREATE OR REPLACE VIEW bars AS SELECT * FROM read_parquet('{glob}', union_by_name=true)")
        for table in ("security_master","universe_current","index_bars","market_regimes","sector_scores","candidates","portfolio_risk_decisions"):
            p=self.parquet/f"{table}.parquet"
            if p.exists():
                con.execute(f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_parquet('{p.as_posix()}')")
        con.close()


def _record_dict(record: object) -> dict:
    values=asdict(record)
    for key,value in tuple(values.items()):
        if isinstance(value, tuple): values[key]=list(value)
        elif hasattr(value,"value") and value.__class__.__module__ == "enum": values[key]=value.value
    return values
