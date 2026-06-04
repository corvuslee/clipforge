# Decision 004: Rename Ledger to Purchasing

## Context

The `Ledger` module was implemented to track `fund`, `wire_cost`, and `autoclipper_cost`. However, the design specification only listed `fund` as Ledger state, indicating implementation drift from the original design.

An external agent (acting as procurement) needs visibility into costs (`wire_cost`, `autoclipper_cost`) to make informed purchasing decisions. This raises the question: should costs be tracked in Ledger, or should they be moved to a separate module?

## Decision

Rename the `Ledger` module to `Purchasing` to accurately reflect its responsibility: managing funds, costs, and purchase transactions.

## Rationale

1. **Cleaner Architecture**: Renaming is cleaner than splitting into two modules (one for fund, one for costs), which would add unnecessary complexity.

## Consequences

### Positive

- Module name accurately reflects its responsibilities

### Negative

- None identified

## Changes

- Design specifications updated to reflect the new module name
