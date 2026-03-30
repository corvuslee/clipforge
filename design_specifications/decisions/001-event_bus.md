# Decision 001 – Event Bus Implementation

## Options Evaluated
1. **BYO (custom in‑process) bus**
2. **Redis Pub/Sub / Streams**
3. **Kafka**

## Decision
Use **Redis** as the event bus – minimal deployment, cross‑process, optional durability.

## Why Redis fits
- TCP‑based broker, lets AI agents connect remotely.
- Streams add optional durable replay.
- Multi‑language client support.
- Deployable as a single container.

## Why Kafka could be considered (but not chosen)
- Strong ordering, replication, replay.
- Handles high throughput and many consumers.
- Needs a cluster and adds latency/complexity – unnecessary for this turn‑based use case.

## Why BYO fails for AI agents
- In‑process only – no external access.
- No network endpoint, no durability.
- Cannot scale to multiple agents.
