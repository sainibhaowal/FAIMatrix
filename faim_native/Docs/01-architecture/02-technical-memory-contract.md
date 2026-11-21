# FAIM query and temporal-memory contract

FAIM keeps raw evidence and graph nodes tenant-scoped.  Existing nodes with no
validity interval remain timeless; this preserves prior data and APIs.

New ingest requests may include optional ISO-8601 `valid_from` and `valid_to`
fields. `valid_to` must be later than `valid_from`. A query may include `as_of`;
when supplied, FAIM returns only nodes valid at that instant. This is evidence
validity filtering, not inferred factual supersession.

`POST /api/v1/query` accepts only `STRICT`, `RELAXED`, and `FAST`. Unknown
profiles are rejected with HTTP 422. Query metrics are calculated from the
current tenant-and-graph scoped nodes and edges, not fixed placeholder values.

Advanced retrieval enrichments remain deterministic heuristics. Their scores
are evidence-ranking signals, not a claim of autonomous reasoning or verified
semantic truth.

If a non-essential query enrichment fails, the query continues on the
canonical retrieval path and lists the affected stable feature name in
`degraded_features`; `metrics.degraded_feature_count` provides the matching
count. This preserves availability without silently representing a degraded
result as a fully enriched one.
