# Interfaces Documentation

## External Agent Events

External agents interact via events defined in the respective modules:

**Transport**: Redis via Event Bus module. Agents use the same `publish`/`subscribe` API as internal modules.

**Connection Lifecycle**: Long-running process that subscribes at startup and stays connected throughout the game.

**Multiple Agents**: Supported. A single program can host multiple specialized agents (e.g., purchasing agent, pricing agent). Each agent handles distinct responsibilities with no overlap. The program emits one `plan_phase_completed` after all internal agents finish planning.

**Events Emitted**:
- To Purchasing: `buy_wire(count: int)`, `buy_autoclipper(count: int)`
- To Market: `set_price(price: float)`
- To Turn Manager: `plan_phase_completed()`

**Events Subscribed**:
- `planning_window_opened()` – from Turn Manager; signals agent can submit plans
- `inventory_state_reported(wire: int, unsold_clips: int, total_clips: int)` – from Inventory; provides current resource state
- `purchasing_state_reported(fund: int, wire_cost: float, autoclipper_cost: float)` – from Purchasing; provides current fund balance and costs
- `factory_state_reported(auto_clippers: int)` – from Factory; provides current production capacity
- `market_state_reported(price: float)` – from Market; provides current selling price

---

## Modules API

### Turn Manager

**Description**: Centralizes turn sequencing and time-step control

**State**:
- `turn_counter: int` – current turn number (starts at 1).
- `pending_state_reports: Set[str]` – modules yet to report state.
- `pending_action_completions: Set[str]` – modules yet to complete action phase.

**Invariants**:
- Turn counter increments monotonically
- Plan phase must complete before action phase

**API**:
- None

**Events Emitted**:
- `plan_phase_started()` – Signals start of planning phase; triggers modules to report state
- `planning_window_opened()` – Notifies external agent that planning actions can be submitted
- `action_phase_started()` – Signals start of action phase; triggers modules to execute queued actions
- `action_phase_completed()` – Signals end of action phase; turn is complete

**Events Subscribed**:
- `plan_phase_completed()` – from External Agent; signals planning is done, triggers action phase
- `purchasing_state_reported(fund: int, wire_cost: float, autoclipper_cost: float)` – from Purchasing; tracks pending state reports
- `inventory_state_reported(wire: int, unsold_clips: int, total_clips: int)` – from Inventory; tracks pending state reports
- `factory_state_reported(auto_clippers: int)` – from Factory; tracks pending state reports
- `market_state_reported(price: float)` – from Market; tracks pending state reports
- `purchasing_action_completed()` – from Purchasing; tracks pending action completions
- `inventory_action_completed()` – from Inventory; tracks pending action completions
- `factory_action_completed()` – from Factory; tracks pending action completions
- `market_action_completed()` – from Market; tracks pending action completions

**Errors**:
- `TurnSequenceError` – code `5101`, message `"Invalid turn transition"`.

### Purchasing

**Description**: Manages funds, costs, and purchase transactions.

**State**:
- `fund: int` – current cash balance.
- `wire_cost: float` – current wire cost per spool.
- `autoclipper_cost: float` – current autoclipper cost (derived from autoclipper count).

**Invariants**:
- Fund cannot go negative

**API**:
- `add_funds(amount: int)` – Add funds to purchasing.
- `remove_funds_for_wire(count: int)` – Remove funds for wire purchase. Returns actual count purchased.
- `remove_funds_for_autoclipper(count: int)` – Remove funds for autoclipper purchase. Returns actual count purchased.

**Events Emitted**:
- `purchasing_state_reported(fund: int, wire_cost: float, autoclipper_cost: float)` – Reports current state to subscribers
- `wire_purchase_approved(count: int)` – Confirms wire purchase validated; other modules can proceed
- `autoclipper_purchase_approved(count: int)` – Confirms autoclipper purchase validated; other modules can proceed
- `purchasing_action_completed()` – Signals purchasing has finished action phase processing

**Events Subscribed**:
- `plan_phase_started()` - from Turn Manager; triggers report of current state
- `buy_wire(count: int)` – from External Agent; queues wire purchase request for action phase
- `buy_autoclipper(count: int)` – from External Agent; queues autoclipper purchase request for action phase
- `action_phase_started()` – from Turn Manager; triggers processing of queued purchase requests
- `clips_sold(clips: int, revenue: int)` – from Market; adds revenue to fund balance

**Errors**:
- `InsufficientFundsError` – code `4101`, message `"Insufficient funds for requested operation"`.

### Inventory

**Description**: Tracks physical resources and production output.

**State**:
- `wire: int` – amount of raw wire available.
- `unsold_clips: int` – clips produced but not yet sold.
- `total_clips: int` – cumulative clips ever produced.

**Invariants**:
- Wire and unsold_clips cannot go negative
- total_clips is cumulative and never decreases

**API**:
- `add_wire(count: int) -> None` – Add wire to inventory.
- `remove_wire(count: int) -> None` – Remove wire from inventory.
- `add_clips(count: int) -> None` – Add clips to inventory.
- `remove_clips(count: int) -> None` – Remove clips from inventory.

**Events Emitted**:
- `inventory_state_reported(wire: int, unsold_clips: int, total_clips: int)` – Reports current wire, unsold clips, and total clips to subscribers
- `inventory_action_completed()` – Signals inventory has finished action phase processing

**Events Subscribed**:
- `plan_phase_started()` – from Turn Manager; triggers report of current state
- `wire_purchase_approved(count: int)` – from Purchasing; adds wire to inventory
- `wire_consumed(count: int)` – from Factory; removes wire from inventory
- `clips_produced(count: int)` – from Factory; adds clips to inventory
- `clips_sold(clips: int, revenue: int)` – from Market; removes sold clips from inventory

**Errors**:
- `InsufficientResourcesError` – code `4201`, message `"Not enough resources for requested operation"`.

### Factory

**Description**: Manages automated production capacity and clip manufacturing.

**State**:
- `auto_clippers: int` – number of automated clippers.
- `wire: int` – cached wire count from Inventory.

**Invariants**:
- auto_clippers cannot go negative

**API**:
- `add_autoclipper(count: int) -> None` – Add autoclippers.
- `remove_autoclipper(count: int) -> None` – Remove autoclippers.
- `produce_clips() -> None` – Produce clips.

**Events Emitted**:
- `factory_state_reported(auto_clippers: int)` – Reports current autoclipper count to subscribers
- `wire_consumed(count: int)` – Reports wire used for clip production
- `clips_produced(count: int)` – Reports clips manufactured this turn
- `factory_action_completed()` – Signals factory has finished action phase processing

**Events Subscribed**:
- `plan_phase_started()` – from Turn Manager; triggers report of current state
- `inventory_state_reported(wire: int, unsold_clips: int, total_clips: int)` – from Inventory; caches wire count for production calculation
- `autoclipper_purchase_approved(count: int)` – from Purchasing; adds autoclippers
- `action_phase_started()` – from Turn Manager; triggers clip production

**Errors**:
- `InsufficientCapacityError` – code `4301`, message `"Not enough autoclippers to remove"`.

### Market

**Description**: Handles pricing logic, demand modeling, and sales transactions.

**State**:
- `price: float` – current selling price.
- `auto_clippers: int` – current production capacity from Factory.
- `unsold_clips: int` – current inventory of unsold clips.

**Invariants**:
- Price must be a positive number

**API**:
- `set_price(price: float) -> None` – Set selling price.
- `process_sales() -> None` – Process sales and emit clips_sold event.

**Events Emitted**:
- `market_state_reported(price: float)` – Reports current selling price to subscribers
- `clips_sold(clips: int, revenue: int)` – Reports clips sold and revenue generated
- `market_action_completed()` – Signals market has finished action phase processing

**Events Subscribed**:
- `plan_phase_started()` – from Turn Manager; triggers report of current state
- `factory_state_reported(auto_clippers: int)` – from Factory; provides current production capacity
- `inventory_state_reported(wire: int, unsold_clips: int, total_clips: int)` – from Inventory; provides current inventory state
- `set_price(price: float)` – from External Agent; updates selling price
- `action_phase_started()` – from Turn Manager; triggers sales processing

**Errors**:
- `InvalidPriceError` – code `4401`, message `"Price must be a positive number"`.

### Shared Utilities

**Description**: Common validation logic for external user actions. Internal module actions are triggered by events and do not require re-validation.

**API**:
- `validate_action(action: ExternalAction, payload: dict) -> None` – Validate external action.

**External Actions**:
- `buy_wire(count: int)` – Purchase wire
- `buy_autoclipper(count: int)` – Purchase autoclipper
- `set_price(price: float)` – Set selling price

**Errors**:
- `ValidationError` – code `4001`, message "Action validation failed".

### Event Bus

**Description**: Message hub for publishing/subscribing to events via Redis pub/sub. See `src/events/schemas.py` for `Payload` and `EventName` type definitions.

**API**:
- `publish(event_name: EventName, payload: Payload, turn: int) -> None` – Publish an event.
- `subscribe(event_name: EventName, handler: Callable[[Payload], None]) -> None` – Subscribe to an event.
- `unsubscribe(event_name: EventName, handler: Callable[[Payload], None]) -> None` – Unsubscribe from an event.

**Errors**:
- `EventBusError` – code `5601`, message `"Event bus operation failed"`.
- `PublishError` – code `5602`, message `"Failed to publish event"`.
- `SubscribeError` – code `5603`, message `"Failed to subscribe to event"`.
