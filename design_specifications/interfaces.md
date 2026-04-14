# Interfaces Documentation

## External Agent Events

External agents interact via events defined in the respective modules:

**Events Emitted**:
- To Ledger: `buy_wire(count: int)`, `buy_autoclipper(count: int)`
- To Market: `set_price(price: float)`
- To Turn Manager: `plan_phase_completed(turn_counter: int)`

**Events Subscribed**:
- `planning_window_opened(turn_counter: int)` – from Turn Manager; signals agent can submit plans
- `inventory_state_reported(wire: int, unsold_clips: int, total_clips: int)` – from Inventory; provides current resource state
- `ledger_state_reported(fund: int)` – from Ledger; provides current fund balance
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

**API**:
- `start_game() -> None` – Initialize game and emit `plan_phase_started`.

**Events Emitted**:
- `plan_phase_started(turn_counter: int)` – Signals start of planning phase; triggers modules to report state
- `planning_window_opened(turn_counter: int)` – Notifies external agent that planning actions can be submitted
- `action_phase_started(turn_counter: int)` – Signals start of action phase; triggers modules to execute queued actions
- `action_phase_completed(turn_counter: int)` – Signals end of action phase; turn is complete

**Events Subscribed**:
- `plan_phase_completed(turn_counter: int)` – from External Agent; signals planning is done, triggers action phase
- `ledger_state_reported(fund: int)` – from Ledger; tracks pending state reports
- `inventory_state_reported(wire: int, unsold_clips: int, total_clips: int)` – from Inventory; tracks pending state reports
- `factory_state_reported(auto_clippers: int)` – from Factory; tracks pending state reports
- `market_state_reported(price: float)` – from Market; tracks pending state reports
- `ledger_action_completed()` – from Ledger; tracks pending action completions
- `inventory_action_completed()` – from Inventory; tracks pending action completions
- `factory_action_completed()` – from Factory; tracks pending action completions
- `market_action_completed()` – from Market; tracks pending action completions

**Errors**:
- `TurnSequenceError` – code `5101`, message `"Invalid turn transition"`.

### Ledger

**Description**: Central ledger handling the system's monetary resources.

**State**:
- `fund: int` – current cash balance.

**API**:
- `add_funds(amount: int) -> None` – Add funds to ledger.
- `remove_funds_for_wire(amount: int) -> None` – Remove funds for wire purchase.
- `remove_funds_for_autoclipper(amount: int) -> None` – Remove funds for autoclipper purchase.

**Events Emitted**:
- `ledger_state_reported(fund: int)` – Reports current fund balance to subscribers
- `wire_purchase_approved(count: int)` – Confirms wire purchase validated; other modules can proceed
- `autoclipper_purchase_approved(count: int)` – Confirms autoclipper purchase validated; other modules can proceed
- `ledger_action_completed()` – Signals ledger has finished action phase processing

**Events Subscribed**:
- `plan_phase_started(turn_counter: int)` - from Turn Manager; triggers report of current state
- `buy_wire(count: int)` – from External Agent; queues wire purchase request for action phase
- `buy_autoclipper(count: int)` – from External Agent; queues autoclipper purchase request for action phase
- `action_phase_started(turn_counter: int)` – from Turn Manager; triggers processing of queued purchase requests
- `clips_sold(clips: int, revenue: int)` – from Market; adds revenue to fund balance

**Errors**:
- `InsufficientFundsError` – code `4101`, message `"Insufficient funds for requested operation"`.

### Inventory

**Description**: Tracks physical resources and production output.

**State**:
- `wire: int` – amount of raw wire available.
- `unsold_clips: int` – clips produced but not yet sold.
- `total_clips: int` – cumulative clips ever produced.

**API**:
- `add_wire(count: int) -> None` – Add wire to inventory.
- `remove_wire(count: int) -> None` – Remove wire from inventory.
- `add_clips(count: int) -> None` – Add clips to inventory.
- `remove_clips(count: int) -> None` – Remove clips from inventory.

**Events Emitted**:
- `inventory_state_reported(wire: int, unsold_clips: int, total_clips: int)` – Reports current wire, unsold clips, and total clips to subscribers
- `inventory_action_completed()` – Signals inventory has finished action phase processing

**Events Subscribed**:
- `plan_phase_started(turn_counter: int)` – from Turn Manager; triggers report of current state
- `wire_purchase_approved(count: int)` – from Ledger; adds wire to inventory
- `wire_consumed(count: int)` – from Factory; removes wire from inventory
- `clips_produced(count: int)` – from Factory; adds clips to inventory
- `clips_sold(clips: int, revenue: int)` – from Market; removes sold clips from inventory

**Errors**:
- `InsufficientResourcesError` – code `4201`, message `"Not enough resources for requested operation"`.

### Factory

**Description**: Manages automated production capacity and clip manufacturing.

**State**:
- `auto_clippers: int` – number of automated clippers.

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
- `plan_phase_started(turn_counter: int)` – from Turn Manager; triggers report of current state
- `autoclipper_purchase_approved(count: int)` – from Ledger; adds autoclippers
- `action_phase_started(turn_counter: int)` – from Turn Manager; triggers clip production

**Errors**:
- `InsufficientCapacityError` – code `4301`, message `"Not enough autoclippers to remove"`.

### Market

**Description**: Handles pricing logic, demand modeling, and sales transactions.

**State**:
- `price: float` – current selling price.
- `demand_parameters` – hidden internal parameters controlling price elasticity and base demand (e.g., `elasticity: float`, `base_demand: int`).

**API**:
- `set_price(price: float) -> None` – Set selling price.
- `process_sales() -> None` – Process sales.

**Events Emitted**:
- `market_state_reported(price: float)` – Reports current selling price to subscribers
- `clips_sold(clips: int, revenue: int)` – Reports clips sold and revenue generated
- `market_action_completed()` – Signals market has finished action phase processing

**Events Subscribed**:
- `plan_phase_started(turn_counter: int)` – from Turn Manager; triggers report of current state
- `set_price(price: float)` – from External Agent; updates selling price
- `action_phase_started(turn_counter: int)` – from Turn Manager; triggers sales processing

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

**Description**: Message hub for publishing/subscribing to events. `publish(event_name, payload)` emits an event; `subscribe(event_name, handler)` registers a handler.

**API**:
- `publish(event_name: str, payload: Mapping[str, Any]) -> None` – Publish an event.
- `subscribe(event_name: str, handler: Callable[[Mapping[str, Any]], None]) -> None` – Subscribe to an event.
- `unsubscribe(event_name: str, handler: Callable[[Mapping[str, Any]], None]) -> None` – Unsubscribe from an event.
- `close() -> None` – Close the connection to event bus.

**Errors**:
- `EventBusError` – code `5601`, message `"Event bus operation failed"`.
- `PublishError` – code `5602`, message `"Failed to publish event"`.
- `SubscribeError` – code `5603`, message `"Failed to subscribe to event"`.
