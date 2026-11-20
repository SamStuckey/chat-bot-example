"""Ingestion: the manifest's canonical source documents become content rows.

The manifest is an allowlist: files it doesn't list are never read.
Sources are Markdown written by hand, so no PDF or HTML parsing is needed.
"""

from ingestion.manifest import ManifestEntry, load_manifest, normalize, read_sources
from ingestion.run import ingest

__all__ = ["ManifestEntry", "ingest", "load_manifest", "normalize", "read_sources"]
