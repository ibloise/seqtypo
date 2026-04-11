# seqtypo

Python client for querying BIGSdb-based APIs (for example PubMLST and Pasteur).

## What is included

- Typed models for resources, databases, schemes, and sequence query results.
- API services with a reusable lightweight HTTP client.
- Helpers to work with base64-encoded sequences.

## Quick start

```python
from seqtypo.api import PubMlstApi

client = PubMlstApi()
databases = client.get_databases(pattern="Neisseria", exact_match=False)

for database in databases:
    print(database.subject, database.href)
```

## Design notes

- Model collections use classes derived from `ModelList` to encapsulate common operations such as filtering and URL extraction.
- `SequenceQueryHandler` automatically builds query payloads and indicates whether a sequence is already base64 encoded.
