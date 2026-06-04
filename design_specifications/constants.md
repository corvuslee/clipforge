# Constants

## Initial State

| Item               | Starting value |
| ------------------ | -------------- |
| `fund`             | $0.00          |
| `wire_inch`        | 150            |
| `wire_cost`        | $20.00         |
| `autoclipper_cost` | $50.00         |
| `clip_price`       | $0.05          |
| `auto_clippers`    | 1              |
| `unsold_clips`     | 0              |
| `total_clips`      | 0              |

## Wire Cost Function

Wire cost has two components: a drifting base cost and random fluctuation.

### Constants

| Constant              | Description                          | Value  |
| --------------------- | ------------------------------------ | ------ |
| `WIRE_COST_MIN`       | Minimum cost per spool               | $15.00 |
| `WIRE_COST_INCREASE`  | Base cost increase per purchase      | $0.50  |
| `WIRE_COST_DECAY`     | Base cost decrease per turn (no buy) | $0.25  |
| `WIRE_NOISE_STD_DEV`  | Standard deviation of cost noise     | $1.00  |
| `WIRE_INCH_PER_SPOOL` | Wire inch per spool                  | 1000   |

### Mechanics

**Base cost drift:**
- Increases by `WIRE_COST_INCREASE` each time wire is purchased
- Decreases by `WIRE_COST_DECAY` per turn when no wire purchased 
- Floors at `WIRE_COST_MIN`

**Random fluctuation:**
- Normal distribution with mean = 0, standard deviation = `WIRE_NOISE_STD_DEV`
- Applied at the start of each plan phase, so agents see the current cost before making decisions

**Per-inch cost**: `wire_cost / WIRE_INCH_PER_SPOOL`

## AutoClipper Cost Function

AutoClipper cost scales exponentially with current count.

| Constant                  | Description               | Value  |
| ------------------------- | ------------------------- | ------ |
| `AUTOCLIPPER_BASE_COST`   | Cost of first autoclipper | $50.00 |
| `AUTOCLIPPER_GROWTH_RATE` | Exponential growth factor | 1.004  |

**Formula**: `autoclipper_cost = AUTOCLIPPER_BASE_COST × AUTOCLIPPER_GROWTH_RATEᴬ` where A = current autoclipper count

**Pricing behavior**:
- All autoclippers purchased in the same batch cost the same price (the current `autoclipper_cost`)
- Price increases for the next turn after purchase count is updated

## Production Function

| Constant                | Description                                | Value |
| ----------------------- | ------------------------------------------ | ----- |
| `CLIPS_PER_AUTOCLIPPER` | Clips produced by one autoclipper per turn | 30    |
| `WIRE_PER_CLIP`         | Wire inch consumed to produce one clip     | 1     |

## Demand Function

Demand determines the fraction of available clips that sell each turn. It is a function of price, production capacity, and inventory level.

### Constants

| Constant                     | Description                                        | Value |
| ---------------------------- | -------------------------------------------------- | ----- |
| `BASE_DEMAND`                | Baseline demand multiplier                         | 0.38  |
| `PRICE_FACTOR_PEAK`          | Maximum price factor at price=0                    | 2.0   |
| `PRICE_FACTOR_SIGMA`         | Width of Gaussian price curve                      | 0.04  |
| `AUTOCLIPPER_FACTOR`         | Demand boost per autoclipper (logarithmic)         | 0.10  |
| `INVENTORY_THRESHOLD_FACTOR` | Days of inventory that halves demand (ratio-based) | 2.0   |
| `DEMAND_NOISE_STD_DEV`       | Standard deviation of demand random fluctuation    | 0.02  |

**Bounds:**
- Demand is clamped to the range [0, 1]
- Values below 0 are set to 0 (no sales)
- Values above 1 are set to 1 (sell all available clips)

### Mechanics

**Price factor (Gaussian curve):**
- Uses Gaussian curve for bounded behavior
- Formula: `price_factor = PRICE_FACTOR_PEAK × exp(-(clip_price²)/(2×PRICE_FACTOR_SIGMA²))`
- At high prices: price_factor decays to 0 (no floor)

**Autoclipper influence:**
- Logarithmic scaling (`log1p`)
- Diminishing returns prevent autoclippers from overwhelming other factors
- Each additional autoclipper contributes less than the previous one

**Clip inventory penalty (ratio-based):**
- Penalizes holding excess unsold clips relative to production capacity
- Formula: `demand_multiplier = 1 / (1 + unsold_clips / (daily_production × INVENTORY_THRESHOLD_FACTOR))`
- `daily_production = auto_clippers × CLIPS_PER_AUTOCLIPPER`
- `INVENTORY_THRESHOLD_FACTOR = 2.0` means 2 days of inventory halves demand
- Creates equilibrium pressure between production and sales

**Sales calculation:**
- Clip sales calculation solely based on `unsold_clips`
- Clips produced in the current turn are only sellable in the next turn
