#!/usr/bin/env python3
"""
Research Paper APIs — free, no-key biomedical literature access.
Sources: PubMed E-utilities, OpenAlex, Semantic Scholar, Crossref

Usage:
  python3 research-apis.py pubmed --query "biochemistry lab tests" --limit 5
  python3 research-apis.py openalex --query "clinical biochemistry diagnostics" --limit 5
  python3 research-apis.py semanticscholar --query "sports medicine biomarkers" --limit 5
  python3 research-apis.py crossref --doi "10.1038/nature12373"
"""

import json, sys, urllib.request, urllib.parse, time

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OPENALEX_BASE = "https://api.openalex.org"
S2_BASE = "https://api.semanticscholar.org/graph/v1"
CROSSREF_BASE = "https://api.crossref.org/works"


def pubmed_search(query, limit=5, with_abstract=False):
    """Search PubMed citations. Free, no key needed. 36M+ records."""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "retmax": limit,
        "retmode": "json",
        "sort": "relevance"
    })
    url = f"{PUBMED_BASE}/esearch.fcgi?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        ids = json.loads(resp.read()).get("esearchresult", {}).get("idlist", [])

    if not ids:
        return {"results": []}

    params2 = urllib.parse.urlencode({
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml"
    })
    url2 = f"{PUBMED_BASE}/efetch.fcgi?{params2}"
    with urllib.request.urlopen(url2, timeout=30) as resp:
        xml = resp.read().decode()

    # Parse XML for titles, abstracts, metadata
    results = []
    import re
    articles = re.split(r'<PubmedArticle>', xml)[1:]
    for article in articles[:limit]:
        title_m = re.search(r'<ArticleTitle[^>]*>(.*?)</ArticleTitle>', article, re.DOTALL)
        pmid_m = re.search(r'<PMID[^>]*>(.*?)</PMID>', article)
        journal_m = re.search(r'<Journal>\s*<Title>(.*?)</Title>', article, re.DOTALL)
        year_m = re.search(r'<PubDate>\s*<Year>\s*(\d{4})', article)
        
        # Extract abstract - multiple AbstractText elements
        abstract_parts = re.findall(r'<AbstractText[^>]*>(.*?)</AbstractText>', article, re.DOTALL)
        abstract = ""
        if abstract_parts:
            # Clean XML tags from abstract text
            for part in abstract_parts:
                clean = re.sub(r'<[^>]+>', '', part).strip()
                if clean:
                    abstract += clean + " "
            abstract = abstract.strip()
        
        # Also check for structured abstract labels
        if not abstract:
            abstract = "N/A"
        
        result = {
            "title": title_m.group(1).strip() if title_m else "N/A",
            "pmid": pmid_m.group(1).strip() if pmid_m else "N/A",
            "journal": journal_m.group(1).strip() if journal_m else "N/A",
            "year": year_m.group(1) if year_m else "N/A",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid_m.group(1)}/" if pmid_m else "",
        }
        if with_abstract:
            result["abstract"] = abstract[:500] if len(abstract) > 500 else abstract
        
        results.append(result)
    return {"source": "PubMed", "query": query, "results": results}


def openalex_search(query, limit=5):
    """Search OpenAlex. 240M works, CC0 license. Free tier = $1/day credit."""
    params = urllib.parse.urlencode({
        "search": query,
        "per-page": str(limit),
    })
    url = f"{OPENALEX_BASE}/works?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "HermesAgent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    results = []
    for work in data.get("results", [])[:limit]:
        authors = [a.get("author", {}).get("display_name", "?") for a in work.get("authorships", [])[:3]]
        results.append({
            "title": work.get("title", "N/A"),
            "doi": work.get("doi", ""),
            "authors": ", ".join(authors) + ("..." if len(work.get("authorships", [])) > 3 else ""),
            "year": work.get("publication_year", ""),
            "cited_by": work.get("cited_by_count", 0),
            "url": work.get("doi", "") or f"https://openalex.org/{work.get('id', '')}",
            "abstract": (work.get("abstract_inverted_index") and "Available") or "N/A",
        })
    return {"source": "OpenAlex", "query": query, "results": results}


def semanticscholar_search(query, limit=5):
    """Search Semantic Scholar. 200M papers, AI summaries. Free key needed."""
    params = urllib.parse.urlencode({
        "query": query,
        "limit": limit,
        "fields": "title,year,authors,externalIds,citationCount,abstract"
    })
    url = f"{S2_BASE}/paper/search?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read())

    results = []
    for paper in data.get("data", [])[:limit]:
        results.append({
            "title": paper.get("title", "N/A"),
            "year": paper.get("year", ""),
            "authors": ", ".join(a.get("name", "?") for a in paper.get("authors", [])[:3]),
            "citations": paper.get("citationCount", 0),
            "url": f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
            "abstract": (paper.get("abstract", "")[:200] + "...") if paper.get("abstract") else "N/A",
        })
    return {"source": "Semantic Scholar", "query": query, "results": results}


def crossref_by_doi(doi):
    """Lookup a paper by DOI. Free, no key."""
    url = f"{CROSSREF_BASE}/{doi}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read())
    msg = data.get("message", {})
    return {
        "title": msg.get("title", [""])[0],
        "doi": doi,
        "authors": [a.get("given", "") + " " + a.get("family", "") for a in msg.get("author", [])[:5]],
        "year": msg.get("published-print", {}).get("date-parts", [[None]])[0][0],
        "cited_by": msg.get("is-referenced-by-count", 0),
        "url": f"https://doi.org/{doi}",
        "publisher": msg.get("publisher", ""),
        "type": msg.get("type", ""),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: research-apis.py <pubmed|openalex|semanticscholar|crossref> [--query Q] [--doi D] [--limit N]")
        sys.exit(1)

    cmd = sys.argv[1]
    query = None
    limit = 5
    doi = None
    with_abstract = False

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--query" and i + 1 < len(sys.argv):
            query = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--doi" and i + 1 < len(sys.argv):
            doi = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--abstract" or sys.argv[i] == "-a":
            with_abstract = True
            i += 1
        else:
            i += 1

    if cmd == "pubmed" and query:
        print(json.dumps(pubmed_search(query, limit, with_abstract), indent=2))
    elif cmd == "openalex" and query:
        print(json.dumps(openalex_search(query, limit), indent=2))
    elif cmd == "semanticscholar" and query:
        print(json.dumps(semanticscholar_search(query, limit), indent=2))
    elif cmd == "crossref" and doi:
        print(json.dumps(crossref_by_doi(doi), indent=2))
    else:
        print("Missing required arguments")
        sys.exit(1)