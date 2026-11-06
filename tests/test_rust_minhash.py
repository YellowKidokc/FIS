import os, pytest
import fingerprint as fp

def test_rust_matches_python():
    if fp._rust_minhash_exe() is None:
        pytest.skip("rust/fis_minhash not built")
    sets = [fp.shingle(fp.normalize(t)) for t in [
        "The quick brown fox jumps over the lazy dog again and again",
        "Grace and truth: coherence ψ ∞ unicode words here today",
        "", "short"]]
    rust = fp.minhash_signatures_batch(sets, 64)
    py = [fp._minhash_signature_py(s, 64) for s in sets]
    assert rust == py
