# Domain Ontology

## Lifecycle concepts

| Concept | Meaning |
|---|---|
| Vision outcome | User or product value sought without a solution commitment |
| Discovery | Bounded evidence gathering and human decision-making before PRD finalization |
| PRD | Human-approved observable product behavior, constraints, exclusions, and success measures |
| Architecture | Components, interfaces, ownership, technical contracts, and decisions that satisfy the PRD |
| Planning | Decomposition of accepted architecture and requirements into deliverable stories |
| Autopilot | Governed implementation, verification, review, recovery, and delivery |

## Discovery records

| Prefix | Record | Meaning |
|---|---|---|
| `VO-` | Vision outcome | Desired user or product result |
| `DQ-` | Discovery question | Consequential uncertainty requiring evidence or a choice |
| `EXP-` | Experiment | Bounded investigation with budget and stop condition |
| `EV-` | Evidence | Traceable observation, source, or experimental result |
| `ASM-` | Assumption | Condition accepted as true enough to proceed |
| `DEC-` | Decision | Explicitly accepted outcome that constrains downstream work |
| `INV-` | Invariant | Condition the product or method must preserve |
| `RSK-` | Risk | Uncertain event or condition with impact and treatment |
| `DEF-` | Deferral | Governed decision not to resolve an item now |
| `DR-` | Discovery Revision | Append-only correction after an accepted Discovery gate |
| `PR-` | Product requirement | Approved, measurable product behavior or constraint |
| `PCR-` | Product change record | Append-only change to an approved PRD |

## Evidence classifications

| Classification | Rule |
|---|---|
| `observed` | Reproducible source, runtime observation, or experiment |
| `inferred` | Reasoned conclusion with cited evidence and stated boundary |
| `hypothesis` | Plausible claim still requiring validation |
| `assumption` | Condition explicitly accepted to proceed |
| `preference` | Human-selected focus, simplification, or trade-off |
| `decision` | Explicit accepted outcome |
| `unknown` | Open question with owner and disposition |

A hypothesis cannot constrain a PRD until it is validated or explicitly
accepted as an assumption.

## Cross-phase traceability

```text
VO-### -> DQ-### -> EV/ASM/DEC/INV/RSK -> PR-### -> ADR-### ->
TH#.E#.US# -> verification and release evidence
```

Item-level traceability is required for consequential records. Low-impact
details may use document-level references.

## Discovery escape

A Discovery escape is a foundational unknown, false assumption, missing
invariant, or external constraint discovered after the readiness gate. It is
not an ordinary implementation defect, test defect, estimation error, or new
scope request.

