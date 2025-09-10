# Binance Bot

A Python-based trading bot for Binance supporting limit, market, stop-limit, grid, OCO, and TWAP orders.

## Features

- Connects to Binance API (supports testnet)
- Modular order types: limit, market, stop-limit, grid, OCO, TWAP
- Input validation and error handling
- Logging and utility functions

## Setup

1. **Clone the repository:**
   ```shell
   git clone https://github.com/Mythripaluri/binance_bot.git
   cd binance_bot
   ```

2. **Install dependencies:**
   ```shell
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Create a `.env` file in the project root:
     ```
     BINANCE_API_KEY=your_api_key_here
     BINANCE_API_SECRET=your_api_secret_here
     USE_TESTNET=true
     DEFAULT_SYMBOL=BTCUSDT
     POSITION_MODE=ONE_WAY
     ```

## Usage

Run the main script:
```shell
python src/main.py
```

## Project Structure

```
src/
  binance_client.py
  main.py
  validators.py
  advanced/
    grid.py
    oco.py
    twap.py
  orders/
    limit_orders.py
    market_orders.py
    shared.py
    stop_limit.py
  utils/
    common.py
    logger.py
```

## Notes

- **Do not share your `.env` file or API keys.**
- For testnet trading, set `USE_TESTNET=true` in `.env`.

##
