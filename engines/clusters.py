from __future__ import annotations
try:
    from cluster_engine import cluster_files as legacy_cluster_files
except Exception:
    legacy_cluster_files = None

def analyze(folderbrain, cache=None, options=None):
    return []
