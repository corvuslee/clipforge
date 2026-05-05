# Module Specifications

> This system is event‑driven; modules communicate exclusively via the event bus.
>
> **API contracts, state, and event payloads**: See [interfaces.md](./interfaces.md).

## Turn Manager
**Description**: Centralizes turn sequencing and time-step control.

**Business Logic**:
- Turn counter increments monotonically
- Plan phase must complete before action phase
- All state reports must be received before opening planning window
- Turn-based sequencing ensures events are processed sequentially; no race conditions

## Ledger
**Description**: Manages financial resources and transaction tracking

**Business Logic**:
- Cannot remove more funds than available (insufficient funds error)
- Purchase requests are queued during plan phase, processed during action phase
- Revenue from sales is credited during action phase

## Inventory
**Description**: Tracks physical resources and production output

**Business Logic**:
- Wire and clips cannot go negative (insufficient resources error)
- `total_clips` is cumulative and never decreases
- Production consumes wire at a fixed rate per clip

## Factory
**Description**: Manages automated production capacity and clip manufacturing

**Business Logic**:
- Each autoclipper produces `CLIPS_PER_AUTOCLIPPER` clips per turn
- Wire is consumed at action phase start (before production)
- If insufficient wire, produce partial clips: `wire // WIRE_PER_CLIP`

## Market
**Description**: Handles pricing logic, demand modeling, and sales transactions

**Business Logic**:
- Price must be a positive number
- Demand is calculated based on price elasticity (hidden parameters)
- Sales limited by unsold clips available
- Revenue = clips sold × price

## Event Bus
**Description**: Facilitates all inter‑module communication via a Redis-based implementation with thin adapter layer.

**Business Logic**:
- All events are published asynchronously
- Event handlers are invoked in subscription order
- Event log persists for debugging/replay

## Shared Utilities

**validate_action()** – Common validation logic for external actions only
- Validates external agent requests before they reach modules
- Checks resource availability, state constraints, and action feasibility
- Internal module-to-module events are trusted and not re-validated

## Module Flows

### Planning Flow

```mermaid
sequenceDiagram
    participant TM as Turn Manager
    participant Ext as External Agent(s)
    participant Inv as Inventory
    participant Led as Ledger
    participant Fac as Factory
    participant Mar as Market

    TM->>TM: start_game (manual)
    TM-xAll: plan_phase_started (event)
    note over All: broadcast to all subscribers
    
    Inv-xAll: inventory_state_reported (event)
    Led-xAll: ledger_state_reported (event)
    Fac-xAll: factory_state_reported (event)
    Mar-xAll: market_state_reported (event)
    note over All: broadcast to Turn Manager and corresponding External Agent(s)
    
    TM-xExt: planning_window_opened (event)
    note over Ext: Planning works
    Ext-xTM: plan_phase_completed (event)
```

### Actions Flow

```mermaid
sequenceDiagram
    participant TM as Turn Manager
    participant Ext as External Agent(s)
    participant Led as Ledger
    participant Inv as Inventory
    participant Fac as Factory
    participant Mar as Market

    TM-xAll: action_phase_started (event)

    %% Modules signal completion
    Led-xTM: ledger_action_completed (event)
    Inv-xTM: inventory_action_completed (event)
    Fac-xTM: factory_action_completed (event)
    Mar-xTM: market_action_completed (event)

    TM->>TM: action_phase_completed (event)
```


### Set Price Flow

```mermaid
sequenceDiagram
    participant TM as Turn Manager
    participant Ext as External Agent(s)
    participant Mar as Market

    TM-xExt: planning_window_opened (event)
    Ext-xMar: set_price (event)
    Mar->>Mar: set_price()
```

### Wire Purchase Flow

```mermaid
sequenceDiagram
    participant TM as Turn Manager
    participant Ext as External Agent(s)
    participant Led as Ledger
    participant Inv as Inventory

    TM-xExt: planning_window_opened (event)
    Ext-xLed: buy_wire (event)
    TM-xLed: action_phase_started (event)
    Led->>Led: remove_funds_for_wire()
    Led-xInv: wire_purchase_approved (event)
    Inv->>Inv: add_wire()
```


### Autoclipper Purchase Flow

```mermaid
sequenceDiagram
    participant TM as Turn Manager
    participant Ext as External Agent(s)
    participant Led as Ledger
    participant Fac as Factory

    TM-xExt: planning_window_opened (event)
    Ext-xLed: buy_autoclipper (event)
    TM-xLed: action_phase_started (event)
    Led->>Led: remove_funds_for_autoclipper()
    Led-xFac: autoclipper_purchase_approved (event)
    Fac->>Fac: add_autoclipper()
```

### Clip Sales Flow

```mermaid
sequenceDiagram
    participant TM as Turn Manager
    participant Mar as Market
    participant Inv as Inventory
    participant Fac as Factory
    participant Led as Ledger

    Note over Mar,Fac: Planning Phase
    Inv-xMar: inventory_state_reported (event)
    Fac-xMar: factory_state_reported (event)

    Note over Mar,Led: Action Phase
    TM-xMar: action_phase_started (event)
    Mar->>Mar: process_sales()
    Mar-xInv: clips_sold (event)
    Inv->>Inv: remove_clips()
    Mar-xLed: clips_sold (event)
    Led->>Led: add_funds()
```

### Production Flow

```mermaid
sequenceDiagram
    participant TM as Turn Manager
    participant Fac as Factory
    participant Inv as Inventory

    Note over Fac,Inv: Planning Phase
    Inv-xFac: inventory_state_reported (event)

    Note over Fac,Inv: Action Phase
    TM-xFac: action_phase_started (event)
    Fac->>Fac: produce_clips()
    Fac-xInv: wire_consumed (event)
    Inv->>Inv: remove_wire()
    Fac-xInv: clips_produced (event)
    Inv->>Inv: add_clips()
```
