import time
import logging
from datetime import datetime, timedelta
from Dhan_Tradehull import Tradehull

# Basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"trading_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def is_market_open():
    """Check if the market is currently open"""
    now = datetime.now()
    
    # Check if it's a weekday (0 = Monday, 4 = Friday)
    if now.weekday() > 4:
        logger.info("Today is a weekend. Market is closed.")
        return False
    
    # Market hours are 9:15 AM to 3:30 PM
    market_open = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 09:15:00", "%Y-%m-%d %H:%M:%S")
    market_close = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 15:30:00", "%Y-%m-%d %H:%M:%S")
    
    if now < market_open:
        logger.info("Market is not open yet.")
        return False
    
    if now > market_close:
        logger.info("Market is already closed for today.")
        return False
    
    return True

def get_ltp(tsl, symbol):
    """Get last traded price"""
    try:
        ltp_data = tsl.get_ltp_data(names=[symbol])
        price = ltp_data.get(symbol, 0)
        # Additional validation to ensure we have a valid price
        if price is None or price <= 0:
            logger.error(f"Retrieved invalid price: {price} for {symbol}")
            return None
        return price
    except Exception as e:
        logger.error(f"Error getting LTP for {symbol}: {str(e)}")
        return None

def get_min_quantity(tsl, symbol, exchange, is_option=False):
    """Get minimum order quantity - simplified to return 1 for equity"""
    try:
        if exchange == "NSE":
            return 1
        else:
            # For non-equity, get lot size (though we won't be using this now)
            lot_size = tsl.get_lot_size(symbol)
            return max(1, lot_size) if lot_size else 1
    except Exception as e:
        logger.error(f"Error getting lot size for {symbol}: {str(e)}")
        return 1

def place_single_order_with_sl_target(tsl, symbol, exchange, quantity, transaction_type, trade_type="MIS", 
                                     sl_percent=0.01, target_percent=0.01):
    """
    Place a single order with stop loss and target
    
    Parameters:
    - tsl: Tradehull instance
    - symbol: Symbol to trade
    - exchange: Exchange to trade on
    - quantity: Quantity to trade
    - transaction_type: 'BUY' or 'SELL'
    - trade_type: 'MIS', 'CNC', etc.
    - sl_percent: Stop loss percentage (0.01 = 1%)
    - target_percent: Target percentage (0.01 = 1%)
    
    Returns:
    - Dictionary with order IDs and execution details
    """
    result = {}
    exit_type = "SELL" if transaction_type == "BUY" else "BUY"
    
    try:
        # Get current price before placing order
        current_price = get_ltp(tsl, symbol)
        if not current_price:
            logger.error(f"Cannot get current price for {symbol}. Skipping order.")
            return None
            
        # Place the primary order
        logger.info(f"Placing {transaction_type} order for {symbol} at market price")
        primary_order_id = tsl.order_placement(
            tradingsymbol=symbol,
            exchange=exchange,
            quantity=quantity,
            price=0,  # Market price
            trigger_price=0,
            order_type='MARKET',
            transaction_type=transaction_type,
            trade_type=trade_type
        )
        
        if not primary_order_id:
            logger.error(f"Failed to place {transaction_type} order for {symbol}")
            return None
            
        result["primary_order_id"] = primary_order_id
        logger.info(f"{transaction_type} order placed for {symbol} - ID: {primary_order_id}")
        
        # Wait for execution
        max_attempts = 5
        attempts = 0
        executed = False
        exec_price = None
        
        while attempts < max_attempts and not executed:
            attempts += 1
            time.sleep(1)  # Wait for execution
            
            try:
                # Get order status
                order_status = tsl.get_order_status(primary_order_id)
                logger.info(f"Order status for {primary_order_id}: {order_status}")
                
                # Check for successful execution - status could be "TRADED", "Completed" or other success indicators
                if order_status in ["TRADED", "Completed", "COMPLETE", "Complete"]:
                    executed = True
                    # Get execution price - first try get_executed_price
                    try:
                        exec_price = tsl.get_executed_price(primary_order_id)
                        logger.info(f"Execution price for {symbol}: {exec_price}")
                    except Exception as price_error:
                        logger.warning(f"Failed to get execution price via API: {price_error}")
                        
                        # Fallback 1: Try to get order details and extract price
                        try:
                            order_details = tsl.get_order_detail(primary_order_id)
                            if order_details and hasattr(order_details, "average_price"):
                                exec_price = order_details.average_price
                                logger.info(f"Got execution price from order details: {exec_price}")
                            elif order_details and isinstance(order_details, dict) and "average_price" in order_details:
                                exec_price = order_details["average_price"]
                                logger.info(f"Got execution price from order details dict: {exec_price}")
                        except Exception as details_error:
                            logger.warning(f"Failed to get order details: {details_error}")
                        
                        # Fallback 2: Use current market price as approximation
                        if not exec_price:
                            exec_price = get_ltp(tsl, symbol)
                            logger.info(f"Using LTP as fallback price for {symbol}: {exec_price}")
                    
                    # Set execution price in result
                    if exec_price:
                        result["execution_price"] = exec_price
                    else:
                        logger.error(f"Could not determine execution price for {symbol}")
                        return result
                
                elif order_status in ["REJECTED", "Rejected", "CANCELLED", "Cancelled"]:
                    logger.error(f"Order {primary_order_id} was {order_status}")
                    return result
            except Exception as status_error:
                logger.error(f"Error checking order status: {status_error}")
        
        if not executed:
            logger.error(f"Order execution verification failed for {symbol}")
            return result
            
        # Calculate SL and Target prices based on direction and execution price
        # Round to nearest 0.10 to comply with tick size requirements
        def round_to_tick_size(price, tick_size=0.10):
            """Round price to nearest tick size"""
            return round(price / tick_size) * tick_size
            
        if transaction_type == "BUY":
            sl_price_raw = exec_price * (1 - sl_percent)
            target_price_raw = exec_price * (1 + target_percent)
            # Round to the nearest 0.10
            sl_price = round_to_tick_size(sl_price_raw)
            target_price = round_to_tick_size(target_price_raw)
        else:  # SELL
            sl_price_raw = exec_price * (1 + sl_percent)
            target_price_raw = exec_price * (1 - target_percent)
            # Round to the nearest 0.10
            sl_price = round_to_tick_size(sl_price_raw)
            target_price = round_to_tick_size(target_price_raw)
            
        result["sl_price"] = sl_price
        result["target_price"] = target_price
        
        # Place stop loss order
        sl_order_id = None
        try:
            sl_order_id = tsl.order_placement(
                tradingsymbol=symbol,
                exchange=exchange,
                quantity=quantity,
                price=0,  # For STOPMARKET, price is 0
                trigger_price=sl_price,
                order_type='STOPMARKET',
                transaction_type=exit_type,
                trade_type=trade_type
            )
            
            if sl_order_id:
                result["sl_order_id"] = sl_order_id
                logger.info(f"Stop loss order placed for {symbol} at {sl_price} - ID: {sl_order_id}")
            else:
                logger.error(f"Failed to place stop loss order for {symbol}")
        except Exception as sl_error:
            logger.error(f"Error placing stop loss order: {sl_error}")
        
        # Place target order
        target_order_id = None
        try:
            target_order_id = tsl.order_placement(
                tradingsymbol=symbol,
                exchange=exchange,
                quantity=quantity,
                price=target_price,
                trigger_price=0,
                order_type='LIMIT',
                transaction_type=exit_type,
                trade_type=trade_type
            )
            
            if target_order_id:
                result["target_order_id"] = target_order_id
                logger.info(f"Target order placed for {symbol} at {target_price} - ID: {target_order_id}")
                logger.info(f"Target Order placed successfully: {target_order_id}")
            else:
                logger.error(f"Failed to place target order for {symbol}")
        except Exception as target_error:
            logger.error(f"Error placing target order: {target_error}")
        
        # Get status of all orders for a detailed view
        def get_order_status_safely(order_id):
            if order_id:
                try:
                    status = tsl.get_order_status(order_id)
                    return status
                except Exception as status_error:
                    logger.error(f"Error fetching status: {status_error}")
                    return "ERROR"
            return "No Order ID"
        
        # Get order statuses
        primary_status = get_order_status_safely(primary_order_id)
        sl_status = get_order_status_safely(sl_order_id)
        target_status = get_order_status_safely(target_order_id)
        
        # Print detailed trade execution details in the format you want
        print("\n--- Trade Execution Details ---")
        print(f"Current Market Price: {exec_price}")
        print(f"Stop Loss Price: {sl_price}")
        print(f"Target Price: {target_price}")
        print(f"\n{transaction_type} Order ID: {primary_order_id}")
        print(f"Stop Loss Order ID: {sl_order_id}")
        print(f"Target Order ID: {target_order_id}")
        print(f"\n{transaction_type} Order Status: {primary_status}")
        print(f"Stop Loss Order Status: {sl_status}")
        print(f"Target Order Status: {target_status}")
        
        # Logging for records
        logger.info(f"--- Trade Summary for {symbol} ---")
        logger.info(f"Entry Price: {exec_price}")
        logger.info(f"Stop Loss: {sl_price}")
        logger.info(f"Target: {target_price}")
        logger.info(f"Primary Order ID: {primary_order_id} - Status: {primary_status}")
        logger.info(f"SL Order ID: {sl_order_id} - Status: {sl_status}")
        logger.info(f"Target Order ID: {target_order_id} - Status: {target_status}")
        
        return result
    
    except Exception as e:
        logger.error(f"Critical error in place_single_order_with_sl_target for {symbol}: {str(e)}")
        return result

def place_orders(tsl, symbol, exchange, current_price, trade_type="BUY"):
    """
    Place only equity orders with proper stop loss and target
    
    Parameters:
    - tsl: Tradehull instance
    - symbol: Symbol to trade
    - exchange: Exchange to trade on
    - current_price: Current price of the symbol
    - trade_type: 'BUY' for gap up, 'SELL' for gap down
    """
    orders_data = {}
    
    # Set SL and Target percentages based on trade direction
    equity_sl_percent = 0.01  # 1%
    equity_target_percent = 0.01  # 1%
    
    # Place equity order
    try:
        equity_qty = get_min_quantity(tsl, symbol, exchange)
        
        # Log order details before placement
        logger.info(f"Placing {trade_type} order for {symbol} with quantity {equity_qty}")
        
        equity_result = place_single_order_with_sl_target(
            tsl=tsl,
            symbol=symbol,
            exchange=exchange,
            quantity=equity_qty,
            transaction_type=trade_type,
            trade_type='MIS',
            sl_percent=equity_sl_percent,
            target_percent=equity_target_percent
        )
        
        if equity_result and "execution_price" in equity_result:
            orders_data["equity"] = {
                "symbol": symbol,
                "qty": equity_qty,
                "entry_price": equity_result["execution_price"],
                "sl_price": equity_result.get("sl_price"),
                "target_price": equity_result.get("target_price"),
                "direction": trade_type,
                "primary_order_id": equity_result.get("primary_order_id"),
                "sl_order_id": equity_result.get("sl_order_id"),
                "target_order_id": equity_result.get("target_order_id")
            }
            
            # Log successful order details
            logger.info(f"Successfully placed {trade_type} order for {symbol}")
            logger.info(f"Entry Price: {equity_result['execution_price']}")
            logger.info(f"Stop Loss: {equity_result.get('sl_price')}")
            logger.info(f"Target: {equity_result.get('target_price')}")
    except Exception as e:
        logger.error(f"Error placing equity order for {symbol}: {str(e)}")
    
    return orders_data

def send_telegram_alert(tsl, message, bot_configs):
    """Send alert to Telegram"""
    for config in bot_configs:
        try:
            tsl.send_telegram_alert(
                message=message,
                receiver_chat_id=config["chat_id"],
                bot_token=config["bot_token"]
            )
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {str(e)}")

def main():
    # API credentials
    client_code = "1106534888"
    token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"

    # Telegram settings
    bot_configs = [
        {
            "bot_token": "7496561137:AAFCFvJLu-BT_1es8d6yzOQyQF-EqJcCIXY",
            "chat_id": "7783423452"  # Your friend's bot and chat ID
        },
        {
            "bot_token": "7980433498:AAHtpYlTBxZsgNuHoK9dreBxISkvLOkrGnY",
            "chat_id": "6320586394"  # Your bot and chat ID
        }
    ]
    
    # Your watchlist - update as needed
    watchlist = [  'AMBUJACEM'
      # 'ADANIPORTS'
    # , 'AMBUJACEM'
        # 'ABB', 'ADANIGREEN', 'SBIN',
        # 'INDIGO', 'NESTLEIND', 'TCS', 'RELIANCE', 'ITC', 'INFY'
    ]
    
    # Make sure watchlist has only valid symbols
    watchlist = [symbol.strip() for symbol in watchlist if symbol.strip()]
    
    # Gap percentage thresholds
    gap_up_threshold = 1.01    # 1% gap up
    gap_down_threshold = 0.99  # 1% gap down
    
    try:
        # Initialize Dhan API client
        tsl = Tradehull(client_code, token_id)
        logger.info("Trading system started")
        
        # Send startup message
        send_telegram_alert(tsl, "🚀 TRADING SYSTEM STARTED", bot_configs)
        
        # Check if market is open
        now = datetime.now()
        market_open = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 09:15:00", "%Y-%m-%d %H:%M:%S")
        market_close = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 15:30:00", "%Y-%m-%d %H:%M:%S")
        
        # Check if it's a weekday
        if now.weekday() > 4:
            logger.info("Today is a weekend. Exiting.")
            send_telegram_alert(tsl, "Today is a weekend. Market is closed.", bot_configs)
            return
        
        # Check if market is already closed for the day
        if now > market_close:
            logger.info("Market is already closed for today. Exiting.")
            send_telegram_alert(tsl, "Market is already closed for today.", bot_configs)
            return
        
        # If market is not open yet, wait until it opens
        if now < market_open:
            wait_seconds = (market_open - now).total_seconds()
            logger.info(f"Market opens in {wait_seconds} seconds. Waiting...")
            send_telegram_alert(tsl, f"Market opens at 9:15 AM. Waiting {wait_seconds/60:.0f} minutes...", bot_configs)
            time.sleep(wait_seconds)
            logger.info("Market is now open!")
            send_telegram_alert(tsl, "Market is now open! Starting to check stocks...", bot_configs)
        
        # Check if we're more than 15 minutes after market open
        market_open_plus_15 = market_open + timedelta(minutes=500)
        if now > market_open_plus_15:
            logger.info("More than 15 minutes after market open. Exiting.")
            send_telegram_alert(tsl, "More than 15 minutes after market open. Will try again tomorrow.", bot_configs)
            return
        
        gap_up_stocks = []
        gap_down_stocks = []
        
        # Process each stock in the watchlist
        for symbol in watchlist:
            try:
                # Determine exchange
                exchange = "NSE" if symbol not in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"] else "INDEX"
                
                # Get daily data
                daily_data = tsl.get_historical_data(tradingsymbol=symbol, exchange=exchange, timeframe="DAY")
                
                if daily_data is None or len(daily_data) < 1:
                    logger.warning(f"Not enough data for {symbol}")
                    continue
                
                # Get yesterday's candle
                yesterday = daily_data.iloc[-1]
                
                # Calculate median and thresholds
                yesterday_median = (yesterday['high'] + yesterday['low'] + yesterday['close']) / 3
                gap_up_price = yesterday_median * gap_up_threshold
                gap_down_price = yesterday_median * gap_down_threshold
                
                # Get current price
                current_price = get_ltp(tsl, symbol)
                
                # IMPORTANT: Skip stocks with invalid prices (None or 0)
                if current_price is None or current_price <= 0:
                    logger.warning(f"Invalid price {current_price} for {symbol} - skipping")
                    send_telegram_alert(tsl, f"⚠️ {symbol}: Could not retrieve valid price. Trading skipped.", bot_configs)
                    continue
                
                # Send alert for this stock
                stock_msg = (
                    f"📊 {symbol}\n"
                    f"Yesterday's Median: ₹{yesterday_median:.2f}\n"
                    f"Gap Up Threshold (+1%): ₹{gap_up_price:.2f}\n"
                    f"Gap Down Threshold (-1%): ₹{gap_down_price:.2f}\n"
                    f"Current Price: ₹{current_price:.2f}"
                )
                send_telegram_alert(tsl, stock_msg, bot_configs)
                
                # Check for gap up condition
                if current_price >= gap_up_price:
                    logger.info(f"{symbol}: Price {current_price} is above threshold {gap_up_price} - GAP UP")
                    
                    # Send alert
                    trade_msg = (
                        f"🔼 GAP UP DETECTED - {symbol}\n"
                        f"Current Price: ₹{current_price:.2f} is above threshold ₹{gap_up_price:.2f}\n"
                        f"Placing BUY orders..."
                    )
                    send_telegram_alert(tsl, trade_msg, bot_configs)
                    
                    # Place BUY orders
                    orders = place_orders(tsl, symbol, exchange, current_price, "BUY")
                    
                    if orders:
                        gap_up_stocks.append(symbol)
                        
                        # Send order details
                        details_msg = f"✅ BUY ORDERS PLACED - {symbol}\n\n"
                        
                        if "equity" in orders:
                            eq = orders["equity"]
                            details_msg += f"💹 EQUITY:\n- Bought at: ₹{eq['entry_price']:.2f}\n- Quantity: {eq['qty']}\n- Stop Loss: ₹{eq['sl_price']:.2f} (-1%)\n- Target: ₹{eq['target_price']:.2f} (+1%)\n- Order IDs: {eq['primary_order_id']}/{eq['sl_order_id']}/{eq['target_order_id']}\n\n"
                        
                        send_telegram_alert(tsl, details_msg, bot_configs)
                
                # Check for gap down condition with valid price check
                elif current_price <= gap_down_price:
                    logger.info(f"{symbol}: Price {current_price} is below threshold {gap_down_price} - GAP DOWN")
                    
                    # Send alert
                    trade_msg = (
                        f"🔽 GAP DOWN DETECTED - {symbol}\n"
                        f"Current Price: ₹{current_price:.2f} is below threshold ₹{gap_down_price:.2f}\n"
                        f"Placing SELL orders..."
                    )
                    send_telegram_alert(tsl, trade_msg, bot_configs)
                    
                    # Place SELL orders
                    orders = place_orders(tsl, symbol, exchange, current_price, "SELL")
                    
                    if orders:
                        gap_down_stocks.append(symbol)
                        
                        # Send order details
                        details_msg = f"✅ SELL ORDERS PLACED - {symbol}\n\n"
                        
                        if "equity" in orders:
                            eq = orders["equity"]
                            details_msg += f"💹 EQUITY:\n- Sold at: ₹{eq['entry_price']:.2f}\n- Quantity: {eq['qty']}\n- Stop Loss: ₹{eq['sl_price']:.2f} (+1%)\n- Target: ₹{eq['target_price']:.2f} (-1%)\n- Order IDs: {eq['primary_order_id']}/{eq['sl_order_id']}/{eq['target_order_id']}\n\n"
                        
                        send_telegram_alert(tsl, details_msg, bot_configs)
                
                else:
                    logger.info(f"{symbol}: Price {current_price} is within threshold range. No trade.")
                    send_telegram_alert(tsl, f"⏸️ NO TRADE - {symbol}\nPrice is within threshold range.", bot_configs)
            
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
            
            time.sleep(1)  # Small delay between stocks
        
        # Send summary
        traded_count = len(gap_up_stocks) + len(gap_down_stocks)
        if traded_count > 0:
            summary = f"📈 TRADING SUMMARY\n"
            
            if gap_up_stocks:
                summary += f"Gap Up Trades: {', '.join(gap_up_stocks)}\n"
            
            if gap_down_stocks:
                summary += f"Gap Down Trades: {', '.join(gap_down_stocks)}\n"
        else:
            summary = "📈 TRADING SUMMARY\nNo gap up or gap down trades today"
            
        send_telegram_alert(tsl, summary, bot_configs)
        
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        send_telegram_alert(tsl, f"❌ ERROR: {str(e)}", bot_configs)

if __name__ == "__main__":
    main()