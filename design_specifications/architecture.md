# Architecture

## Technology Stack

- **Language**: Python 3.14+
- **Event Bus**: Redis (pub/sub)
- **Redis Client**: redis-py (async)
- **Validation**: Pydantic
- **Testing**: pytest
- **Package Manager**: uv
- **Container Runtime**: Podman Compose
- **Code Quality**: pyright, ruff

## Project Structure

```
src/
  modules/
    turn_manager.py
    ledger.py
    inventory.py
    factory.py
    market.py
  events/
    bus.py
    schemas.py
  utils/
    validation.py
    constants.py
  main.py
tests/
  test_turn_manager.py
  test_ledger.py
  test_inventory.py
  test_factory.py
  test_market.py
```

## External Agent Integration

External agents connect to the same Redis instance as internal modules via Pub/Sub.

- **Network**: All containers run in an isolated Podman network
- **Authentication**: None (Redis not exposed to host)
- **Connection**: Agents connect to `redis:6379` within the Podman network
- **Multiple agents**: Supported

**Security constraint**: Do not publish Redis port to host. The entire application must remain within the isolated Podman network.

## Testing Strategy

- **Unit tests**: Module logic in isolation with mocked event bus
- **Integration tests**: Event flows between modules with real Redis
- **E2E tests**: Full game simulation with hardcoded action sequences over multiple turns
