import click
from tabulate import tabulate
from .utils.logger import get_logger
from .binance_client import get_client
from .validators import OrderBase, LimitOrder, StopLimitOrder, OCOOrder, TWAPParams, GridParams
from .orders.market_orders import place_market_order
from .orders.limit_orders import place_limit_order
from .orders.stop_limit import place_stop_limit
from .advanced.oco import place_oco
from .advanced.twap import run_twap
from .advanced.grid import run_grid

logger = get_logger()

@click.group()
def cli():
    """Binance USDT-M Futures CLI Bot"""
    pass

# --- Account Info Commands ---
@cli.command()
def account():
    """Check account information (balances, margin, etc.)"""
    client = get_client()
    try:
        resp = client.account()
        click.echo(resp)
    except Exception as e:
        logger.error(f"Failed to fetch account info: {e}")
        click.echo("Error fetching account info")

@cli.command()
@click.argument("symbol")
def orders(symbol):
    """Check open orders for a symbol"""
    client = get_client()
    try:
        resp = client.get_orders(symbol=symbol.upper())
        click.echo(tabulate(resp, headers="keys"))
    except Exception as e:
        logger.error(f"Failed to fetch orders for {symbol}: {e}")
        click.echo(f"Error fetching orders for {symbol}")

@cli.command()
@click.argument("symbol")
def positions(symbol):
    """Check positions for a symbol"""
    client = get_client()
    try:
        resp = client.get_position_risk(symbol=symbol.upper())
        click.echo(tabulate(resp, headers="keys"))
    except Exception as e:
        logger.error(f"Failed to fetch positions for {symbol}: {e}")
        click.echo(f"Error fetching positions for {symbol}")

# --- Market Commands ---
@cli.command()
def ping():
    """Ping the exchange and print server time"""
    client = get_client()
    try:
        pong = client.ping()
        server_time = client.time()
        click.echo(f"Ping: {pong}, Server Time: {server_time}")
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        click.echo("Error pinging server")

@cli.command()
@click.argument("symbol")
def price(symbol):
    """Get latest price for a symbol"""
    client = get_client()
    try:
        r = client.ticker_price(symbol=symbol.upper())
        click.echo(r)
    except Exception as e:
        logger.error(f"Failed to fetch price for {symbol}: {e}")
        click.echo(f"Error fetching price for {symbol}")

# --- Orders Group ---
@cli.group()
def order():
    """Place basic and advanced orders"""
    pass

@order.command("market")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
def order_market(symbol, side, qty):
    try:
        data = OrderBase(symbol=symbol.upper(), side=side.upper(), qty=qty)
        resp = place_market_order(data)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Market order failed: {e}")
        click.echo("Error placing market order")

@order.command("limit")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--price", required=True, type=float)
@click.option("--tif", default="GTC", show_default=True)
def order_limit(symbol, side, qty, price, tif):
    try:
        data = LimitOrder(symbol=symbol.upper(), side=side.upper(), qty=qty, price=price)
        resp = place_limit_order(data, tif=tif)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Limit order failed: {e}")
        click.echo("Error placing limit order")

@order.command("stop-limit")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--stop", required=True, type=float)
@click.option("--price", required=True, type=float)
@click.option("--tif", default="GTC", show_default=True)
def order_stop_limit(symbol, side, qty, stop, price, tif):
    try:
        data = StopLimitOrder(symbol=symbol.upper(), side=side.upper(), qty=qty, stop=stop, price=price)
        resp = place_stop_limit(data, tif=tif)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Stop-limit order failed: {e}")
        click.echo("Error placing stop-limit order")

@order.command("oco")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--tp", required=True, type=float)
@click.option("--sl", required=True, type=float)
def order_oco(symbol, side, qty, tp, sl):
    try:
        data = OCOOrder(symbol=symbol.upper(), side=side.upper(), qty=qty, tp=tp, sl=sl)
        resp = place_oco(data)
        click.echo(resp)
    except Exception as e:
        logger.error(f"OCO order failed: {e}")
        click.echo("Error placing OCO order")

# --- Strategies Group ---
@cli.group()
def strat():
    """Run strategies (TWAP, Grid)"""
    pass

@strat.command("twap")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--slices", required=True, type=int)
@click.option("--duration", required=True, type=int, help="seconds")
def strat_twap(symbol, side, qty, slices, duration):
    try:
        params = TWAPParams(symbol=symbol.upper(), side=side.upper(), qty=qty, slices=slices, duration=duration)
        resp = run_twap(params)
        click.echo(tabulate([{ "slice": i+1, "result": r } for i, r in enumerate(resp)], headers="keys"))
    except Exception as e:
        logger.error(f"TWAP strategy failed: {e}")
        click.echo("Error running TWAP strategy")

@strat.command("grid")
@click.option("--symbol", required=True)
@click.option("--qty", required=True, type=float)
@click.option("--lower", required=True, type=float)
@click.option("--upper", required=True, type=float)
@click.option("--levels", required=True, type=int)
def strat_grid(symbol, qty, lower, upper, levels):
    try:
        params = GridParams(symbol=symbol.upper(), qty=qty, lower=lower, upper=upper, levels=levels)
        resp = run_grid(params)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Grid strategy failed: {e}")
        click.echo("Error running Grid strategy")

if __name__ == "__main__":
    cli()











# import click
# from tabulate import tabulate
# from .utils.logger import get_logger
# from .binance_client import get_client
# from .validators import OrderBase, LimitOrder, StopLimitOrder, OCOOrder, TWAPParams, GridParams
# from .orders.market_orders import place_market_order
# from .orders.limit_orders import place_limit_order
# from .orders.stop_limit import place_stop_limit
# from .advanced.oco import place_oco
# from .advanced.twap import run_twap
# from .advanced.grid import run_grid

# logger = get_logger()

# # --- Account Info Commands ---

# @cli.command()
# def account():
#     """Check account information (balances, margin, etc.)"""
#     client = get_client()
#     resp = client.account()
#     print(resp)


# @cli.command()
# @click.argument("symbol")
# def orders(symbol):
#     """Check open orders for a symbol"""
#     client = get_client()
#     resp = client.get_orders(symbol=symbol)
#     print(resp)


# @cli.command()
# @click.argument("symbol")
# def positions(symbol):
#     """Check positions for a symbol"""
#     client = get_client()
#     resp = client.get_position_risk(symbol=symbol)
#     print(resp)


# @click.group()
# def cli():
#     "Binance USDT-M Futures CLI Bot"
#     pass

# @cli.command()
# def ping():
#     "Ping the exchange and print server time"
#     c = get_client()
#     r = c.ping()
#     t = c.time()
#     click.echo(f"Ping: {r}, Server Time: {t}")

# @cli.command()
# @click.argument("symbol")
# def price(symbol):
#     "Get latest price for a symbol"
#     c = get_client()
#     r = c.ticker_price(symbol=symbol.upper())
#     click.echo(r)

# @cli.group()
# def order():
#     "Place basic and advanced orders"
#     pass

# @order.command("market")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# def order_market(symbol, side, qty):
#     data = OrderBase(symbol=symbol, side=side.upper(), qty=qty)
#     resp = place_market_order(data)
#     click.echo(resp)

# @order.command("limit")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# @click.option("--price", required=True, type=float)
# @click.option("--tif", default="GTC", show_default=True)
# def order_limit(symbol, side, qty, price, tif):
#     data = LimitOrder(symbol=symbol, side=side.upper(), qty=qty, price=price)
#     resp = place_limit_order(data, tif=tif)
#     click.echo(resp)

# @order.command("stop-limit")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# @click.option("--stop", required=True, type=float)
# @click.option("--price", required=True, type=float)
# @click.option("--tif", default="GTC", show_default=True)
# def order_stop_limit(symbol, side, qty, stop, price, tif):
#     data = StopLimitOrder(symbol=symbol, side=side.upper(), qty=qty, stop=stop, price=price)
#     resp = place_stop_limit(data, tif=tif)
#     click.echo(resp)

# @order.command("oco")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# @click.option("--tp", required=True, type=float)
# @click.option("--sl", required=True, type=float)
# def order_oco(symbol, side, qty, tp, sl):
#     data = OCOOrder(symbol=symbol, side=side.upper(), qty=qty, tp=tp, sl=sl)
#     resp = place_oco(data)
#     click.echo(resp)

# @cli.group()
# def strat():
#     "Run strategies (TWAP, Grid)"
#     pass

# @strat.command("twap")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# @click.option("--slices", required=True, type=int)
# @click.option("--duration", required=True, type=int, help="seconds")
# def strat_twap(symbol, side, qty, slices, duration):
#     params = TWAPParams(symbol=symbol, side=side.upper(), qty=qty, slices=slices, duration=duration)
#     resp = run_twap(params)
#     click.echo(tabulate([{ "slice": i+1, "result": r } for i, r in enumerate(resp)], headers="keys"))

# @strat.command("grid")
# @click.option("--symbol", required=True)
# @click.option("--qty", required=True, type=float)
# @click.option("--lower", required=True, type=float)
# @click.option("--upper", required=True, type=float)
# @click.option("--levels", required=True, type=int)
# def strat_grid(symbol, qty, lower, upper, levels):
#     params = GridParams(symbol=symbol, qty=qty, lower=lower, upper=upper, levels=levels)
#     resp = run_grid(params)
#     click.echo(resp)

# if __name__ == "__main__":
#     cli()
