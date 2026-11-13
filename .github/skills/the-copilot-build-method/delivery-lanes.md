# Delivery lanes: local usage

The [canonical method](SKILL.md) owns classification and authority. Use the
source checkout's `bin/method` from the project checkout being changed, or
pass `lane --repo /target/checkout` before its action (the
existing CLI default for validation/packet commands is still the tool
checkout). Lane records are local working evidence, not a product backlog.
No command below installs, pushes, merges, deploys or releases.

## Direct: documentation or routine fix

Run from the target Git checkout. No handwritten brief or planning hierarchy:

```sh
/path/to/copilotautopilot/bin/method lane start \
  --task readme-fix --owner developer \
  --outcome "Correct the documented command" --scope README.md \
  --acceptance "The command matches actual CLI help" --check cli-help \
  --kind docs --design existing --certainty clear --risk R0
```

Retain the returned `revision` outside the generated record; replace it only
with the result of an authorized subsequent command. Preflight **before**
implementation and on resume:

```sh
METHOD=/path/to/copilotautopilot/bin/method
$METHOD lane preflight --task readme-fix --owner developer \
  --expected-revision "$REVISION"
# Implement the README correction, then perform its real acceptance check.
$METHOD lane check --task readme-fix --owner developer \
  --expected-revision "$REVISION" --name cli-help --covered AC1 \
  -- "$METHOD" --help
```

Choose a command that actually tests the criterion; a successful help command
alone cannot prove that a README agrees with it. Record the owner's actual
comparison/self-review in, for example,
`docs/plan/runtime/lanes/readme-fix-review.md` (excluded from implementation
fingerprinting). Do not fabricate the report or reviewer:

```sh
$METHOD lane review --task readme-fix --owner developer \
  --expected-revision "$REVISION" --reviewer developer --verdict approved \
  --report docs/plan/runtime/lanes/readme-fix-review.md
$METHOD lane complete --task readme-fix --owner developer \
  --expected-revision "$REVISION" \
  --gitflow "not-applicable: local implementation only; no delivery authorized"
```

Every command returns a new revision. Completion is implementation completion,
not release readiness, product acceptance or production activation.
For documentation with no executable check, use an explicit verifiable
documentation/consistency inspection; document what it can and cannot prove.

## Managed: established feature across sessions

An optional JSON brief is useful for larger scopes. For example:

```json
{
  "task": "catalog-filter",
  "owner": "developer",
  "outcome": "Implement the already accepted catalog filtering behavior",
  "scope": ["src/catalog", "tests/catalog"],
  "non_goals": ["No new access-control behavior", "No deployment"],
  "acceptance": ["Only matching records are returned", "Existing pagination works"],
  "checks": ["filter-unit"],
  "integration_checks": ["catalog-integration"],
  "kind": "feature",
  "design": "existing",
  "design_evidence": ["docs/accepted-catalog-design.md"],
  "certainty": "clear",
  "risk": "R2",
  "multi_session": true
}
```

```sh
$METHOD lane assess --brief /path/to/brief.json
$METHOD lane start --brief /path/to/brief.json
```

The evidence must describe the actual accepted design; file existence does
not establish acceptance. No new product/design decision may be hidden under
`design: existing`. Non-goals, integration checks and design evidence are
required for Managed. Run each named check using explicit command arguments,
with `--covered AC1 --covered AC2` as appropriate. R2 or adversarial/critical
review requires a real independent actor/report and `--independent`.

Resume the record with the same owner and retained revision. It retains
outcome, non-goals, criteria, checks, evidence, actual progress and next action,
without adding a theme or duplicating backlog status.

## Escalation, failures and refusal

```sh
$METHOD lane pause --task catalog-filter --owner developer \
  --expected-revision "$REVISION" --reason "Dependency unavailable"
$METHOD lane resume --task catalog-filter --owner developer \
  --expected-revision "$REVISION"
# To change scope/risk/criteria, submit a complete revised brief:
$METHOD lane amend --brief /path/to/revised-brief.json \
  --expected-revision "$REVISION"
```

Amendment preserves prior scope, owner, history and the highest selected lane;
it pauses work and clears old verification/review. Resume is explicit and
refuses uncertainty or Governed requirements. Changed out-of-scope files block
execution; an explicit scope amendment may include an expansion but may not
authorize unrelated changes or erase history.

Checks retain real exit status and output hashes, not output text or secrets.
A failure exits `2`, preserves failure evidence and cannot complete. Mark
an attempted repair with `lane check --repair`; after two unsuccessful repairs,
pause for specialist/human disposition. A required review `request-changes`
pauses for owner repair; it is never completion. Record an actual authority
refusal using `pause --authority-refused`; lighter resume is then unavailable.
A new overlapping task cannot reset unfinished/refused evidence.

## Governed: authorization, migration or production operation

```sh
$METHOD lane assess --task access-policy --owner developer \
  --outcome "Implement the approved access-policy change locally" \
  --scope src/access --acceptance "Denied requests remain denied" \
  --check access-regression --kind feature --design existing \
  --certainty clear --risk R3 --trigger authorization
```

This returns `Governed`, a packet route and closed local execution. Requesting
`--lane Direct` cannot lower it. `start` can retain the paused handoff evidence,
but `check`, `resume` and `complete` cannot execute it as lighter work.
Obtain explicit human scope/authority, satisfy applicable product/design gates,
and use the existing `method packet project/build/preflight/verify/reconcile`
protocol with caller-retained authorization hashes. Reuse valid accepted
upstream evidence; do not fabricate a replacement greenfield lifecycle.
Recovery/rollback and independent review are required where applicable.

Locally implementing migration tooling is not permission to run a migration;
implementing access administration is not permission to grant access.
Deployment, release, merge and production activation require their own human
authority. A lane command never grants those operations.

## Compatibility and limits

Admitted v1/v2/v3 work defaults to the existing packet protocol. A brief naming
`admitted_item` routes to packets; a legacy story grant remains story-scoped.
Do not create a lighter record for work already admitted or refused through
another gate. The lane route cannot modify a product backlog or waive its
verification/review gates. Accepted/frozen product artefacts stay protected.

The compact route requires Git and a bounded regular-file inventory, rejects
symlinks, uses an exclusive writer lock and caller-retained revision, and
refuses oversized evidence. It is not an OS sandbox or identity service:
commands are explicit caller inputs and must be safe verification, attribution
must come from real human/reviewer evidence, and semantic classification needs
honest owner assessment. Machine hashes bind evidence, not human authenticity.
Stale/missing retained revisions require explicit recovery, not automatic
trust in edited state. Package/install/activation is a separate approved task;
installed/global or other workspace instructions may remain older until then.

The inventory includes Git-ignored files. For checks that generate artifacts,
declare optional `verification_outputs` in the brief (or repeat
`--verification-output`, e.g. `--verification-output .pytest_cache`).
These explicit output-only write grants are excluded from the implementation
digest, may not overlap implementation/design/control paths, and cannot be
expanded by amendment to hide a violation. Run from the Git checkout root.
Repositories with unfinished product backlog work conservatively refuse local
lane entry: code paths alone cannot prove the assignment unrelated. Use the
existing packet/admission authority, not an omitted `admitted_item`.
