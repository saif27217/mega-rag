---
name: qdrant-rag
description: "Qdrant RAG verification via Nomic embed + query_points."
version: 1.1.0
author: Lazer
tags: [qdrant, rag, embedding, nomic, verification, semantic-search]
---

# Qdrant RAG Verification

Embed queries with Nomic (768-dim) and query Qdrant via `query_points()`. Used for SOP audits, clinical verification, and semantic search across collections.

## Core pattern

```python
from qdrant_client import QdrantClient
from nomic.embed import text as nmic

qc = QdrantClient(url=os.environ['QDRANT_URL'], api_key=os.environ['QDRANT_API_KEY'])
emb = nmic([claim], model="nomic-embed-text-v1.5", task_type="search_query")
vector = emb["embeddings"][0]

# query_points().points — NOT qc.search (removed in qdrant-client 1.18)
pts = qc.query_points("collection-name", query=vector, limit=5).points
for p in pts:
    print(p.score, p.payload)
```

## Runtime

Use `~/.hermes/rag-env/bin/python3` — system python lacks `qdrant_client` and `nomic`.

```bash
source ~/.hermes/.env          # exports QDRANT_URL, QDRANT_API_KEY
/home/sak/.hermes/rag-env/bin/python3 script.py
```

## Embedding

- `task_type="search_query"` for queries, `"search_document"` for documents
- All collections are 768-dim Cosine — mismatched dims raise at upsert

## Upserting points (e.g., updates-v1)

```python
from qdrant_client.models import PointStruct
import hashlib

points = []
for f in findings:
    points.append(PointStruct(
        id=int(hashlib.md5(f['tag'].encode()).hexdigest(), 16) % (2**63),
        vector=emb["embeddings"][i],
        payload={"title": f['tag'], "evidence": f['text'][:1200], ...}
    ))

qc.upsert("updates-v1", points=points)   # max 100 per batch
```

## Verification thresholds

| Score | Action |
|---|---|
| ≥ 0.70 | Verified — keep claim |
| 0.50–0.69 | Weak — reword or drop |
| ~0 | RAG-gap — source externally, don't assert |

## Pitfalls

1. **No `qc.search()`** — use `query_points(...).points`
2. **Empty text fields** — some collections (e.g., `mega-yt`) store transcripts in `"text"` not `"chunk_text"`. Probe with `list(p.payload.keys())` if snippets are missing
3. **No `.name` on CollectionInfo** — access via returned object's attributes directly
4. **Sandbox import failure** — `nomic` only in rag-env, not `execute_code`'s Python
5. **ID overflow** — hash to int and mod by `2**63`

## Collection field map

| Collection | Text field | Notes |
|---|---|---|
| `vdc`, `biochem-v1`, `updates-v1` | `chunk_text` or `text` | SOP/clinical content |
| `mega-yt` | `text` | YouTube transcripts; may be empty in some chunks — query directly if CLI returns no snippets |
| `harrison-22nd` | `chunk_text` | Medical textbook |

## Related Skills

- **sop-auditor** — calls this for verification
- **rag-verification-workflow** — batch claim checking via `rag-verification` CLI
