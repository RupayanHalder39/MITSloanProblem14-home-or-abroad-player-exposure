# Handoff

State of the package, what is finished, and what a human needs to do next.

Repository root: `MITSloanProblem14-home-or-abroad-player-exposure`
Public repository: `https://github.com/RupayanHalder39/MITSloanProblem14-home-or-abroad-player-exposure`
Research workspace: read-only. Nothing in it was modified.

**AUTHORSHIP STATUS: CONFIRMED — Rupayan Halder.**

| Question | Answer |
|---|---|
| **AUTHORSHIP** | **CONFIRMED — Rupayan Halder** |
| **GITHUB CONTENT READY** | **YES** |
| **SAFE TO PUSH** | **YES** |

---

## What is done

- **AUTHORSHIP CONFIRMED.** The researcher confirmed in writing that the complete
  author list is **Rupayan Halder**. `CITATION.cff` names him alone. Reviewer
  comments, project files, acknowledgements, related projects, previous papers,
  the SoccerSolver collaboration and Ruben's comments on the abstract were all
  explicitly ruled out as sources of authorship.
- **SoccerSolver is a research collaborator and acknowledgement, not an author.**
  It is not an author, funder, sponsor or owner, and none of those is claimed. The
  collaboration statement is preserved verbatim:

  > This research was developed in collaboration with SoccerSolver. SoccerSolver
  > currently works with more than 10 football clubs.

- The workspace was mapped and `problem_2` confirmed as MIT Sloan Problem 14.
  `problem_1` is a different project and is excluded.
- The revised final paper was read in full, and an earlier pre-review DOCX was
  inspected and rejected as superseded.
- Every headline claim was re-derived from the frozen result tables. All hold.
  Four over-broad framings were caught and narrowed; see section 6 of
  [`PUBLIC_RELEASE_AUDIT.md`](PUBLIC_RELEASE_AUDIT.md).
- Ruben's two reviewer points are applied and preserved: the motivation is a
  forecasting question with no policy reading, and Elo is a lagged match-result
  outcome rather than ground truth.
- The negative domestic-U23 result is stated as a statement about incremental
  forecast value, explicitly **not** as evidence that domestic youth development
  is ineffective.
- Data licensing was audited source by source. No raw or row-level data is
  published; reproducibility is classified **PARTIAL**.
- 20 code files were copied verbatim under `src/`. Mixed `problem_1` code and the
  mixed modelling-table builder were excluded.
- Two project-generated figures, seven aggregate result tables and a
  study-design table are published.
- Both required assets were supplied, copied and digest-pinned. See
  `assets/README.md`.
- `scripts/validate_public_package.py` re-derives every published headline
  number from the published tables, verifies links, images and asset digests, and
  runs the secret, restricted-content, portability and staged-scope scans.
- Full documentation is written: `README.md`, `docs/methodology.md`,
  `data/README.md`, `NOTICE.md`, `assets/README.md`, `paper/README.md`,
  `PUBLIC_RELEASE_AUDIT.md`, `LICENSE`, `CITATION.cff`, `requirements.txt`,
  `.gitignore`, `.gitattributes`, `src/README.md`.

## What a human must do

Nothing blocks publication. The only remaining decision is optional.

### Optional: decide the paper's fate

No paper file is published. Three items are unresolved, detailed in
[`paper/README.md`](paper/README.md):

- The venue's redistribution terms.
- Rights on the images embedded in the paper.
- The final DOCX, which was not found in the expected location. The definitive
  version exists only as a two-page PDF, and an available DOCX is a superseded
  pre-review draft.

Authorship is no longer among these; it is confirmed.

### Publishing mechanics

Git was installed via `winget` (`Git.Git`, version 2.55.0.windows.3) because it
was absent from the machine. The repository is initialised on `main`, and the
remote is the exact Problem 14 repository:

```
git remote add origin https://github.com/RupayanHalder39/MITSloanProblem14-home-or-abroad-player-exposure.git
git push -u origin main
```

The commands below are the intended sequence. `git push` has **not** been run
yet; it is performed only after the validator and the staged-file review pass,
and the resulting commit hash is recorded in the release record at the end of
this file.

After the push, `git status`, `git branch --show-current`, `git log --oneline -3`
and `git remote -v` confirm the final state. `.gitattributes` pins LF line
endings for every text file, so the published code stays byte-faithful to the
research workspace on any contributor's machine regardless of their
`core.autocrlf` setting. All 20 source files are byte-for-byte identical to the
research workspace originals, including line endings.

### Done, no action needed

- **Assets.** Both required images were supplied on 2026-09-28, copied into
  `assets/`, and verified byte-identical to the originals: `RupayanHalder.jpeg`
  (JPEG, 348 × 344) and `SoccerSolverLogo.png` (PNG, 819 × 306). Their digests
  and dimensions are pinned in the validator, which also fails on any other image
  in the tree. See `assets/README.md`.
- **Package.** Documentation, licence, notice, citation, requirements,
  `.gitignore`, `.gitattributes`, seven aggregate result tables, a study-design
  table, two figures, and 20 verbatim source files.

## Optional, still open

Decide the paper's fate. No paper file is published. Four items are unresolved,
detailed in [`paper/README.md`](paper/README.md):

- Venue redistribution terms.
- Rights on the images embedded in the paper.
- The final DOCX, which was not found in the expected location. The definitive
  version exists only as a two-page PDF, and an available DOCX is a superseded
  pre-review draft.

## Integrity checks already performed

| Check | Result |
|---|---|
| 20 published source files versus the research workspace | SHA-256 identical, 0 mismatches |
| 6 published result tables versus the authoritative originals | SHA-256 identical |
| `five_country_feature_ablation.csv` cross-checked against two independent originals | Identical to both |
| 2 published figures versus the generator output | SHA-256 identical |
| 2 supplied assets versus the originals in the research workspace | SHA-256 identical |
| Both assets decode as valid JPEG / PNG at the expected dimensions | Yes |
| Python compile check of all published code | Passes |
| Staged-file scope | 46 files, no data, no archive, no environment, no unapproved image |
| Validator tamper-tested | 30 deliberate mutations, all 30 caught; 4 controls stayed clean |
| Independent QA, separate from the validator | All checks pass (master untouched, byte-identity, secret and path scan) |
| Validator | All checks pass, no blockers |

The code copy is **verbatim**: no source file was edited, reindented or
reformatted, so the published code is the code that produced the published
tables.

## Optional improvements, in priority order

1. **Add a `LICENSE` decision for the paper** if it is ever published, since a
   conference licence and MIT are not the same thing.
2. **Independent standings cross-check.** football-data.co.uk was unreachable
   from the research environment and was not bypassed, so league standings have
   no second source. Verifying elite-club flags against it would strengthen the
   exposure definition.
3. **Per-federation coefficients.** One common OLS slope for all 90 federations
   is a real limitation. Federations with different baselines could support
   different slopes.
4. **A second outcome variable.** Elo is the only target. A second independent
   measure of national-team strength would test whether the increment survives.
5. **A non-linearity check.** A single linear term per feature is a strong
   restriction. Splines or bins would show whether the relationship is flat.
6. **Preregister the horizon.** The ablation flips sign between t+2 and t+3, so
   the "long-horizon" reading is partly a choice of where to stop. Declaring the
   horizon in advance would make it a finding rather than a selection.

## Things that are settled, and should not be reopened

- **Elo is not ground truth.** It is a lagged match-result outcome. Stated at the
  top of the README and in the methodology.
- **The signal is largely compositional.** The between-country component is the
  larger one at every horizon. This is the main constraint on the claims.
- **Within-country signal helps at t+1, is slightly harmful at t+2, and
  strengthens with the horizon.** The earlier "only at t+3 to t+5" phrasing was
  wrong and has been corrected everywhere.
- **No development model beats Elo from t+2 to t+5.** At t+1 the domestic
  opportunity index is 0.193 MAE lower, which is negligible and reverses. An
  earlier draft overstated this as "at any horizon"; the validator now asserts
  both halves so it cannot drift back.
- **The domestic hypothesis is not supported.** Domestic U23 elite opportunity
  did not improve the forecast at any horizon.
- **Group B domestic is missing, never zero.** All 1,146 Group B rows carry a
  missing value.
- **No data is published.** Licence position is not clear enough. Not
  revisitable without a legal opinion.
- **The figures are the project-generated ones**, not the paper's embedded
  renderings, because the published figures trace back to the published CSVs and
  the validator re-checks them.
- **Both assets are the ones supplied by the researcher**, digest-pinned. No
  substitute was ever used, and any other image is now a validation failure.

## Reproducing this state

```
python scripts/validate_public_package.py
```

Passing exit code 0 with no `BLOCKED` or `FAIL` lines is the current, intended
state: the package is internally consistent and complete except for the
authorship caveat, which is a human decision and not a defect. A non-zero exit
means something drifted and must be investigated before any publication step.
