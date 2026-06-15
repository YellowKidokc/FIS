from __future__ import annotations
from core.models import to_dict
from core import review_blocks
from engines import classifier, duplicates, folderbrain as folderbrain_engine, inventory, naming, router, similarity

def run_folder_intelligence(folder_path: str, options=None):
    scan = inventory.scan(folder_path, options)
    cache = {"inventory": scan}
    brain = folderbrain_engine.build(folder_path, cache, scan)
    findings = []
    for engine in (duplicates, naming, classifier, router, similarity):
        findings.extend(engine.analyze(brain, cache, options) or [])
    brain.findings = [to_dict(f) for f in findings]
    blocks = review_blocks.build(brain, findings)
    return {"folderbrain": to_dict(brain), "findings": to_dict(findings), "review_blocks": to_dict(blocks)}
