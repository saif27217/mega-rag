# Mega-RAG — Cross-Collection Diagnostic Synthesizer

A RAG (Retrieval Augmented Generation) pipeline built on Qdrant Cloud for clinical biochemistry and internal medicine queries. Queries multiple specialized knowledge collections simultaneously and synthesizes answers with PubMed literature support.

## Architecture

```
User Query → Nomic Embedding → Qdrant Search (multiple collections) → LLM Synthesis → Answer + Citations
                                                              ↓
                                                      PubMed Abstracts
                                                              ↓
                                                      Auto-ingest to updates-v2
```

## Collections

| Collection | Points | Description | Use Case |
|---|---|---|---|
| `biochem-v1` | 26,303 | Biochemistry textbook — analytes, enzymes, pathophysiology | Lab values, biomarkers, clinical chemistry |
| `harrison-22nd` | 39,460 | Harrison's Principles of Internal Medicine, 22nd edition | Diseases, diagnosis, treatment protocols |
| `sports-medicine` | 20,416 | Sports medicine & nutrition textbooks | Exercise physiology, athletic performance |
| `vdc` | 135,642 | Vijaya Diagnostic Centre SOPs & reference materials | Lab procedures, test menus, SOPs |
| `updates-v1` | Dynamic | Living collection — new findings, gap analyses, audit flags | Recent discoveries not yet in textbooks |
| `updates-v2` | Dynamic | PubMed literature auto-ingested from mega-rag queries | Live research paper abstracts |

## Scripts

### `mega-rag` — Cross-Collection Synthesizer
Queries multiple RAG collections + PubMed and generates a combined report.

```bash
# Smart mode — auto-selects 2-4 relevant collections
mega-rag "How to interpret iron studies"

# Fast mode — picks the single best collection
mega-rag --fast "IGF-1 stability in blood samples"

# All mode — queries all 6 collections + PubMed
mega-rag --all "Heart risk stratification biomarkers"
```

### `rag` — Single Collection Query Engine
Direct semantic search against one Qdrant collection.

```bash
# Quick query
rag --collection biochem-v1 "creatine kinase normal values"

# JSON output for scripting
rag --collection harrison-22nd --json "diabetes diagnostic criteria"

# Interactive chat mode
rag --collection vdc --chat

# List all collections
rag --list
```

### `rag-ingest-updates` — Add Entries to Living Collections
Append-only ingestion into `updates-v1` or `updates-v2`.

```bash
# Single entry
rag-ingest-updates --title "New finding" \
  --content "Content here..." \
  --source "PMID: 12345678" \
  --tag "literature"

# Batch from JSON file
rag-ingest-updates --file findings.json --collection updates-v2
```

### `rag-verification` — Claim Verifier
Checks content claims against multiple RAG collections + PubMed with confidence badges.

```bash
# Single claim verification
rag-verification "Creatine monohydrate improves athletic performance"

# Batch from file
rag-verification --file outline.txt

# Interactive mode
rag-verification --interactive

# Force specific collection
rag-verification --collection biochem-v1 "HbA1c > 6.5% = diabetes"
```

### `research-apis.py` — Free Research Paper APIs
Access PubMed, OpenAlex, Semantic Scholar, and Crossref programmatically.

```bash
# PubMed with abstracts
python3 research-apis.py pubmed --query "iron deficiency anemia" --limit 5 --abstract

# OpenAlex search
python3 research-apis.py openalex --query "clinical biochemistry" --limit 5

# Semantic Scholar
python3 research-apis.py semanticscholar --query "sports medicine biomarkers" --limit 5

# Crossref DOI lookup
python3 research-apis.py crossref --doi "10.1038/nature12373"
```

## Setup

### Prerequisites
- Python 3.11+ with venv
- Qdrant Cloud account (free tier available)
- Nomic Atlas account (free tier available)
- OpenRouter API key (for LLM responses)

### Install Dependencies

```bash
cd ~/.hermes
python3 -m venv rag-env
source rag-env/bin/activate
pip install qdrant-client nomic requests
```

### Configure Environment

Create `~/.hermes/.env` with:

```bash
QDRANT_URL=https://your-instance.europe-west6-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
NOMIC_API_KEY=your_nomic_api_key
OPENROUTER_API_KEY=sk-or-your_openrouter_key
```

The scripts auto-read credentials from `~/.hermes/.env` or environment variables.

### Add to PATH

```bash
ln -sf ~/.hermes/bin/mega-rag /usr/local/bin/mega-rag
ln -sf ~/.hermes/bin/rag /usr/local/bin/rag
ln -sf ~/.hermes/bin/rag-ingest-updates /usr/local/bin/rag-ingest-updates
ln -sf ~/.hermes/bin/rag-verification /usr/local/bin/rag-verification
```

## Output

Reports are saved to `~/.hermes/output/mega-rag/` with timestamped filenames:
```
mega-rag_20260526_060143.md
```

Verification reports go to `~/.hermes/output/rag-verification/`.

## Cost

- **Nomic embedding**: Free tier (100K embeddings/month)
- **Qdrant Cloud**: Free tier (5M vectors, 500MB storage)
- **LLM responses**: ~$0.0003 per query (DeepSeek V4 Flash via OpenRouter)
- **PubMed/Crossref/OpenAlex**: Completely free, no API keys required
