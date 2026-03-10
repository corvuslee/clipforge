# World Model

Modules:
- Inventory — wire, unsold_clips, total_clips
- Treasury — money
- Market — price, demand, handles sales
- Factory — auto_clippers, handles production

Event Bus:
- Events are facts (validate before publishing)
- All module communication goes through the bus
- Full event log per turn

Actions (interface):
- set_price(value)
- buy_wire(amount)
- buy_autoclipper
- make_clip
- wait

Turn Sequence:
1. Receive actions (from any controller — LLM, script, human)
2. Execute actions, publish events
3. End-of-turn: auto-production, sales
4. Emit world snapshot + event log

Episode: turn limit or clip target

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# LLM Layer

Agents (turn order):
1. Pricing — sets price
2. Purchasing — buys wire or auto-clippers
3. Production — manually makes clips

Agent I/O:
- Input: world snapshot + own event history + own comment history
- Output: {"action": "...", "value": ..., "comment": "..."}

Visibility:
- Agents see world module events only, not each other's
- Agent's own comments serve as self-memory

Reward: total clips produced