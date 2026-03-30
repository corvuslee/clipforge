# World Model Capabilities

## Core Capabilities
- Simulate a paperclip production business ecosystem
- Model economic interactions (supply/demand, pricing, production)
- Provide turn-based decision making interface
- Track resource flows (money, materials, products)
- Enforce business rules and constraints
- Generate observable state for AI agents
- Log all events for analysis and debugging

## Key Features
- Multi-module architecture with clear separation of concerns
- Event-driven communication pattern
- Validation and error handling
- State persistence and snapshot capability
- Configurable parameters (hidden from agents)
- Support for multiple concurrent agents

## Modules
- **Inventory**: wire, unsold_clips, total_clips
- **Treasury**: money
- **Market**: price, demand, sales processing
- **Factory**: auto_clippers, production handling
- **Turn Manager**: turn_counter, turn progression control

## System Flow
1. Receive actions (from any controller — LLM, script, human)
2. Execute actions with validation
3. Process end-of-turn operations (auto-production, sales)
4. Emit world state snapshot + event log

## Constraints
- Maximum 3 manual clips per turn
- Hidden internal parameters (costs, demand curves)
- All inter-module communication via event bus
- Failure events for invalid operations