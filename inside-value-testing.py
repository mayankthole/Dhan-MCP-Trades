import pandas as pd
import os
import time
import logging
import json
import threading
from datetime import datetime, timedelta
from Dhan_Tradehull import Tradehull

# Global variables for coordination between strategies
GLOBAL_LOCK = threading.Lock()
ACTIVE_SYMBOLS = set()  # Symbols that are being actively traded
STOPPED_SCANNING = False  # Flag to stop scanning threads when market closes

# Configure logging
def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    standard_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    detailed_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
    
    logger = logging.getLogger('inside_value_system')
    logger.setLevel(logging.DEBUG)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(standard_formatter)
    logger.addHandler(console_handler)
    
    file_handler = logging.FileHandler(f'logs/inside_value_system_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    signal_handler = logging.FileHandler(f'logs/signals_{datetime.now().strftime("%Y%m%d")}.log')
    signal_handler.setLevel(logging.INFO)
    signal_handler.setFormatter(standard_formatter)
    signal_logger = logging.getLogger('signals')
    signal_logger.setLevel(logging.INFO)
    signal_logger.addHandler(signal_handler)
    
    trade_handler = logging.FileHandler(f'logs/trades_{datetime.now().strftime("%Y%m%d")}.log')
    trade_handler.setLevel(logging.INFO)
    trade_handler.setFormatter(detailed_formatter)
    trade_logger = logging.getLogger('trades')
    trade_logger.setLevel(logging.INFO)
    trade_logger.addHandler(trade_handler)
    
    error_handler = logging.FileHandler(f'logs/errors_{datetime.now().strftime("%Y%m%d")}.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    return logger, signal_logger, trade_logger

# Initialize loggers
logger, signal_logger, trade_logger = setup_logging()

#########################
# COMMON UTILITY FUNCTIONS
#########################

def get_ltp_safely(tsl, symbol, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            time.sleep(delay)
            ltp_data = tsl.get_ltp_data(names=[symbol])
            ltp = ltp_data.get(symbol, 0)
            
            if ltp > 0:
                logger.debug(f"LTP fetch successful for {symbol}: {ltp}")
            else:
                logger.warning(f"LTP fetch returned zero for {symbol}")
                
            return ltp
        except Exception as e:
            if "Too many requests" in str(e) and attempt < max_retries - 1:
                logger.warning(f"Rate limited, waiting {delay*2}s before retry...")
                time.sleep(delay * 2)  # Wait longer on rate limit
            else:
                logger.error(f"Could not get LTP for {symbol}: {e}")
                return 0
    return 0

def get_current_day_candle(tsl, symbol, exchange, timeframe="15"):
    try:
        intraday_data = tsl.get_historical_data(tradingsymbol=symbol, exchange=exchange, timeframe=timeframe)
        
        if intraday_data is None or len(intraday_data) == 0:
            logger.warning(f"No intraday data available for {symbol}")
            return None
        
        logger.debug(f"Intraday data for {symbol} - columns: {intraday_data.columns.tolist()}")
        logger.debug(f"Intraday data for {symbol} - first row: {intraday_data.iloc[0].to_dict()}")
        
        today = datetime.now().date()
        
        date_columns = ['date', 'datetime', 'timestamp', 'time', 'candle_time']
        found_date_column = None
        
        for col in date_columns:
            if col in intraday_data.columns:
                found_date_column = col
                break
        
        if found_date_column:
            date_index = pd.to_datetime(intraday_data[found_date_column]).dt.date
            today_candles = intraday_data[date_index == today]
        else:
            if hasattr(intraday_data.index, 'date'):
                date_index = intraday_data.index.date
                today_mask = [d == today for d in date_index]
                today_candles = intraday_data.iloc[today_mask]
            else:
                logger.warning(f"Cannot determine date information for {symbol} intraday data - using recent candles")
                today_candles = intraday_data.iloc[-30:]  # Use last 30 candles
        
        if len(today_candles) == 0:
            logger.warning(f"No intraday data available for {symbol} today")
            return None
        
        running_candle = {
            'open': today_candles.iloc[0]['open'],
            'high': today_candles['high'].max(),
            'low': today_candles['low'].min(),
            'close': today_candles.iloc[-1]['close'],  # Latest close
            'datetime': today_candles.iloc[-1].name if hasattr(today_candles.iloc[-1], 'name') else datetime.now(),
            'is_complete': False
        }
        
        return running_candle
        
    except Exception as e:
        logger.error(f"Error getting running candle for {symbol}: {e}", exc_info=True)
        return None

def get_min_quantity(tsl, symbol, exchange):
    try:
        return 1
    except Exception as e:
        logger.error(f"Error getting minimum quantity for {symbol}: {e}")
        return 1  # Default to 1 in case of error

def round_to_tick_size(price, tick_size=0.10):
    return round(price / tick_size) * tick_size

def place_order_with_sl_target(tsl, symbol, exchange, quantity, transaction_type, 
                              sl_percent=0.01, target_percent=0.01, trade_type="MIS"):
    result = {}
    exit_type = "SELL" if transaction_type == "BUY" else "BUY"
    
    try:
        current_price = get_ltp_safely(tsl, symbol)
        if not current_price or current_price <= 0:
            logger.error(f"Cannot get valid current price for {symbol}. Skipping order.")
            return None
        
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
        
        max_attempts = 5
        attempts = 0
        executed = False
        exec_price = None
        
        while attempts < max_attempts and not executed:
            attempts += 1
            time.sleep(1)  # Wait for execution
            
            try:
                order_status = tsl.get_order_status(primary_order_id)
                logger.info(f"Order status for {primary_order_id}: {order_status}")
                
                if order_status in ["TRADED", "Completed", "COMPLETE", "Complete"]:
                    executed = True
                    try:
                        exec_price = tsl.get_executed_price(primary_order_id)
                        logger.info(f"Execution price for {symbol}: {exec_price}")
                    except Exception as price_error:
                        logger.warning(f"Failed to get execution price via API: {price_error}")
                        
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
                        
                        if not exec_price:
                            exec_price = get_ltp_safely(tsl, symbol)
                            logger.info(f"Using LTP as fallback price for {symbol}: {exec_price}")
                    
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
        
        if transaction_type == "BUY":
            sl_price_raw = exec_price * (1 - sl_percent)
            target_price_raw = exec_price * (1 + target_percent)
            sl_price = round_to_tick_size(sl_price_raw)
            target_price = round_to_tick_size(target_price_raw)
            logger.info(f"BUY order for {symbol} at {exec_price} - Stop loss set 1% lower at {sl_price}, Target set 1% higher at {target_price}")
        else:  # SELL
            sl_price_raw = exec_price * (1 + sl_percent)
            target_price_raw = exec_price * (1 - target_percent)
            sl_price = round_to_tick_size(sl_price_raw)
            target_price = round_to_tick_size(target_price_raw)
            logger.info(f"SELL order for {symbol} at {exec_price} - Stop loss set 1% higher at {sl_price}, Target set 1% lower at {target_price}")
            
        result["sl_price"] = sl_price
        result["target_price"] = target_price
        
        try:
            logger.info(f"Placing STOPMARKET order for {symbol} - {exit_type} at trigger price {sl_price}")
            logger.info(f"STOPMARKET uses price=0 (executes at market when triggered) and trigger_price={sl_price}")
            
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
        
        try:
            logger.info(f"Placing LIMIT order for {symbol} - {exit_type} at price {target_price}")
            logger.info(f"LIMIT uses price={target_price} (exact price to execute at) and trigger_price=0 (no trigger)")
            
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
        
        def get_order_status_safely(order_id):
            if order_id:
                try:
                    status = tsl.get_order_status(order_id)
                    return status
                except Exception as status_error:
                    logger.error(f"Error fetching status: {status_error}")
                    return "ERROR"
            return "No Order ID"
        
        primary_status = get_order_status_safely(primary_order_id)
        sl_status = get_order_status_safely(result.get("sl_order_id"))
        target_status = get_order_status_safely(result.get("target_order_id"))
        
        print("\n--- Trade Execution Details ---")
        print(f"Current Market Price: {exec_price}")
        print(f"Stop Loss Price: {sl_price}")
        print(f"Target Price: {target_price}")
        print(f"\n{transaction_type} Order ID: {primary_order_id}")
        print(f"Stop Loss Order ID: {result.get('sl_order_id', 'Failed')}")
        print(f"Target Order ID: {result.get('target_order_id', 'Failed')}")
        print(f"\n{transaction_type} Order Status: {primary_status}")
        print(f"Stop Loss Order Status: {sl_status}")
        print(f"Target Order Status: {target_status}")
        
        result["symbol"] = symbol
        result["exchange"] = exchange
        result["transaction_type"] = transaction_type
        result["quantity"] = quantity
        result["primary_status"] = primary_status
        result["sl_status"] = sl_status
        result["target_status"] = target_status
        
        return result
    
    except Exception as e:
        logger.error(f"Critical error in place_order_with_sl_target for {symbol}: {str(e)}", exc_info=True)
        return result

def save_signal_details(signal_data, strategy_type="combined", filename=None):
    if not signal_data:
        return None
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{strategy_type}_inside_value_signals_{timestamp}.json"

    if not os.path.exists('signals'):
        os.makedirs('signals')
    
    filepath = os.path.join('signals', filename)
    
    def convert_numpy_types(obj):
        if isinstance(obj, (list, tuple)):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        elif hasattr(obj, 'item'):  # NumPy scalars have an 'item' method
            return obj.item()       # Convert to Python native type
        else:
            return obj
    
    if isinstance(signal_data, list):
        for signal in signal_data:
            signal['Strategy_Type'] = strategy_type
    else:
        signal_data['Strategy_Type'] = strategy_type
    
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                existing_data = json.load(f)
                
                if isinstance(signal_data, list):
                    for new_signal in signal_data:
                        symbol = new_signal.get('Symbol')
                        updated = False
                        
                        for i, existing_signal in enumerate(existing_data):
                            if existing_signal.get('Symbol') == symbol and existing_signal.get('Strategy_Type') == strategy_type:
                                existing_data[i] = convert_numpy_types(new_signal)
                                updated = True
                                break
                        
                        if not updated:
                            existing_data.append(convert_numpy_types(new_signal))
                else:
                    symbol = signal_data.get('Symbol')
                    updated = False
                    
                    for i, signal in enumerate(existing_data):
                        if signal.get('Symbol') == symbol and signal.get('Strategy_Type') == strategy_type:
                            existing_data[i] = convert_numpy_types(signal_data)
                            updated = True
                            break
                    
                    if not updated:
                        existing_data.append(convert_numpy_types(signal_data))
                
                signal_data_to_save = existing_data
            except:
                if isinstance(signal_data, list):
                    signal_data_to_save = [convert_numpy_types(s) for s in signal_data]
                else:
                    signal_data_to_save = [convert_numpy_types(signal_data)]
    else:
        if isinstance(signal_data, list):
            signal_data_to_save = [convert_numpy_types(s) for s in signal_data]
        else:
            signal_data_to_save = [convert_numpy_types(signal_data)]
    
    with open(filepath, 'w') as f:
        json.dump(signal_data_to_save, f, indent=4)
    
    return filepath

def generate_daily_report(bullish_signals, bearish_signals):
    timestamp = datetime.now().strftime("%Y%m%d")
    report_file = f"combined_inside_value_report_{timestamp}.txt"
    
    if not os.path.exists('reports'):
        os.makedirs('reports')
    
    filepath = os.path.join('reports', report_file)
    
    bullish_inside_value_count = sum(1 for signal in bullish_signals if signal.get('Inside Value (Combined)') == 'Yes')
    bullish_triggered_count = sum(1 for signal in bullish_signals if signal.get('Inside Value (Combined)') == 'Yes' and signal.get('Above_Threshold', False))
    
    bearish_inside_value_count = sum(1 for signal in bearish_signals if signal.get('Inside Value (Combined)') == 'Yes')
    bearish_triggered_count = sum(1 for signal in bearish_signals if signal.get('Inside Value (Combined)') == 'Yes' and signal.get('Below_Threshold', False))
    
    with open(filepath, 'w') as f:
        f.write(f"==== COMBINED INSIDE VALUE INTRADAY SCANNER - DAILY REPORT ====\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n")
        
        f.write("--- SUMMARY ---\n")
        f.write(f"Total stocks scanned: {len(set([s.get('Symbol') for s in bullish_signals + bearish_signals]))}\n\n")
        
        f.write("--- BULLISH SCAN RESULTS ---\n")
        f.write(f"Bullish inside value stocks identified: {bullish_inside_value_count}\n")
        f.write(f"Bullish entry signals triggered: {bullish_triggered_count}\n\n")
        
        f.write("--- BEARISH SCAN RESULTS ---\n")
        f.write(f"Bearish inside value stocks identified: {bearish_inside_value_count}\n")
        f.write(f"Bearish entry signals triggered: {bearish_triggered_count}\n\n")
        
        f.write("--- BULLISH INSIDE VALUE STOCKS ---\n")
        for signal in bullish_signals:
            if signal.get('Inside Value (Combined)') == 'Yes':
                symbol = signal.get('Symbol', 'Unknown')
                median = signal.get('Yesterday_Median', 0)
                threshold = signal.get('Entry_Threshold', 0)
                current = signal.get('Current_Price', 0)
                triggered = "✓" if signal.get('Above_Threshold', False) else "-"
                
                f.write(f"{triggered} {symbol}: Median={median:.2f}, Threshold={threshold:.2f}, Current={current:.2f}\n")
        f.write("\n")
        
        f.write("--- BEARISH INSIDE VALUE STOCKS ---\n")
        for signal in bearish_signals:
            if signal.get('Inside Value (Combined)') == 'Yes':
                symbol = signal.get('Symbol', 'Unknown')
                median = signal.get('Yesterday_Median', 0)
                threshold = signal.get('Entry_Threshold', 0)
                current = signal.get('Current_Price', 0)
                triggered = "✓" if signal.get('Below_Threshold', False) else "-"
                
                f.write(f"{triggered} {symbol}: Median={median:.2f}, Threshold={threshold:.2f}, Current={current:.2f}\n")
        f.write("\n")
        
        if bullish_triggered_count > 0:
            f.write("--- TRIGGERED BULLISH SIGNALS ---\n")
            for signal in bullish_signals:
                if signal.get('Inside Value (Combined)') == 'Yes' and signal.get('Above_Threshold', False):
                    symbol = signal.get('Symbol', 'Unknown')
                    threshold = signal.get('Entry_Threshold', 0)
                    current = signal.get('Current_Price', 0)
                    pct_above = (current - threshold) / threshold * 100
                    
                    f.write(f"- {symbol}: Price={current:.2f}, Above threshold by {pct_above:.2f}%\n")
            f.write("\n")
        
        if bearish_triggered_count > 0:
            f.write("--- TRIGGERED BEARISH SIGNALS ---\n")
            for signal in bearish_signals:
                if signal.get('Inside Value (Combined)') == 'Yes' and signal.get('Below_Threshold', False):
                    symbol = signal.get('Symbol', 'Unknown')
                    threshold = signal.get('Entry_Threshold', 0)
                    current = signal.get('Current_Price', 0)
                    pct_below = (threshold - current) / threshold * 100
                    
                    f.write(f"- {symbol}: Price={current:.2f}, Below threshold by {pct_below:.2f}%\n")
            f.write("\n")
        
        bullish_trades = [s for s in bullish_signals if s.get('Trades_Executed', False)]
        bearish_trades = [s for s in bearish_signals if s.get('Trades_Executed', False)]
        
        if bullish_trades or bearish_trades:
            f.write("--- TRADES EXECUTED ---\n")
            
            if bullish_trades:
                f.write("BULLISH TRADES:\n")
                for trade in bullish_trades:
                    symbol = trade.get('Symbol', 'Unknown')
                    entry_price = trade.get('execution_price', 0)
                    quantity = trade.get('quantity', 0)
                    f.write(f"- {symbol} (BULLISH): {quantity} @ ₹{entry_price:.2f}\n")
                    
                    sl_price = trade.get('sl_price', 0)
                    target_price = trade.get('target_price', 0)
                    f.write(f"  * Stop Loss: ₹{sl_price:.2f} (-1%)\n")
                    f.write(f"  * Target: ₹{target_price:.2f} (+1%)\n")
                f.write("\n")
            
            if bearish_trades:
                f.write("BEARISH TRADES:\n")
                for trade in bearish_trades:
                    symbol = trade.get('Symbol', 'Unknown')
                    entry_price = trade.get('execution_price', 0)
                    quantity = trade.get('quantity', 0)
                    f.write(f"- {symbol} (BEARISH): {quantity} @ ₹{entry_price:.2f}\n")
                    
                    sl_price = trade.get('sl_price', 0)
                    target_price = trade.get('target_price', 0)
                    f.write(f"  * Stop Loss: ₹{sl_price:.2f} (+1%)\n")
                    f.write(f"  * Target: ₹{target_price:.2f} (-1%)\n")
    
    logger.info(f"Combined daily report generated: {filepath}")
    return filepath

def send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs):
    success = True
    
    for config in bot_configs:
        try:
            # Add a small delay between messages to avoid Telegram rate limiting
            time.sleep(0.5)
            
            # Send the alert using this bot and chat ID
            tsl.send_telegram_alert(
                message=message,
                receiver_chat_id=config["chat_id"],
                bot_token=config["bot_token"]
            )
            
            logger.info(f"Alert sent via bot to chat ID: {config['chat_id']}")
            
        except Exception as e:
            logger.error(f"Failed to send alert to {config['chat_id']} using bot token: {config['bot_token'][:10]}... : {e}")
            success = False
    
    return success

def check_market_hours():
    now = datetime.now()
    
    if now.weekday() > 4:
        return False
    
    market_start = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 09:15:00", "%Y-%m-%d %H:%M:%S")
    market_end = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 15:30:00", "%Y-%m-%d %H:%M:%S")
    
    return market_start <= now <= market_end

def is_symbol_available_for_trading(symbol, strategy_type="bullish"):
    with GLOBAL_LOCK:
        if symbol in ACTIVE_SYMBOLS:
            logger.info(f"Symbol {symbol} is already being traded by another strategy, skipping {strategy_type} strategy")
            return False
        
        ACTIVE_SYMBOLS.add(symbol)
        logger.info(f"Symbol {symbol} is now being traded by {strategy_type} strategy")
        return True

def release_symbol(symbol):
    with GLOBAL_LOCK:
        if symbol in ACTIVE_SYMBOLS:
            ACTIVE_SYMBOLS.remove(symbol)
            logger.info(f"Symbol {symbol} has been released from trading restrictions")

#########################
# BULLISH STRATEGY FUNCTIONS
#########################

def check_inside_value_conditions_set1(prev_h, prev_l, prev_c, curr_h, curr_l, curr_c):
    prev_bottom = (prev_h + prev_l) / 2
    prev_median = (prev_h + prev_l + prev_c) / 3
    prev_top = prev_median - prev_bottom + prev_median
    
    curr_bottom = (curr_h + curr_l) / 2
    curr_median = (curr_h + curr_l + curr_c) / 3
    curr_top = curr_median - curr_bottom + curr_median
    
    condition1 = prev_bottom < curr_top
    condition2 = prev_bottom < curr_bottom
    condition3 = prev_top > curr_top
    condition4 = prev_top > curr_bottom
    
    is_inside = condition1 and condition2 and condition3 and condition4
    
    return condition1, condition2, condition3, condition4, is_inside, prev_bottom, prev_top, curr_bottom, curr_top



def check_inside_value_conditions_set2(prev_h, prev_l, prev_c, curr_h, curr_l, curr_c):
    prev_bottom = (prev_h + prev_l) / 2
    prev_median = (prev_h + prev_l + prev_c) / 3
    prev_top = prev_median - prev_bottom + prev_median
    
    curr_bottom = (curr_h + curr_l) / 2
    curr_median = (curr_h + curr_l + curr_c) / 3
    curr_top = curr_median - curr_bottom + curr_median
    
    condition1 = prev_bottom > curr_top
    condition2 = prev_bottom > curr_bottom
    condition3 = prev_top < curr_top
    condition4 = prev_top < curr_bottom
    
    is_inside = condition1 and condition2 and condition3 and condition4
    
    return condition1, condition2, condition3, condition4, is_inside, prev_bottom, prev_top, curr_bottom, curr_top



def check_intraday_inside_value(tsl, symbol, exchange):
    try:
        daily_data = tsl.get_historical_data(tradingsymbol=symbol, exchange=exchange, timeframe="DAY")
        
        if daily_data is None or len(daily_data) < 1:
            logger.warning(f"Not enough daily data for {symbol}")
            return False, 0, 0, {}
        
        yesterday = daily_data.iloc[-1]
        
        today_running = get_current_day_candle(tsl, symbol, exchange)
        
        if today_running is None:
            return False, 0, 0, {}
        
        prev_h, prev_l, prev_c = yesterday['high'], yesterday['low'], yesterday['close']
        curr_h, curr_l, curr_c = today_running['high'], today_running['low'], today_running['close']
        
        cond1_set1, cond2_set1, cond3_set1, cond4_set1, is_inside_set1, prev_bottom, prev_top, curr_bottom, curr_top = check_inside_value_conditions_set1(
            prev_h, prev_l, prev_c, curr_h, curr_l, curr_c
        )
        
        cond1_set2, cond2_set2, cond3_set2, cond4_set2, is_inside_set2, prev_bottom, prev_top, curr_bottom, curr_top = check_inside_value_conditions_set2(
            prev_h, prev_l, prev_c, curr_h, curr_l, curr_c
        )
        
        is_inside_combined = is_inside_set1 or is_inside_set2
        
        yesterday_median = (prev_h + prev_l + prev_c) / 3
        entry_threshold = round_to_tick_size(yesterday_median * 1.01)
        
        ltp = get_ltp_safely(tsl, symbol)
        
        details = {
            'Symbol': symbol,
            'Exchange': exchange,
            'Inside Value (Combined)': 'Yes' if is_inside_combined else 'No',
            'Inside Value (Set 1)': 'Yes' if is_inside_set1 else 'No',
            'Inside Value (Set 2)': 'Yes' if is_inside_set2 else 'No',
            
            'Yesterday_High': prev_h,
            'Yesterday_Low': prev_l,
            'Yesterday_Close': prev_c,
            'Yesterday_Median': yesterday_median,
            
            'Today_High': curr_h,
            'Today_Low': curr_l,
            'Today_Open': today_running['open'],
            'Today_Current': curr_c,
            
            'Entry_Threshold': entry_threshold,
            'Current_Price': ltp,
            'Above_Threshold': ltp >= entry_threshold,
            
            'Last_Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            
            'Set1_Condition1': 'True' if cond1_set1 else 'False',
            'Set1_Condition2': 'True' if cond2_set1 else 'False',
            'Set1_Condition3': 'True' if cond3_set1 else 'False',
            'Set1_Condition4': 'True' if cond4_set1 else 'False',
            
            'Set2_Condition1': 'True' if cond1_set2 else 'False',
            'Set2_Condition2': 'True' if cond2_set2 else 'False',
            'Set2_Condition3': 'True' if cond3_set2 else 'False',
            'Set2_Condition4': 'True' if cond4_set2 else 'False',
        }
        
        return is_inside_combined, yesterday_median, entry_threshold, details
        
    except Exception as e:
        logger.error(f"Error checking intraday inside value for {symbol}: {e}", exc_info=True)
        return False, 0, 0, {}
    

def check_intraday_bearish_inside_value(tsl, symbol, exchange):
    try:
        daily_data = tsl.get_historical_data(tradingsymbol=symbol, exchange=exchange, timeframe="DAY")
        
        if daily_data is None or len(daily_data) < 1:
            logger.warning(f"Not enough daily data for {symbol}")
            return False, 0, 0, {}
        
        yesterday = daily_data.iloc[-1]
        
        today_running = get_current_day_candle(tsl, symbol, exchange)
        
        if today_running is None:
            return False, 0, 0, {}
        
        prev_h, prev_l, prev_c = yesterday['high'], yesterday['low'], yesterday['close']
        curr_h, curr_l, curr_c = today_running['high'], today_running['low'], today_running['close']
        
        cond1_set1, cond2_set1, cond3_set1, cond4_set1, is_inside_set1, prev_bottom, prev_top, curr_bottom, curr_top = check_bearish_inside_value_conditions_set1(
            prev_h, prev_l, prev_c, curr_h, curr_l, curr_c
        )
        
        cond1_set2, cond2_set2, cond3_set2, cond4_set2, is_inside_set2, prev_bottom, prev_top, curr_bottom, curr_top = check_bearish_inside_value_conditions_set2(
            prev_h, prev_l, prev_c, curr_h, curr_l, curr_c
        )
        
        is_inside_combined = is_inside_set1 or is_inside_set2
        
        yesterday_median = (prev_h + prev_l + prev_c) / 3
        entry_threshold = round_to_tick_size(yesterday_median * 0.99)
        
        ltp = get_ltp_safely(tsl, symbol)
        
        details = {
            'Symbol': symbol,
            'Exchange': exchange,
            'Inside Value (Combined)': 'Yes' if is_inside_combined else 'No',
            'Inside Value (Set 1)': 'Yes' if is_inside_set1 else 'No',
            'Inside Value (Set 2)': 'Yes' if is_inside_set2 else 'No',
            
            'Yesterday_High': prev_h,
            'Yesterday_Low': prev_l,
            'Yesterday_Close': prev_c,
            'Yesterday_Median': yesterday_median,
            
            'Today_High': curr_h,
            'Today_Low': curr_l,
            'Today_Open': today_running['open'],
            'Today_Current': curr_c,
            
            'Entry_Threshold': entry_threshold,
            'Current_Price': ltp,
            'Below_Threshold': ltp <= entry_threshold,
            
            'Last_Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            
            'Set1_Condition1': 'True' if cond1_set1 else 'False',
            'Set1_Condition2': 'True' if cond2_set1 else 'False',
            'Set1_Condition3': 'True' if cond3_set1 else 'False',
            'Set1_Condition4': 'True' if cond4_set1 else 'False',
            
            'Set2_Condition1': 'True' if cond1_set2 else 'False',
            'Set2_Condition2': 'True' if cond2_set2 else 'False',
            'Set2_Condition3': 'True' if cond3_set2 else 'False',
            'Set2_Condition4': 'True' if cond4_set2 else 'False',
        }
        
        return is_inside_combined, yesterday_median, entry_threshold, details
        
    except Exception as e:
        logger.error(f"Error checking intraday bearish inside value for {symbol}: {e}", exc_info=True)
        return False, 0, 0, {}

def generate_inside_value_alert_message(stock_details):
    symbol = stock_details.get('Symbol', 'Unknown')
    
    message = f"🔍 BULLISH INSIDE VALUE PATTERN DETECTED - {symbol}\n\n"
    
    message += "📊 Pattern Detection:\n"
    message += f"- Inside Value: {stock_details.get('Inside Value (Combined)', 'No')}\n"
    
    if stock_details.get('Inside Value (Set 1)') == 'Yes':
        message += "- Pattern Type: Set 1 Equations\n"
    if stock_details.get('Inside Value (Set 2)') == 'Yes':
        message += "- Pattern Type: Set 2 Equations\n"
    
    message += f"\n💰 Price Analysis:\n"
    message += f"- Yesterday's Median: ₹{stock_details.get('Yesterday_Median', 0):.2f}\n"
    message += f"- Entry Threshold (1% above): ₹{stock_details.get('Entry_Threshold', 0):.2f}\n"
    message += f"- Current Price: ₹{stock_details.get('Current_Price', 0):.2f}\n"
    
    message += f"\n⏰ Last Updated: {stock_details.get('Last_Updated', '')}"
    message += f"\n\n📣 Will alert when price crosses threshold upward!"
    
    return message

def generate_threshold_alert_message(stock_details):
    symbol = stock_details.get('Symbol', 'Unknown')
    current_price = stock_details.get('Current_Price', 0)
    threshold = stock_details.get('Entry_Threshold', 0)
    
    message = f"🎯 BULLISH ENTRY SIGNAL TRIGGERED - {symbol}\n\n"
    
    message += f"💰 Price Analysis:\n"
    message += f"- Entry Threshold: ₹{threshold:.2f}\n"
    message += f"- Current Price: ₹{current_price:.2f}\n"
    message += f"- Price crossed threshold by: ₹{current_price - threshold:.2f} ({(current_price - threshold) / threshold * 100:.2f}%)\n"
    
    message += f"\n📈 Trade Details:\n"
    message += f"- BUY Order:\n"
    message += f"  • Buy {symbol} @ ₹{current_price:.2f}\n"
    
    if 'execution_price' in stock_details:
        exec_price = stock_details.get('execution_price')
        sl_price = stock_details.get('sl_price')
        target_price = stock_details.get('target_price')
        quantity = stock_details.get('quantity', 1)
        
        message += f"  • Executed at: ₹{exec_price:.2f}\n"
        message += f"  • Quantity: {quantity}\n"
        message += f"  • Stop Loss: ₹{sl_price:.2f} (-1%)\n"
        message += f"  • Target: ₹{target_price:.2f} (+1%)\n"
    
    message += f"\n⏰ Last Updated: {stock_details.get('Last_Updated', '')}"
    
    return message




 def generate_bearish_inside_value_alert_message(stock_details):
    symbol = stock_details.get('Symbol', 'Unknown')
    
    message = f"🔍 BEARISH INSIDE VALUE PATTERN DETECTED - {symbol}\n\n"
    
    message += "📊 Pattern Detection:\n"
    message += f"- Bearish Inside Value: {stock_details.get('Inside Value (Combined)', 'No')}\n"
    
    if stock_details.get('Inside Value (Set 1)') == 'Yes':
        message += "- Pattern Type: Set 1 Equations\n"
    if stock_details.get('Inside Value (Set 2)') == 'Yes':
        message += "- Pattern Type: Set 2 Equations\n"
    
    message += f"\n💰 Price Analysis:\n"
    message += f"- Yesterday's Median: ₹{stock_details.get('Yesterday_Median', 0):.2f}\n"
    message += f"- Entry Threshold (1% below): ₹{stock_details.get('Entry_Threshold', 0):.2f}\n"
    message += f"- Current Price: ₹{stock_details.get('Current_Price', 0):.2f}\n"
    
    message += f"\n⏰ Last Updated: {stock_details.get('Last_Updated', '')}"
    message += f"\n\n📣 Will alert when price crosses threshold downward!"
    
    return message

def generate_bearish_threshold_alert_message(stock_details):
    symbol = stock_details.get('Symbol', 'Unknown')
    current_price = stock_details.get('Current_Price', 0)
    threshold = stock_details.get('Entry_Threshold', 0)
    
    message = f"🎯 BEARISH ENTRY SIGNAL TRIGGERED - {symbol}\n\n"
    
    message += f"💰 Price Analysis:\n"
    message += f"- Entry Threshold: ₹{threshold:.2f}\n"
    message += f"- Current Price: ₹{current_price:.2f}\n"
    message += f"- Price crossed threshold by: ₹{threshold - current_price:.2f} ({(threshold - current_price) / threshold * 100:.2f}%)\n"
    
    message += f"\n📉 Trade Details:\n"
    message += f"- SELL Order:\n"
    message += f"  • Sell {symbol} @ ₹{current_price:.2f}\n"
    
    if 'execution_price' in stock_details:
        exec_price = stock_details.get('execution_price')
        sl_price = stock_details.get('sl_price')
        target_price = stock_details.get('target_price')
        quantity = stock_details.get('quantity', 1)
        
        message += f"  • Executed at: ₹{exec_price:.2f}\n"
        message += f"  • Quantity: {quantity}\n"
        message += f"  • Stop Loss: ₹{sl_price:.2f} (+1%)\n"
        message += f"  • Target: ₹{target_price:.2f} (-1%)\n"
    
    message += f"\n⏰ Last Updated: {stock_details.get('Last_Updated', '')}"
    
    return message

def check_bearish_inside_value_conditions_set1(prev_h, prev_l, prev_c, curr_h, curr_l, curr_c):
    prev_bottom = (prev_h + prev_l) / 2
    prev_median = (prev_h + prev_l + prev_c) / 3
    prev_top = prev_median - prev_bottom + prev_median
    
    curr_bottom = (curr_h + curr_l) / 2
    curr_median = (curr_h + curr_l + curr_c) / 3
    curr_top = curr_median - curr_bottom + curr_median
    
    condition1 = prev_bottom > curr_top
    condition2 = prev_bottom > curr_bottom
    condition3 = prev_top < curr_top
    condition4 = prev_top < curr_bottom
    
    is_inside = condition1 and condition2 and condition3 and condition4
    
    return condition1, condition2, condition3, condition4, is_inside, prev_bottom, prev_top, curr_bottom, curr_top

def check_bearish_inside_value_conditions_set2(prev_h, prev_l, prev_c, curr_h, curr_l, curr_c):
    prev_bottom = (prev_h + prev_l) / 2
    prev_median = (prev_h + prev_l + prev_c) / 3
    prev_top = prev_median - prev_bottom + prev_median
    
    curr_bottom = (curr_h + curr_l) / 2
    curr_median = (curr_h + curr_l + curr_c) / 3
    curr_top = curr_median - curr_bottom + curr_median
    
    condition1 = prev_bottom < curr_top
    condition2 = prev_bottom < curr_bottom
    condition3 = prev_top > curr_top
    condition4 = prev_top > curr_bottom
    
    is_inside = condition1 and condition2 and condition3 and condition4
    
    return condition1, condition2, condition3, condition4, is_inside, prev_bottom, prev_top, curr_bottom, curr_top

def place_bullish_entry_orders(tsl, stock_details):
    symbol = stock_details.get('Symbol')
    exchange = stock_details.get('Exchange')
    current_price = stock_details.get('Current_Price')

    try:
        if not is_symbol_available_for_trading(symbol, "bullish"):
            return stock_details, False
        
        quantity = get_min_quantity(tsl, symbol, exchange)
        
        order_result = place_order_with_sl_target(
            tsl=tsl,
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            transaction_type="BUY",
            sl_percent=0.01,
            target_percent=0.01,
            trade_type="MIS"
        )
        
        if not order_result:
            logger.error(f"Failed to place orders for {symbol}")
            release_symbol(symbol)
            return stock_details, False
        
        stock_details.update(order_result)
        stock_details['Trades_Executed'] = True
        stock_details['Trades_Executed_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stock_details['quantity'] = quantity
        
        logger.info(f"Successfully placed bullish orders for {symbol}")
        trade_logger.info(
            f"BULLISH ENTRY | {symbol} | Price: {order_result.get('execution_price')} | "
            f"SL: {order_result.get('sl_price')} | Target: {order_result.get('target_price')}"
        )
        
        return stock_details, True
    
    except Exception as e:
        logger.error(f"Error placing bullish entry orders for {symbol}: {e}", exc_info=True)
        release_symbol(symbol)
        return stock_details, False

def place_bearish_entry_orders(tsl, stock_details):
    symbol = stock_details.get('Symbol')
    exchange = stock_details.get('Exchange')
    current_price = stock_details.get('Current_Price')
    
    try:
        if not is_symbol_available_for_trading(symbol, "bearish"):
            return stock_details, False
        
        quantity = get_min_quantity(tsl, symbol, exchange)
        
        order_result = place_order_with_sl_target(
            tsl=tsl,
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            transaction_type="SELL",  # Bearish - so we SELL
            sl_percent=0.01,
            target_percent=0.01,
            trade_type="MIS"
        )
        
        if not order_result:
            logger.error(f"Failed to place bearish orders for {symbol}")
            release_symbol(symbol)
            return stock_details, False
        
        stock_details.update(order_result)
        stock_details['Trades_Executed'] = True
        stock_details['Trades_Executed_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stock_details['quantity'] = quantity
        
        logger.info(f"Successfully placed bearish orders for {symbol}")
        trade_logger.info(
            f"BEARISH ENTRY | {symbol} | Price: {order_result.get('execution_price')} | "
            f"SL: {order_result.get('sl_price')} | Target: {order_result.get('target_price')}"
        )
        
        return stock_details, True
    
    except Exception as e:
        logger.error(f"Error placing bearish entry orders for {symbol}: {e}", exc_info=True)
        release_symbol(symbol)
        return stock_details, False

def scan_stocks_bullish(tsl, symbol, exchange, hot_watchlist, inside_value_alerted_stocks, threshold_alerted_stocks, traded_stocks, bot_configs):
    try:
        with GLOBAL_LOCK:
            if symbol in ACTIVE_SYMBOLS:
                return None
            
        if symbol in traded_stocks:
            return None
            
        is_inside, median, threshold, details = check_intraday_inside_value(tsl, symbol, exchange)
        
        if is_inside:
            if symbol not in hot_watchlist:
                hot_watchlist[symbol] = details
                logger.info(f"Added {symbol} to bullish hot watchlist")
                
                if symbol not in inside_value_alerted_stocks:
                    message = generate_inside_value_alert_message(details)
                    send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                    
                    inside_value_alerted_stocks.add(symbol)
                    
                    signal_logger.info(f"BULLISH INSIDE VALUE | {symbol} | Median: {median} | Threshold: {threshold}")
            else:
                hot_watchlist[symbol] = details
            
            current_price = details.get('Current_Price', 0)
            if current_price >= threshold and symbol not in threshold_alerted_stocks:
                updated_details, success = place_bullish_entry_orders(tsl, details)
                
                if success:
                    traded_stocks.add(symbol)
                    threshold_alerted_stocks.add(symbol)
                    
                    message = generate_threshold_alert_message(updated_details)
                    send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                    
                    save_signal_details(updated_details, "bullish")
                    
                    signal_logger.info(f"BULLISH THRESHOLD CROSSED | {symbol} | Current: {current_price} | Threshold: {threshold}")
                    
                    hot_watchlist.pop(symbol)
                    
                    return updated_details
            
            return details
                
        return None
        
    except Exception as e:
        logger.error(f"Error in bullish scan for {symbol}: {e}", exc_info=True)
        return None

def scan_stocks_bearish(tsl, symbol, exchange, hot_watchlist, inside_value_alerted_stocks, threshold_alerted_stocks, traded_stocks, bot_configs):
    try:
        if symbol in traded_stocks:
            return None
            
        is_inside, median, threshold, details = check_intraday_bearish_inside_value(tsl, symbol, exchange)
        
        if is_inside:
            if symbol not in hot_watchlist:
                hot_watchlist[symbol] = details
                logger.info(f"Added {symbol} to bearish hot watchlist")
                
                if symbol not in inside_value_alerted_stocks:
                    message = generate_bearish_inside_value_alert_message(details)
                    send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                    
                    inside_value_alerted_stocks.add(symbol)
                    
                    signal_logger.info(f"BEARISH INSIDE VALUE | {symbol} | Median: {median} | Threshold: {threshold}")
            else:
                hot_watchlist[symbol] = details
            
            current_price = details.get('Current_Price', 0)
            if current_price <= threshold and symbol not in threshold_alerted_stocks:
                updated_details, success = place_bearish_entry_orders(tsl, details)
                
                if success:
                    traded_stocks.add(symbol)
                    threshold_alerted_stocks.add(symbol)
                    
                    message = generate_bearish_threshold_alert_message(updated_details)
                    send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                    
                    save_signal_details(updated_details, "bearish")
                    
                    signal_logger.info(f"BEARISH THRESHOLD CROSSED | {symbol} | Current: {current_price} | Threshold: {threshold}")
                    
                    hot_watchlist.pop(symbol)
                    
                    return updated_details
            
            return details
                
        return None
        
    except Exception as e:
        logger.error(f"Error in bearish scan for {symbol}: {e}", exc_info=True)
        return None

def monitor_active_trades(tsl, active_trades, bot_configs):
    for symbol, details in list(active_trades.items()):
        try:
            primary_status = details.get('primary_status')
            sl_status = details.get('sl_status')
            target_status = details.get('target_status')
            
            if sl_status == "COMPLETED" or target_status == "COMPLETED":
                logger.info(f"Exit order completed for {symbol} - releasing symbol")
                release_symbol(symbol)
                active_trades.pop(symbol)
                
        except Exception as e:
            logger.error(f"Error monitoring active trade for {symbol}: {e}", exc_info=True)
            
    return active_trades

def run_combined_inside_value_scanner(client_code, token_id, watchlist, bot_configs, scan_interval=300):
    global STOPPED_SCANNING
    
    tsl = Tradehull(client_code, token_id)
    
    startup_message = f"🚀 COMBINED INSIDE VALUE SCANNER STARTED\n\n" \
                      f"Running both BULLISH and BEARISH strategies\n" \
                      f"Monitoring {len(watchlist)} stocks\n" \
                      f"Scan interval: {scan_interval} seconds"
    send_telegram_alerts_to_multiple_bots(tsl, startup_message, bot_configs)
    
    bullish_inside_value_alerted = set()
    bullish_threshold_alerted = set()
    bullish_traded = set()
    bullish_hot_watchlist = {}
    bullish_signals = []
    
    bearish_inside_value_alerted = set()
    bearish_threshold_alerted = set()
    bearish_traded = set()
    bearish_hot_watchlist = {}
    bearish_signals = []
    
    active_trades = {}
    
    last_full_scan = datetime.now() - timedelta(seconds=scan_interval)
    
    while check_market_hours() and not STOPPED_SCANNING:
        current_time = datetime.now()
        
        scan_full_list = (current_time - last_full_scan).total_seconds() >= scan_interval
        
        active_trades = monitor_active_trades(tsl, active_trades, bot_configs)
        
        for symbol, details in list(bullish_hot_watchlist.items()):
            try:
                if symbol in bullish_traded or symbol in ACTIVE_SYMBOLS:
                    continue
                
                current_price = get_ltp_safely(tsl, symbol)
                threshold = details.get('Entry_Threshold', 0)
                
                details['Current_Price'] = current_price
                details['Last_Updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                details['Above_Threshold'] = current_price >= threshold
                
                if current_price >= threshold:
                    logger.info(f"Bullish threshold crossed for {symbol} - Current: {current_price}, Threshold: {threshold}")
                    
                    if symbol not in bullish_threshold_alerted:
                        updated_details, success = place_bullish_entry_orders(tsl, details)
                        
                        if success:
                            updated_details['Strategy_Type'] = 'bullish'
                            active_trades[symbol] = updated_details
                            
                            bullish_traded.add(symbol)
                            
                            bullish_threshold_alerted.add(symbol)
                            
                            message = generate_threshold_alert_message(updated_details)
                            send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                            
                            save_signal_details(updated_details, "bullish")
                            bullish_signals.append(updated_details)
                            
                            signal_logger.info(f"BULLISH THRESHOLD CROSSED | {symbol} | Current: {current_price} | Threshold: {threshold}")
                            
                            bullish_hot_watchlist.pop(symbol)
                    else:
                        bullish_hot_watchlist[symbol] = details
                else:
                    is_inside, _, _, updated_details = check_intraday_inside_value(tsl, symbol, details.get('Exchange'))
                    
                    if is_inside:
                        bullish_hot_watchlist[symbol] = updated_details
                    else:
                        logger.info(f"Bullish inside value pattern no longer valid for {symbol}")
                        bullish_hot_watchlist.pop(symbol)
            
            except Exception as e:
                logger.error(f"Error processing bullish hot list stock {symbol}: {e}", exc_info=True)
        
        for symbol, details in list(bearish_hot_watchlist.items()):
            try:
                if symbol in bearish_traded or symbol in ACTIVE_SYMBOLS:
                    continue
                
                current_price = get_ltp_safely(tsl, symbol)
                threshold = details.get('Entry_Threshold', 0)
                
                details['Current_Price'] = current_price
                details['Last_Updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                details['Below_Threshold'] = current_price <= threshold
                
                if current_price <= threshold:
                    logger.info(f"Bearish threshold crossed for {symbol} - Current: {current_price}, Threshold: {threshold}")
                    
                    if symbol not in bearish_threshold_alerted:
                        updated_details, success = place_bearish_entry_orders(tsl, details)
                        
                        if success:
                            updated_details['Strategy_Type'] = 'bearish'
                            active_trades[symbol] = updated_details
                            
                            bearish_traded.add(symbol)
                            
                            bearish_threshold_alerted.add(symbol)
                            
                            message = generate_bearish_threshold_alert_message(updated_details)
                            send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                            
                            save_signal_details(updated_details, "bearish")
                            bearish_signals.append(updated_details)
                            
                            signal_logger.info(f"BEARISH THRESHOLD CROSSED | {symbol} | Current: {current_price} | Threshold: {threshold}")
                            
                            bearish_hot_watchlist.pop(symbol)
                    else:
                        bearish_hot_watchlist[symbol] = details
                else:
                    is_inside, _, _, updated_details = check_intraday_bearish_inside_value(tsl, symbol, details.get('Exchange'))
                    
                    if is_inside:
                        bearish_hot_watchlist[symbol] = updated_details
                    else:
                        logger.info(f"Bearish inside value pattern no longer valid for {symbol}")
                        bearish_hot_watchlist.pop(symbol)
            
            except Exception as e:
                logger.error(f"Error processing bearish hot list stock {symbol}: {e}", exc_info=True)
        
        if scan_full_list:
            logger.info(f"Starting full combined scan at {current_time.strftime('%H:%M:%S')}")
            
            batch_size = 10
            
            for i in range(0, len(watchlist), batch_size):
                batch = watchlist[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(watchlist)-1)//batch_size + 1} ({len(batch)} stocks)...")
                
                for symbol in batch:
                    try:
                        exchange = "INDEX" if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"] else "NSE"
                        
                        with GLOBAL_LOCK:
                            if symbol in ACTIVE_SYMBOLS:
                                continue
                        
                        bullish_signal = scan_stocks_bullish(
                            tsl, symbol, exchange, 
                            bullish_hot_watchlist, bullish_inside_value_alerted, 
                            bullish_threshold_alerted, bullish_traded,
                            bot_configs
                        )
                        
                        if bullish_signal:
                            if bullish_signal.get('Trades_Executed', False):
                                bullish_signal['Strategy_Type'] = 'bullish'
                                active_trades[symbol] = bullish_signal
                            
                            bullish_signals.append(bullish_signal)
                            
                            # Skip bearish scan if any bullish signal was found
                            continue
                        
                        # Only check bearish if not in bullish watchlist
                        if symbol not in bullish_hot_watchlist:
                            bearish_signal = scan_stocks_bearish(
                                tsl, symbol, exchange, 
                                bearish_hot_watchlist, bearish_inside_value_alerted, 
                                bearish_threshold_alerted, bearish_traded,
                                bot_configs
                            )
                            
                            if bearish_signal:
                                if bearish_signal.get('Trades_Executed', False):
                                    bearish_signal['Strategy_Type'] = 'bearish'
                                    active_trades[symbol] = bearish_signal
                                
                                bearish_signals.append(bearish_signal)
                        else:
                            logger.info(f"Skipping bearish scan for {symbol} as it's already in bullish watchlist")
                        
                    except Exception as e:
                        logger.error(f"Error processing {symbol} during full scan: {e}", exc_info=True)
                
                time.sleep(5)
            
            if bullish_signals:
                save_signal_details(bullish_signals, "bullish")
            
            if bearish_signals:
                save_signal_details(bearish_signals, "bearish")
            
            last_full_scan = current_time
        
        time.sleep(1)
    
    if bullish_signals or bearish_signals:
        report_path = generate_daily_report(bullish_signals, bearish_signals)
        
        end_day_message = f"📊 COMBINED INSIDE VALUE TRADING DAY SUMMARY\n\n"
        end_day_message += f"Total stocks scanned: {len(watchlist)}\n\n"
        
        end_day_message += f"BULLISH SUMMARY:\n"
        end_day_message += f"- Inside value patterns found: {len(bullish_inside_value_alerted)}\n"
        end_day_message += f"- Entry signals triggered: {len(bullish_threshold_alerted)}\n"
        end_day_message += f"- Stocks traded: {len(bullish_traded)}\n\n"
        
        end_day_message += f"BEARISH SUMMARY:\n"
        end_day_message += f"- Inside value patterns found: {len(bearish_inside_value_alerted)}\n"
        end_day_message += f"- Entry signals triggered: {len(bearish_threshold_alerted)}\n"
        end_day_message += f"- Stocks traded: {len(bearish_traded)}\n\n"
        
        end_day_message += f"Detailed report saved to: {report_path}"
        
        send_telegram_alerts_to_multiple_bots(tsl, end_day_message, bot_configs)
    
    logger.info("Market closed. Combined scanning stopped.")
    STOPPED_SCANNING = True

def main():
    client_code = "1106534888"
    token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"
  
    bot_configs = [
        {
            "bot_token": "7496561137:AAFCFvJLu-BT_1es8d6yzOQyQF-EqJcCIXY",
            "chat_id": "7783423452"
        },
        {
            "bot_token": "7980433498:AAHtpYlTBxZsgNuHoK9dreBxISkvLOkrGnY",
            "chat_id": "6320586394"
        }
    ]
    
    watchlist = [
        'ABB', 'AUBANK', 'AARTIIND', 'ADANIENT', 'ADANIGREEN', 
        'ADANIPORTS', 'AMBUJACEM', 
        'ASHOKLEY', 'ASIANPAINT', 'AUROPHARMA', 'AXISBANK', 'BSOFT', 
        'BSE', 'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BANDHANBNK', 'BANKBARODA', 
        'BEL', 'BHARATFORG', 'BHEL', 'BPCL', 'BHARTIARTL', 
        'BRITANNIA', 'CANBK', 'CDSL', 'TORNTPOWER', 
        'CIPLA', 'COALINDIA', 'COFORGE',  
        'DLF', 'DABUR', 'DIVISLAB', 'DIXON', 
        'DRREDDY', 'GAIL',  
        'GODREJPROP', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE', 
        'HEROMOTOCO', 'HINDALCO', 'HAL', 'HINDPETRO', 'HINDUNILVR', 
        'ICICIBANK', 'IDFCFIRSTB', 'ITC', 
        'IOC', 'IRCTC', 'IRFC', 'INDUSTOWER', 'INDUSINDBK', 'INFY', 
        'INDIGO', 'JSWSTEEL', 'JINDALSTEL', 'JIOFIN',  
        'KOTAKBANK', 'LICHSGFIN', 'LTIM', 'LT', 
        'LUPIN', 'M&MFIN', 'M&M', 'MANAPPURAM', 
        'MARUTI', 'MCX',  
        'NMDC', 'NTPC', 'NATIONALUM', 'ONGC', 'OFSS',  
        'PERSISTENT', 'PETRONET',  
        'PFC', 'POWERGRID', 'PNB', 'RECLTD', 
        'RELIANCE', 'SBICARD', 'SBILIFE', 'MOTHERSON',  
        'SIEMENS', 'SBIN', 'SAIL', 'SUNPHARMA',  
        'TATACONSUM', 'TATACHEM', 'TCS', 'TATAMOTORS', 
        'TATAPOWER', 'TATASTEEL', 'TECHM', 'FEDERALBNK', 'INDHOTEL',  
        'TITAN', 'TRENT', 'UPL', 'ULTRACEMCO', 
        'VBL', 'VEDL', 'IDEA', 'VOLTAS', 'WIPRO', 'ZOMATO'
    ]
    
    watchlist = [symbol.strip() for symbol in watchlist if symbol.strip()]
    
    try:
        tsl = Tradehull(client_code, token_id)
        
        if not check_market_hours():
            now = datetime.now()
            today = now.date()
            
            market_start = datetime.strptime(f"{today.strftime('%Y-%m-%d')} 09:15:00", "%Y-%m-%d %H:%M:%S")
            
            wait_seconds = (market_start - now).total_seconds()
            
            if wait_seconds > 0:
                if now.weekday() <= 4:
                    wait_minutes = int(wait_seconds / 60)
                    wait_hours = int(wait_minutes / 60)
                    remaining_minutes = wait_minutes % 60
                    
                    message = f"🕒 WAITING FOR MARKET OPEN\n\n" \
                              f"Combined Inside Value Scanner initialized\n" \
                              f"Current time: {now.strftime('%H:%M:%S')}\n" \
                              f"Market opens at: 09:15:00\n" \
                              f"Waiting time: {wait_hours} hours {remaining_minutes} minutes\n\n" \
                              f"Scanner will automatically start at market open."
                    
                    send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                    
                    logger.info(f"Waiting for market hours. Current time: {now.strftime('%H:%M:%S')}, waiting {wait_hours}h {remaining_minutes}m.")
                    
                    if wait_seconds > 1800:
                        update_interval = 1800
                        sleep_intervals = int(wait_seconds / update_interval)
                        
                        for i in range(sleep_intervals):
                            time.sleep(update_interval)
                            
                            now = datetime.now()
                            remaining = (market_start - now).total_seconds()
                            remaining_hours = int(remaining / 3600)
                            remaining_minutes = int((remaining % 3600) / 60)
                            
                            update_message = f"⏳ MARKET OPEN COUNTDOWN\n\n" \
                                           f"Current time: {now.strftime('%H:%M:%S')}\n" \
                                           f"Time remaining: {remaining_hours}h {remaining_minutes}m"
                            
                            send_telegram_alerts_to_multiple_bots


                            