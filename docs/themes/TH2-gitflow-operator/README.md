# TH2: Gitflow Operator

## Goal

Extend the Copilot Build Method with a mandatory `gitflow-operator` command
contract that current autopilot skills use for branch/MR/CI/release-note work
without repeated GitOps boilerplate.

## Definition of Done

- The build method documents that current autopilot skills MUST use
  `gitflow-operator` for Gitflow operations.
- The `gitflow-operator` command contract is specified and implemented or scaffolded
  according to the selected delivery architecture.
- Delivery items create one feature/fix branch per affected repo from `develop`.
- Completed delivery items return to `develop` through one squash commit.
- MR descriptions include release-note evidence for the delivery item.
