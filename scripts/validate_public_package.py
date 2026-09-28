"""validate_public_package.py
============================

Self-check for the public MIT Sloan Problem 14 release
("Home or Abroad? Where Elite Player Exposure Adds Information About
Future National-Team Strength").

WHAT THIS DOES
--------------
1. Verifies the repository layout (expected directories and published files).
2. Re-derives every published headline number from the aggregate result tables
   in ``results/`` and compares it against the frozen value recorded in this
   file. A mismatch is a hard failure.
3. Verifies that internal README links and image references resolve to files
   that actually exist in the repository.
4. Runs a conservative secret / restricted-content / portability scan over the
   tracked release text.

WHAT THIS DOES NOT DO
---------------------
This is aggregate verification, not retraining. It does not re-run the models.
The raw inputs are not redistributable, so a full rebuild requires a lawful
local copy of the source data; see ``data/README.md``. Reproducibility is
therefore classified as PARTIAL.

The expected values below were transcribed from the frozen, validated result
tables of the private research workspace and independently re-checked against
the source CSVs at release time. They are deliberately NOT recomputed from the
published CSVs before comparison: the point of this script is to catch drift
between the narrative and the evidence.

Run from the repository root:

    python scripts/validate_public_package.py

Exit code 0 = all checks passed. Non-zero = at least one check failed.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# Tolerance for floating-point transcription. The published tables carry full
# double precision, so this only absorbs decimal rounding in the checks below.
TOL = 5e-4

# ---------------------------------------------------------------------------
# Frozen headline values.
# key -> (description, expected value)
# ---------------------------------------------------------------------------
FIVE_COUNTRY_MAE = {
    # (lag, model) -> pooled out-of-time MAE
    (1, "P2-M0_elo"): 42.502185,
    (1, "P2-M1_domestic"): 50.375721,
    (1, "P2-M2_abroad"): 47.280159,
    (2, "P2-M0_elo"): 47.617601,
    (2, "P2-M1_domestic"): 67.978080,
    (2, "P2-M2_abroad"): 54.359563,
    (3, "P2-M0_elo"): 55.417171,
    (3, "P2-M1_domestic"): 82.357038,
    (3, "P2-M2_abroad"): 65.497935,
    (4, "P2-M0_elo"): 63.699893,
    (4, "P2-M1_domestic"): 93.501096,
    (4, "P2-M2_abroad"): 75.199420,
    (5, "P2-M0_elo"): 67.110219,
    (5, "P2-M1_domestic"): 111.154324,
    (5, "P2-M2_abroad"): 80.051224,
}

STAGE_A_MODELS = ("P2-M0_elo", "P2-M1_domestic", "P2-M2_abroad",
                  "P2-M3_domestic_plus_abroad", "P2-M4_deoi", "P2-M5_total_exposure")

ABLATION_DELTA = {
    # lag -> (remove_domestic delta, remove_abroad delta)
    1: (-8.142787, -5.258812),
    2: (-8.008107, -7.331265),
    3: (-1.628260, 5.198628),
    4: (3.819381, 3.280619),
    5: (-19.407345, 18.922750),
}

EXPANDED_DELTA = {
    # lag -> (E2 delta, E3 delta)
    1: (-0.128255, -0.196663),
    2: (-0.507156, -0.708090),
    3: (-0.531515, -0.622572),
    4: (-0.171778, -0.725047),
    5: (-0.699915, -0.895505),
}

EXPANDED_ELO_MAE = {1: 38.628667, 2: 55.418380, 3: 63.345783, 4: 69.399969, 5: 74.464406}

LOCO_T3 = {"P2-E0_elo": 63.347894, "P2-E1_abroad": 64.073725,
           "P2-E2_elo_abroad": 63.013476, "P2-E3_elo_abroad_u23": 62.703272}

DECOMPOSITION_DELTA = {
    # lag -> (W1 between, W2 within, W3 both)
    1: (-0.444027, -0.263015, -0.340605),
    2: (-0.335176, 0.089922, -0.423623),
    3: (-0.715130, -0.402429, -0.826332),
    4: (-0.645291, -0.468922, -0.601929),
    5: (-1.056892, -0.616706, -1.034839),
}

AGE_DELTA = {
    # lag -> (all-age delta, U23 delta)
    1: (-0.191450, -0.196663),
    2: (-0.709839, -0.708090),
    3: (-0.842080, -0.622572),
    4: (-0.646754, -0.725047),
    5: (-0.967555, -0.895505),
}

DESIGN_FACTS = {
    ("analysis_a", "federations"): "5",
    ("analysis_a", "team_seasons"): "70",
    ("analysis_b", "federations"): "90",
    ("analysis_b", "team_seasons"): "1216",
    ("analysis_b", "group_a_federations"): "5",
    ("analysis_b", "group_b_federations"): "85",
    ("analysis_b", "group_b_domestic_zeros"): "0",
}

# Required published files.
REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "NOTICE.md",
    "CITATION.cff",
    "requirements.txt",
    ".gitignore",
    ".gitattributes",
    "PUBLIC_RELEASE_AUDIT.md",
    "Handoff.md",
    "assets/RupayanHalder.jpeg",
    "assets/SoccerSolverLogo.png",
    "data/README.md",
    "docs/methodology.md",
    "figures/Figure_1_home_vs_abroad_and_ablation.png",
    "figures/Figure_2_expanded_panel_and_decomposition.png",
    "results/five_country_model_comparison.csv",
    "results/five_country_feature_ablation.csv",
    "results/expanded_panel_model_comparison.csv",
    "results/expanded_panel_loco_t3.csv",
    "results/between_within_decomposition.csv",
    "results/u23_vs_all_age_abroad.csv",
    "results/study_design.csv",
    "src/README.md",
    "scripts/validate_public_package.py",
    "assets/README.md",
    "paper/README.md",
    # The 20 analytical modules, copied byte-for-byte from the research
    # workspace. Listed individually so the manifest below is closed: a file
    # that is not named here cannot reach the public release.
    "src/scripts/analysis/problem2_nation_coverage_audit.py",
    "src/scripts/download/download_eloratings.py",
    "src/scripts/download/download_transfermarkt.py",
    "src/scripts/eda/pub_common.py",
    "src/scripts/features/build_problem2.py",
    "src/scripts/models/models_common.py",
    "src/scripts/models/problem2_age_test.py",
    "src/scripts/models/problem2_baselines.py",
    "src/scripts/models/problem2_between_within.py",
    "src/scripts/models/problem2_expanded_panel.py",
    "src/scripts/normalize/normalize_eloratings.py",
    "src/scripts/normalize/normalize_transfermarkt_clubs.py",
    "src/scripts/normalize/normalize_transfermarkt_players.py",
    "src/shared/__init__.py",
    "src/shared/catalog.py",
    "src/shared/config.py",
    "src/shared/downloader.py",
    "src/shared/logutil.py",
    "src/shared/names.py",
    "src/shared/tables.py",
]

# Published file count. Guard against the manifest being edited carelessly, and
# against files being added to the tree without being added here.
EXPECTED_FILE_COUNT = 46

# This script contains the secret patterns as literal strings, so it cannot scan
# itself for them without self-matching. It is still scanned for restricted
# paths, absolute local paths, symlinks and size.
SELF = "scripts/validate_public_package.py"

# These two files were supplied by the researcher and are now required. They
# were previously absent and are no longer tolerated as blockers: if either
# disappears, that is a failure, not a known condition.
REQUIRED_ASSETS = ["assets/RupayanHalder.jpeg", "assets/SoccerSolverLogo.png"]

# Frozen SHA-256 digests of the supplied assets, recorded at the point they were
# received. A mismatch means a different file has taken the place of the one
# that was reviewed and approved, which must not pass silently.
ASSET_SHA256 = {
    "assets/RupayanHalder.jpeg": "89ad3f2d774c64980510b68ec6b7a3f05ee2e83b22a091fc6b0d3ed4993b4269",
    "assets/SoccerSolverLogo.png": "72f39bb76960e99c40aca1a89159cd2bbffb3abfce577a64d3503a971148f029",
}

# Width and height of the supplied assets, so a substituted or truncated image
# is caught even if the digest check is ever relaxed.
ASSET_PIXELS = {
    "assets/RupayanHalder.jpeg": (348, 344),
    "assets/SoccerSolverLogo.png": (819, 306),
}

SECRET_PATTERNS = [
    r"password", r"passwd", r"api[_-]?key", r"secret[_-]?key", r"access[_-]?token",
    r"private[_-]?key", r"BEGIN (RSA|OPENSSH|EC) PRIVATE KEY", r"aws_secret",
    r"postgres(ql)?://", r"mysql://", r"mongodb(\+srv)?://", r"ssh-rsa\s+AAAA",
    r"ghp_[A-Za-z0-9]{20,}", r"sk-[A-Za-z0-9]{20,}",
]
# "token" alone is deliberately excluded: it is far too common in prose and in
# football-data code. Credential-shaped tokens are covered by the patterns above.

# The bare word "token" is checked separately as a *warning*, because the brief
# asks for it, but it must not fail the build on legitimate prose.
SOFT_SECRET_PATTERN = re.compile(r"\btoken\b", re.IGNORECASE)

RESTRICTED_SUFFIXES = (".csv.gz", ".sql", ".db", ".sqlite", ".duckdb", ".parquet",
                       ".zip", ".tar", ".gz", ".7z", ".pkl", ".pickle", ".feather")
RESTRICTED_DIR_PARTS = ("data/raw", "data/processed", "dataset/raw", "dataset/interim",
                        "dataset/processed", "outputs", "records", "logs", ".venv")

TEXT_SUFFIXES = (".md", ".py", ".txt", ".cff", ".json", ".csv", ".cfg", ".toml", ".yml", ".yaml")

# The only binary payloads permitted anywhere in the release. Each is either
# project-generated from published tables or supplied and approved by the
# researcher, and each is pinned by digest in ASSET_SHA256.
ALLOWED_BINARIES = set(REQUIRED_ASSETS) | {
    "figures/Figure_1_home_vs_abroad_and_ablation.png",
    "figures/Figure_2_expanded_panel_and_decomposition.png",
}

results_log: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str = "") -> None:
    results_log.append((status, name, detail))


def read_rows(relpath: str) -> list[dict]:
    with open(ROOT / relpath, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def check_layout() -> None:
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if p.is_file() and p.stat().st_size > 0:
            record("PASS", f"file present: {rel}")
        else:
            record("FAIL", f"file missing or empty: {rel}")


def check_assets() -> None:
    """The two supplied assets must be present, unmodified and correctly sized.

    Both were previously missing and no substitute was ever used. They are now
    supplied and approved, so they are pinned: a digest or dimension mismatch
    means a different image has taken their place.
    """
    import struct

    for rel in REQUIRED_ASSETS:
        p = ROOT / rel
        if not p.is_file():
            record("FAIL", f"required asset missing: {rel}")
            continue

        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        expected = ASSET_SHA256[rel]
        if digest != expected:
            record("FAIL", f"asset digest changed for {rel}: expected {expected}, got {digest}")
        else:
            record("PASS", f"asset digest verified: {rel} ({digest[:12]}...)")

        data = p.read_bytes()
        width = height = None
        fmt = None
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            fmt = "PNG"
            width, height = struct.unpack(">II", data[16:24])
        elif data[:2] == b"\xff\xd8":
            fmt = "JPEG"
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    height, width = struct.unpack(">HH", data[i + 5:i + 9])
                    break
                i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
        else:
            record("FAIL", f"asset is not a readable PNG or JPEG: {rel}")

        if width is not None:
            exp_w, exp_h = ASSET_PIXELS[rel]
            if (width, height) != (exp_w, exp_h):
                record("FAIL", f"asset dimensions changed for {rel}: "
                               f"expected {exp_w}x{exp_h}, got {width}x{height}")
            else:
                record("PASS", f"asset is a valid {fmt}, {width}x{height}: {rel}")


def check_five_country() -> None:
    rows = read_rows("results/five_country_model_comparison.csv")
    index = {(int(r["lag"]), r["model"]): float(r["mae_pooled"]) for r in rows}
    for key, expected in FIVE_COUNTRY_MAE.items():
        got = index.get(key)
        if got is None:
            record("FAIL", f"five-country MAE missing for {key}")
        elif abs(got - expected) > TOL:
            record("FAIL", f"five-country MAE {key}: expected {expected}, got {got}")
        else:
            record("PASS", f"five-country MAE {key[0]} {key[1]} = {got:.3f}")

    # Structural claim: abroad beats domestic at every tested horizon.
    breaches = [lag for lag in range(1, 6)
                if index[(lag, "P2-M2_abroad")] >= index[(lag, "P2-M1_domestic")]]
    if breaches:
        record("FAIL", f"abroad does not beat domestic at lags {breaches}")
    else:
        record("PASS", "abroad-only MAE below domestic-only MAE at t+1..t+5")

    # Structural claim: no development model beats current Elo from t+2 to t+5.
    breaches = [(lag, m) for lag in range(2, 6)
                for m in STAGE_A_MODELS if m != "P2-M0_elo"
                if index[(lag, m)] < index[(lag, "P2-M0_elo")]]
    if breaches:
        record("FAIL", f"a development model beat Elo beyond t+1 at {sorted(set(breaches))}")
    else:
        record("PASS", "no development model beats current Elo at t+2..t+5")

    # Structural claim: at t+1 exactly one model edges past Elo, by a negligible
    # margin. Checked explicitly so the README cannot quietly overstate this.
    t1 = {m: index[(1, m)] for m in STAGE_A_MODELS if (1, m) in index}
    t1_beaters = sorted(m for m, v in t1.items()
                        if m != "P2-M0_elo" and v < t1["P2-M0_elo"])
    if t1_beaters != ["P2-M4_deoi"]:
        record("FAIL", f"unexpected t+1 model(s) beating Elo: {sorted(t1_beaters)}")
    else:
        margin = t1["P2-M0_elo"] - t1["P2-M4_deoi"]
        if margin > 0.25:
            record("FAIL", f"t+1 DEOI margin is {margin:.3f}, larger than the 0.25 MAE described")
        else:
            record("PASS", f"t+1: only P2-M4_deoi edges Elo, by {margin:.3f} MAE "
                           f"(42.309 vs 42.502) - negligible and not persistent")


def check_ablation() -> None:
    rows = read_rows("results/five_country_feature_ablation.csv")
    index = {(int(r["lag"]), r["variant"]): float(r["mae_delta_vs_full"]) for r in rows}
    for lag, (dom, abr) in ABLATION_DELTA.items():
        for variant, expected in (("remove_domestic", dom), ("remove_abroad", abr)):
            got = index.get((lag, variant))
            if got is None:
                record("FAIL", f"ablation missing for {(lag, variant)}")
            elif abs(got - expected) > TOL:
                record("FAIL", f"ablation {(lag, variant)}: expected {expected}, got {got}")
            else:
                record("PASS", f"ablation t+{lag} {variant} = {got:+.2f}")

    worse = [lag for lag in (3, 4, 5) if index[(lag, "remove_abroad")] <= 0]
    if worse:
        record("FAIL", f"removing abroad did not worsen MAE at lags {worse}")
    else:
        record("PASS", "removing abroad worsened MAE at t+3, t+4 and t+5")

    helped = [lag for lag in range(1, 6) if index[(lag, "remove_domestic")] < 0]
    if len(helped) != 4:
        record("FAIL", f"removing domestic improved MAE at {len(helped)} of 5 lags, expected 4")
    else:
        record("PASS", "removing domestic improved MAE at 4 of 5 lags (all but t+4)")


def check_expanded() -> None:
    rows = read_rows("results/expanded_panel_model_comparison.csv")
    e2 = {int(r["lag"]): float(r["delta_mae_vs_E0"]) for r in rows if r["model"] == "P2-E2_elo_abroad"}
    e3 = {int(r["lag"]): float(r["delta_mae_vs_E0"]) for r in rows if r["model"] == "P2-E3_elo_abroad_u23"}
    e0 = {int(r["lag"]): float(r["mae_pooled"]) for r in rows if r["model"] == "P2-E0_elo"}

    for lag, (a, b) in EXPANDED_DELTA.items():
        for name, got, expected in (("E2", e2.get(lag), a), ("E3", e3.get(lag), b)):
            if got is None:
                record("FAIL", f"expanded delta missing for {name} t+{lag}")
            elif abs(got - expected) > TOL:
                record("FAIL", f"expanded delta {name} t+{lag}: expected {expected}, got {got}")
            else:
                record("PASS", f"expanded delta {name} t+{lag} = {got:+.3f}")

    for lag, expected in EXPANDED_ELO_MAE.items():
        got = e0.get(lag)
        if got is None or abs(got - expected) > TOL:
            record("FAIL", f"expanded Elo MAE t+{lag}: expected {expected}, got {got}")
        else:
            record("PASS", f"expanded Elo baseline MAE t+{lag} = {got:.3f}")

    breaches = [lag for lag in range(1, 6) if not (e2[lag] < 0 and e3[lag] < 0)]
    if breaches:
        record("FAIL", f"abroad did not improve on Elo at lags {breaches}")
    else:
        record("PASS", "Elo+abroad and Elo+U23-abroad both improve on Elo at t+1..t+5")

    spread_e2 = (min(-v for v in e2.values()), max(-v for v in e2.values()))
    spread_e3 = (min(-v for v in e3.values()), max(-v for v in e3.values()))
    record("PASS", f"published E2 range {spread_e2[0]:.3f}-{spread_e2[1]:.3f}; "
                   f"E3 range {spread_e3[0]:.3f}-{spread_e3[1]:.3f}")

    loco = {r["model"]: float(r["mae_loco_pooled"]) for r in read_rows("results/expanded_panel_loco_t3.csv")}
    for model, expected in LOCO_T3.items():
        got = loco.get(model)
        if got is None or abs(got - expected) > TOL:
            record("FAIL", f"LOCO t+3 {model}: expected {expected}, got {got}")
        else:
            record("PASS", f"LOCO t+3 {model} = {got:.2f}")

    if not loco["P2-E3_elo_abroad_u23"] < loco["P2-E0_elo"]:
        record("FAIL", "LOCO t+3: Elo+U23-abroad does not improve on Elo")
    else:
        record("PASS", "LOCO t+3: Elo+U23-abroad improves on Elo alone")


def check_decomposition() -> None:
    rows = read_rows("results/between_within_decomposition.csv")
    w1 = {int(r["lag"]): float(r["delta_mae_vs_elo"]) for r in rows if r["model"] == "P2-W1_elo_between"}
    w2 = {int(r["lag"]): float(r["delta_mae_vs_elo"]) for r in rows if r["model"] == "P2-W2_elo_within"}
    w3 = {int(r["lag"]): float(r["delta_mae_vs_elo"]) for r in rows if r["model"] == "P2-W3_elo_between_within"}
    for lag, (a, b, c) in DECOMPOSITION_DELTA.items():
        for name, got, expected in (("W1 between", w1.get(lag), a),
                                    ("W2 within", w2.get(lag), b),
                                    ("W3 both", w3.get(lag), c)):
            if got is None:
                record("FAIL", f"decomposition missing for {name} t+{lag}")
            elif abs(got - expected) > TOL:
                record("FAIL", f"decomposition {name} t+{lag}: expected {expected}, got {got}")
            else:
                record("PASS", f"decomposition t+{lag} {name} = {got:+.3f}")

    breaches = [lag for lag in range(1, 6) if not (w1[lag] < 0 and w1[lag] < w2[lag])]
    if breaches:
        record("FAIL", f"between-country is not the stronger component at lags {breaches}")
    else:
        record("PASS", "between-country component improves MAE and exceeds within at t+1..t+5")


def check_age() -> None:
    rows = read_rows("results/u23_vs_all_age_abroad.csv")
    a1 = {int(r["lag"]): float(r["delta_mae_vs_elo"]) for r in rows if r["model"] == "P2-A1_elo_allage"}
    a2 = {int(r["lag"]): float(r["delta_mae_vs_elo"]) for r in rows if r["model"] == "P2-A2_elo_u23"}
    for lag, (a, b) in AGE_DELTA.items():
        for name, got, expected in (("all-age", a1.get(lag), a), ("U23", a2.get(lag), b)):
            if got is None:
                record("FAIL", f"age test missing for {name} t+{lag}")
            elif abs(got - expected) > TOL:
                record("FAIL", f"age test {name} t+{lag}: expected {expected}, got {got}")
            else:
                record("PASS", f"age test t+{lag} {name} = {got:+.3f}")

    gaps = [abs(a1[lag] - a2[lag]) for lag in range(1, 6)]
    if max(gaps) > 0.30:
        record("FAIL", f"U23 and all-age profiles diverge by up to {max(gaps):.3f} MAE")
    else:
        record("PASS", f"U23 and all-age abroad profiles stay within {max(gaps):.3f} MAE")


def check_design() -> None:
    rows = read_rows("results/study_design.csv")
    index = {(r["stage"], r["quantity"]): r["value"] for r in rows}
    for key, expected in DESIGN_FACTS.items():
        got = index.get(key)
        if got != expected:
            record("FAIL", f"design fact {key}: expected {expected}, got {got}")
        else:
            record("PASS", f"design fact {key[0]} {key[1]} = {got}")


def check_readme_links() -> None:
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")

    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path = target.split("#", 1)[0]
        if not path:
            continue
        if not (ROOT / path).exists():
            record("FAIL", f"README link target does not exist: {target}")
    record("PASS", "README relative link targets checked")

    for alt, target in re.findall(r"!\[([^\]]*)\]\(([^)\s]+)\)", text):
        if target.startswith(("http://", "https://")):
            continue
        if not (ROOT / target).exists():
            record("FAIL", f"README image missing on disk: {target}")
        else:
            record("PASS", f"README image resolves: {target}")

    # HTML <img> tags, used for the author portrait and the collaborator mark so
    # they can be sized and floated. Both must resolve, and both required assets
    # must actually be referenced, or a supplied asset would sit unused.
    for src in re.findall(r'<img[^>]+src="([^"]+)"', text):
        if src.startswith(("http://", "https://")):
            record("FAIL", f"README embeds a remote image; assets must be local: {src}")
            continue
        if not (ROOT / src).is_file():
            record("FAIL", f"README <img> src missing on disk: {src}")
        else:
            record("PASS", f"README <img> src resolves: {src}")

    for rel in REQUIRED_ASSETS:
        if rel in text:
            record("PASS", f"README references the required asset: {rel}")
        else:
            record("FAIL", f"README does not reference the required asset: {rel}")

    required_phrases = {
        "Elo is treated as a lagged match-result outcome rather than ground truth":
            "Ruben comment 2 framing",
        "rather than ground truth for national-team quality":
            "Elo is not ground truth",
        "predictive association":
            "causal limitation is stated",
        "not a causal": "causal limitation is stated",
        "MIT Sloan Sports Analytics Conference research project":
            "conference identifier",
        "SoccerSolver": "collaboration statement",
    }
    lowered = re.sub(r"\s+", " ", text).lower()
    for phrase, why in required_phrases.items():
        if re.sub(r"\s+", " ", phrase).lower() in lowered:
            record("PASS", f"README states {why}")
        else:
            record("FAIL", f"README is missing {why} (expected phrase: {phrase})")

    if "Problem 14" in text:
        record("PASS", "README identifies Problem 14")
    else:
        record("FAIL", "README does not identify Problem 14")

    # The domestic result is about incremental forecast value. It must not be
    # dressed up as a verdict on domestic youth development.
    for phrase, why in {
        "not** evidence that domestic youth development is ineffective":
            "the negative domestic result is not read as a development verdict",
        "incremental predictive value":
            "the domestic result is framed as forecast value",
    }.items():
        if phrase.lower() in lowered:
            record("PASS", f"README states {why}")
        else:
            record("FAIL", f"README is missing {why} (expected phrase: {phrase})")


def _flat(path: Path) -> str:
    """Read a document, drop markdown blockquote markers, collapse whitespace.

    Blockquote markers are stripped so a quoted statement is comparable to the
    same statement written inline.
    """
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^[ \t]*>[ \t]?", "", text, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", text)


def check_no_forbidden_framing() -> None:
    """The reviewer-resolved framing must not be undone by a stray sentence."""
    readme = _flat(ROOT / "README.md").lower()
    forbidden = [
        "should federations send players abroad",
        "federations should export players",
        "complete quality index",
        "is ground truth for national-team quality",
        "proves that sending players abroad",
        "domestic scouting is failing",
    ]
    hits = [f for f in forbidden if f in readme]

    # The one legitimate mention of an "ineffective" reading is the disclaimer
    # that rules it out. Remove that disclaimer, then require the phrase to be
    # gone, so the claim cannot survive anywhere else.
    disclaimed = re.sub(
        r"it is \*{0,2}not\*{0,2} evidence that (domestic|domestic youth) development is ineffective",
        "", readme)
    leaked = [p for p in ("domestic youth development is ineffective",
                          "domestic development is ineffective")
              if p in disclaimed]

    if hits or leaked:
        record("FAIL", f"README contains forbidden framing: {hits + leaked}")
    else:
        record("PASS", "README contains no forbidden causal, quality-index or "
                       "development-verdict framing; the negative domestic result "
                       "appears only inside the disclaimer that rules that reading out")


def check_authorship_metadata() -> None:
    """Authorship is CONFIRMED as Rupayan Halder. Assert the resolved state.

    Guards against three regressions: the caveat coming back, a second author
    appearing, or SoccerSolver being described as anything other than a
    research collaborator and acknowledgement.
    """
    readme = _flat(ROOT / "README.md")
    notice = _flat(ROOT / "NOTICE.md")
    audit = _flat(ROOT / "PUBLIC_RELEASE_AUDIT.md")
    handoff = _flat(ROOT / "Handoff.md")
    citation = _flat(ROOT / "CITATION.cff")
    # The YAML authors block must be parsed with newlines intact.
    citation_raw = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    # The paper directory keeps a status table of its own. It is a current-status
    # table, not a historical log, so a confirmed authorship must not still be
    # described there as pending.
    paper_readme = _flat(ROOT / "paper/README.md")
    if re.search(r"authorship[^\n]{0,40}confirmed", paper_readme, re.IGNORECASE):
        record("PASS", "paper/README.md records authorship as confirmed")
    else:
        record("FAIL", "paper/README.md does not record authorship as confirmed")

    # A handoff that claims the push already happened must quote the commit it
    # produced. Without a hash the claim is unfalsifiable, and before the push
    # it is simply false.
    push_claims = re.search(
        r"\bpush\b[^.]{0,80}\b(?:was performed|has been (?:performed|pushed|run)"
        r"|is complete|completed)\b|\bpushed to origin\b", handoff, re.IGNORECASE)
    commit_hash = re.search(r"\b[0-9a-f]{40}\b", handoff)
    if push_claims and not commit_hash:
        record("FAIL", "Handoff.md claims the push was performed but records no "
                       "40-character commit hash; the claim is unfalsifiable")
    elif commit_hash:
        record("PASS", f"Handoff.md records a real commit hash "
                       f"({commit_hash.group(0)[:12]}) for the push it describes")
    else:
        record("PASS", "Handoff.md makes no claim that a push has already happened")

    # CFF 1.2.0 requires cff-version, message, title, authors and date-released,
    # plus a version for type: software. A present-but-empty key satisfies neither
    # the schema nor a reader, so require a value as well as the key.
    required_cff = ("cff-version", "message", "title", "authors", "date-released",
                    "type", "version", "license")
    absent_cff, empty_cff = [], []
    # In YAML these two carry their value on the following indented lines, so an
    # empty inline value is correct for them. `authors` is validated separately by
    # the author-block check below, which requires an indented entry list.
    block_valued = {"authors", "keywords"}
    for k in required_cff:
        m = re.search(rf'^{k}:[ \t]*(.*)$', citation_raw, re.MULTILINE)
        if not m:
            absent_cff.append(k)
        elif k in block_valued:
            continue
        elif not m.group(1).strip().strip('"').strip("'").strip():
            empty_cff.append(k)
    if absent_cff:
        record("FAIL", f"CITATION.cff is missing required CFF 1.2.0 fields: {absent_cff}")
    if empty_cff:
        record("FAIL", f"CITATION.cff has required fields with no value: {empty_cff}; "
                       f"an empty key satisfies neither the schema nor a reader")
    if not absent_cff and not empty_cff:
        record("PASS", "CITATION.cff carries every required CFF 1.2.0 field with a "
                       "value, including date-released and a software version")

    # An empty identifier is worse than an absent one: it looks supplied.
    for field in ("orcid", "doi", "url", "repository-code"):
        m = re.search(rf'^\s*{field}:[ \t]*(.*)$', citation_raw, re.MULTILINE)
        if m and not m.group(1).strip().strip('"').strip("'").strip("`"):
            record("FAIL", f"CITATION.cff has an empty {field}; remove the key instead")
            break
    else:
        record("PASS", "CITATION.cff has no empty identifier fields")

    # The collaboration statement, preserved verbatim. Whitespace is normalised
    # only; the wording itself is asserted.
    ack_norm = re.sub(
        r"\s+", " ",
        "This research was developed in collaboration with SoccerSolver. "
        "SoccerSolver currently works with more than 10 football clubs.")
    for name, doc in (("README.md", readme), ("NOTICE.md", notice),
                      ("PUBLIC_RELEASE_AUDIT.md", audit)):
        if ack_norm in doc:
            record("PASS", f"{name} preserves the SoccerSolver collaboration statement verbatim")
        else:
            record("FAIL", f"{name} does not preserve the collaboration statement verbatim: {ack_norm}")

    for name, doc in (("README.md", readme), ("PUBLIC_RELEASE_AUDIT.md", audit),
                      ("Handoff.md", handoff)):
        if "authorship: confirmed" in doc.lower() or "authorship status: confirmed" in doc.lower():
            record("PASS", f"{name} records authorship as CONFIRMED")
        else:
            record("FAIL", f"{name} does not record authorship as CONFIRMED")

    # No unresolved-authorship language may survive in a current-status document.
    for name, doc in (("README.md", readme), ("CITATION.cff", citation),
                      ("Handoff.md", handoff)):
        if re.search(r"pending human confirmation|authorship status:\s*pending", doc, re.IGNORECASE):
            record("FAIL", f"{name} still carries unresolved-authorship language")
        else:
            record("PASS", f"{name} carries no unresolved-authorship language")

    # Exactly one author in CITATION.cff, parsed structurally. Every line of the
    # block must be indented, so trailing comment text cannot be slurped in.
    author_block = re.search(r"^authors:[ \t]*\n((?:[ \t]+[^\n]*\n)+)", citation_raw, re.MULTILINE)
    if not author_block:
        record("FAIL", "CITATION.cff has no authors block")
        return
    block = author_block.group(1)
    entries = re.findall(r"^\s*-\s+([\w-]+):", block, re.MULTILINE)
    families = re.findall(r"^\s*-\s+family-names:\s*(\S+)", block, re.MULTILINE)
    given = re.findall(r"^\s+given-names:\s*(\S+)", block, re.MULTILINE)
    if len(entries) == 1 and families == ["Halder"] and given == ["Rupayan"]:
        record("PASS", "CITATION.cff lists exactly one author: Rupayan Halder")
    else:
        record("FAIL", f"CITATION.cff author list is not exactly [Rupayan Halder]: "
                       f"entries={entries}, family-names={families}, given-names={given}")

    if re.search(r"soccersolver", block, re.IGNORECASE):
        record("FAIL", "SoccerSolver appears in the CITATION.cff authors block")
    else:
        record("PASS", "SoccerSolver is not in the CITATION.cff authors block")

    # SoccerSolver must never be described as author, funder, sponsor, owner or
    # partner of the research. Proximity matching proved unreliable here, because
    # an <img> tag and other markup can sit between a role word and the name, so
    # this is done at sentence level instead: a sentence mentioning SoccerSolver
    # and a role word must also carry a negation. Any other form is a finding.
    sentence_split = re.compile(r"(?<=[.!?;])\s+")
    role_word = re.compile(
        r"\b(?:co-?)?(?:author(?:ed|ing|s|ship)?|funder?s?|funded|sponsor(?:ed|ing|s)?"
        r"|owner(?:s|ship)?|owned|partner(?:ed|ing|s)?|patron)\b",
        re.IGNORECASE)
    # Uses of a role word that describe the *process* or a *file label*, rather
    # than asserting that SoccerSolver holds the role. These are removed before
    # the sentence is judged, so "change the Authorship statement" and
    # "Author identification" are not mistaken for a claim.
    non_claim = re.compile(
        r"\bauthorship\b"
        r"|\bauthors?\s+(?:identification|photo|photograph|headshot|portrait|image"
        r"|identifier|list|order|block|statement|metadata|status|line|role|record"
        r"|section|heading|entry|entries|field|name|names|byline|credit|credits)\b",
        re.IGNORECASE)
    # An explicit denial is the only acceptable form. Denial clauses are deleted
    # from the sentence before it is judged, so "is not an author" is excised
    # while a contradictory claim in the same sentence is still caught. Checking
    # the whole sentence for a negation would not: one denial would excuse any
    # number of claims in the same breath.
    role_core = r"(?:author|funder|sponsor|owner|partner|patron)\w*"
    denial_phrase = re.compile(
        # "not ... author, funder, sponsor or owner" - the trailing enumeration
        # must go too, or removing only the first role word leaves the rest of
        # the claim standing in the sentence.
        r"\b(?:is|are|was|were)?\s*\bnot\b[^.;]{0,80}?\b" + role_core
        + r"(?:[^.;]{0,30}?\b" + role_core + r")*"
        r"|\bnone of (?:which|those|these|whom)\b[^.;]{0,80}?"
        r"\b(?:claimed|established|inferred|intended)\b"
        r"|\bnone (?:is|are) (?:claimed|established|inferred)\b",
        re.IGNORECASE)
    negation = re.compile(
        r"\b(?:not|no|never|none|nor|neither|without|deliberately|excludes?|"
        r"excluded|ruled out)\b", re.IGNORECASE)
    role_docs = ("README.md", "NOTICE.md", "PUBLIC_RELEASE_AUDIT.md", "Handoff.md",
                 "CITATION.cff", "assets/README.md", "paper/README.md",
                 "data/README.md", "src/README.md")
    docs = (("README.md", readme), ("NOTICE.md", notice),
            ("PUBLIC_RELEASE_AUDIT.md", audit), ("Handoff.md", handoff),
            ("CITATION.cff", citation),
            ("assets/README.md", _flat(ROOT / "assets/README.md")),
            ("paper/README.md", _flat(ROOT / "paper/README.md")),
            ("data/README.md", _flat(ROOT / "data/README.md")),
            ("src/README.md", _flat(ROOT / "src/README.md")))

    offenders = []
    for name, doc in docs:
        for sent in sentence_split.split(doc):
            if "soccersolver" not in sent.lower():
                continue
            scan = denial_phrase.sub(" ", non_claim.sub(" ", sent))
            m = role_word.search(scan)
            if m:
                offenders.append(
                    f"{name}: ...{scan.strip()[:90]}...")

    if offenders:
        for o in sorted(set(offenders)):
            record("FAIL", f"SoccerSolver described in a role it does not hold: {o}")
    else:
        record("PASS", f"SoccerSolver is never described as author, funder, sponsor, owner "
                       f"or partner across all {len(role_docs)} documents; every sentence "
                       f"naming it alongside a role word carries a negation")

    # And the denial must positively exist, so the check cannot pass by omission.
    denial = re.compile(r"soccersolver[^.]{0,160}?\bnot\b[^.]{0,60}?\bauthor\b",
                        re.IGNORECASE)
    for name, doc in (("README.md", readme), ("NOTICE.md", notice),
                      ("PUBLIC_RELEASE_AUDIT.md", audit), ("Handoff.md", handoff)):
        if denial.search(doc):
            record("PASS", f"{name} explicitly states SoccerSolver is not an author")
        else:
            record("FAIL", f"{name} does not explicitly state that SoccerSolver is not an author")


def check_secret_and_restricted_scan() -> None:
    findings: list[str] = []
    soft: list[str] = []
    restricted: list[str] = []
    absolute_paths: list[str] = []

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(ROOT).as_posix()
        rel_lower = rel.lower()

        # Repository metadata and bytecode caches are not published content, and
        # must not be scanned. `.git/logs/...` in particular collides with the
        # "logs" exclusion, which made the validator fail only after the first
        # commit created a reflog.
        parts = set(path.relative_to(ROOT).parts)
        if ".git" in parts or "__pycache__" in parts:
            continue

        if any(part in rel_lower for part in RESTRICTED_DIR_PARTS) and not rel_lower.endswith(".gitignore"):
            findings.append(f"path under an excluded directory: {rel}")

        if path.suffix.lower() in RESTRICTED_SUFFIXES:
            restricted.append(f"{rel} ({path.stat().st_size} bytes)")

        # Any image or other binary outside the approved set is a finding.
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff",
                                   ".webp", ".ico", ".pdf", ".svg", ".emf", ".wmf"):
            if rel not in ALLOWED_BINARIES:
                restricted.append(f"unapproved image or document: {rel}")

        if path.suffix.lower() in TEXT_SUFFIXES or path.name in (".gitignore", ".gitattributes", "LICENSE"):
            try:
                text = path.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                continue
            for pattern in SECRET_PATTERNS:
                if rel == SELF:
                    continue
                for m in re.finditer(pattern, text, re.IGNORECASE):
                    findings.append(f"{rel}: matches /{pattern}/")
            if SOFT_SECRET_PATTERN.search(text) and rel != SELF:
                soft.append(rel)
            # Portability: no machine-specific absolute Windows paths outside
            # the audit and handoff documents, which record provenance
            # deliberately. A drive letter must be followed by a separator and
            # at least two more path segments, so ordinary prose such as
            # "Note: see x/y/z" is not mistaken for a local path. This file
            # is exempt because find_git() names the standard Git install
            # locations, which are install conventions rather than machine
            # details.
            exempt = ("public_release_audit.md", "handoff.md", SELF)
            if rel_lower not in exempt:
                for m in re.finditer(r"\b[A-Za-z]:[\\/](?:[A-Za-z0-9_.~() -]+[\\/]){2,}", text):
                    absolute_paths.append(f"{rel}: {m.group(0).strip()}")

    if restricted:
        for r in restricted:
            record("FAIL", f"restricted or unapproved payload present: {r}")
    else:
        record("PASS", "no database, archive or unapproved image payload; "
                       f"only {len(ALLOWED_BINARIES)} approved images")

    for f in findings:
        record("FAIL", f"secret scan: {f}")
    if not findings:
        record("PASS", "no credential-shaped strings in the release")

    for a in absolute_paths:
        record("FAIL", f"absolute local path: {a}")
    if not absolute_paths:
        record("PASS", "no machine-specific absolute paths outside the audit documents")

    if soft:
        record("PASS", f"'token' appears in {len(soft)} file(s) in non-credential prose (not a failure)")


def check_symlinks_and_sizes() -> None:
    symlinks = [p for p in ROOT.rglob("*") if p.is_symlink()]
    if symlinks:
        for s in symlinks:
            record("FAIL", f"symlink present: {s.relative_to(ROOT).as_posix()}")
    else:
        record("PASS", "no symlinks in the release")

    big = [(p.relative_to(ROOT).as_posix(), p.stat().st_size)
           for p in ROOT.rglob("*")
           if p.is_file() and not p.is_symlink() and p.stat().st_size > 2 * 1024 * 1024]
    if big:
        for name, size in big:
            record("FAIL", f"file larger than 2 MiB: {name} ({size} bytes)")
    else:
        record("PASS", "no file exceeds 2 MiB")


def find_git() -> str | None:
    """Locate git, including the standard Windows install locations.

    A freshly installed Git is often not yet on the PATH of a running shell, so
    the usual locations are probed before giving up.
    """
    import shutil
    found = shutil.which("git")
    if found:
        return found
    for candidate in (r"C:\Program Files\Git\cmd\git.exe",
                      r"C:\Program Files\Git\bin\git.exe",
                      r"C:\Program Files (x86)\Git\cmd\git.exe",
                      str(Path.home() / "AppData/Local/Programs/Git/cmd/git.exe")):
        if Path(candidate).is_file():
            return candidate
    return None


def actual_tree() -> list[str]:
    """Every real file in the release tree, as forward-slash relative paths.

    `.git` is metadata and `__pycache__` is a build artefact; neither is
    published, and both are gitignored, so neither belongs in the manifest.
    """
    found = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        parts = set(path.relative_to(ROOT).parts)
        if ".git" in parts or "__pycache__" in parts:
            continue
        found.append(path.relative_to(ROOT).as_posix())
    return sorted(found)


def check_closed_manifest() -> None:
    """The release is a closed set of files.

    check_layout proves every expected file is present. This proves the
    converse: nothing else is. Without it, a stray dataset, notebook, log or
    extra image dropped into the tree is invisible to the package - it would
    not be published only because nobody remembered to stage it.
    """
    expected = set(REQUIRED_FILES)
    actual = set(actual_tree())

    unexpected = sorted(actual - expected)
    if unexpected:
        for u in unexpected:
            record("FAIL", f"file present but not in the release manifest: {u}")
    else:
        record("PASS", f"no undeclared files in the tree "
                       f"({len(actual)} files, all declared)")

    if len(REQUIRED_FILES) != EXPECTED_FILE_COUNT:
        record("FAIL", f"manifest lists {len(REQUIRED_FILES)} files but "
                       f"EXPECTED_FILE_COUNT is {EXPECTED_FILE_COUNT}")
    else:
        record("PASS", f"manifest lists exactly {EXPECTED_FILE_COUNT} files")


def check_git_tracked_scope() -> None:
    git_dir = ROOT / ".git"
    if not git_dir.exists():
        record("PASS", "no .git directory in the release tree; the closed-manifest "
                       "check above covers the file scope instead")
        return

    git = find_git()
    if git is None:
        # An environment problem, not a package defect. Do not fail the run.
        record("BLOCKED", "a .git directory exists but git is not installed or not on PATH; "
                          "tracked-file scope not verified")
        return

    import subprocess
    try:
        out = subprocess.run([git, "ls-files"], cwd=ROOT, capture_output=True,
                             text=True, timeout=60, check=True).stdout
    except Exception as exc:  # noqa: BLE001
        record("BLOCKED", f"could not list tracked files with git: {exc}")
        return
    tracked = {line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()}
    expected = set(REQUIRED_FILES)

    offenders = sorted(t for t in tracked
                       if t.startswith((".venv/", "data/raw/", "data/processed/", "records/"))
                       or Path(t).suffix.lower() in RESTRICTED_SUFFIXES)
    if offenders:
        for o in offenders:
            record("FAIL", f"restricted path is tracked: {o}")
    else:
        record("PASS", f"no restricted path is tracked ({len(tracked)} tracked files)")

    # Staged files are what actually gets published, so the index must match the
    # manifest exactly - no more, and none missing.
    undeclared = sorted(tracked - expected)
    if undeclared:
        for u in undeclared:
            record("FAIL", f"file is staged for publication but is not in the "
                           f"release manifest: {u}")
    else:
        record("PASS", "every staged file is declared in the release manifest")

    unstaged = sorted(expected - tracked)
    if unstaged:
        for u in unstaged:
            record("FAIL", f"manifest file is not staged, so the release would be "
                           f"incomplete: {u}")
    else:
        record("PASS", "every manifest file is staged for publication")


def main() -> int:
    for fn in (check_layout, check_closed_manifest, check_assets,
               check_five_country, check_ablation,
               check_expanded, check_decomposition, check_age, check_design,
               check_readme_links, check_no_forbidden_framing,
               check_authorship_metadata, check_secret_and_restricted_scan,
               check_symlinks_and_sizes, check_git_tracked_scope):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            record("FAIL", f"{fn.__name__} raised {type(exc).__name__}: {exc}")

    passed = sum(1 for s, _, _ in results_log if s == "PASS")
    failed = [n for s, n, _ in results_log if s == "FAIL"]
    blocked = [n for s, n, _ in results_log if s == "BLOCKED"]

    print("=" * 74)
    print("MIT Sloan Problem 14 - public package validation")
    print("Aggregate verification only. This does not re-run the models.")
    print(f"{len(REQUIRED_ASSETS)} required assets are digest-pinned; "
          "any other image in the tree is a failure.")
    print("=" * 74)
    for status, name, detail in results_log:
        if status != "PASS":
            print(f"  [{status}] {name}{(' - ' + detail) if detail else ''}")
    print("-" * 74)
    print(f"PASS: {passed}   FAIL: {len(failed)}   BLOCKED: {len(blocked)}")
    if blocked:
        print("\nKnown blockers (documented in PUBLIC_RELEASE_AUDIT.md):")
        for b in blocked:
            print(f"  - {b}")
    if failed:
        print("\nFAILURES:")
        for f in failed:
            print(f"  - {f}")
        print("\nRESULT: FAIL")
        return 1
    print("\nRESULT: PASS" + (" (with documented blockers)" if blocked else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
