import pandas as pd
import os
import time
import logging
import json
from datetime import datetime, timedelta
from Dhan_Tradehull import Tradehull

# Configure logging
def setup_logging():
    """Set up logging with different handlers for different log types"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create formatters
    standard_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    detailed_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
    
    # Create main logger
    logger = logging.getLogger('inside_value_system')
    logger.setLevel(logging.DEBUG)
    
    # Console handler (for INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(standard_formatter)
    logger.addHandler(console_handler)
    
    # File handler for general logs
    file_handler = logging.FileHandler(f'logs/inside_value_system_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # File handler for signal logs
    signal_handler = logging.FileHandler(f'logs/signals_{datetime.now().strftime("%Y%m%d")}.log')
    signal_handler.setLevel(logging.INFO)
    signal_handler.setFormatter(standard_formatter)
    signal_logger = logging.getLogger('signals')
    signal_logger.setLevel(logging.INFO)
    signal_logger.addHandler(signal_handler)
    
    # File handler for trade logs
    trade_handler = logging.FileHandler(f'logs/trades_{datetime.now().strftime("%Y%m%d")}.log')
    trade_handler.setLevel(logging.INFO)
    trade_handler.setFormatter(detailed_formatter)
    trade_logger = logging.getLogger('trades')
    trade_logger.setLevel(logging.INFO)
    trade_logger.addHandler(trade_handler)
    
    # File handler for errors
    error_handler = logging.FileHandler(f'logs/errors_{datetime.now().strftime("%Y%m%d")}.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    return logger, signal_logger, trade_logger

# Initialize loggers
logger, signal_logger, trade_logger = setup_logging()

def check_inside_value_conditions_set1(prev_h, prev_l, prev_c, curr_h, curr_l, curr_c):
    """
    Check the first set of inside value conditions.
    
    Equation 1: PH+PL/2 < DH+DL+DC/3 - DH+DL/2 + DH+DL+DC/3
    Equation 2: PH+PL/2 < DH+DL/2
    Equation 3: PH+PL+PC/3 - PH+PL/2 + PH+PL+PC/3 > DH+DL+DC/3 - DH+DL/2 + DH+DL+DC/3
    Equation 4: PH+PL+PC/3 - PH+PL/2 + PH+PL+PC/3 > DH+DL/2
    """
    # Calculate all values needed for the equations
    prev_bottom = (prev_h + prev_l) / 2
    prev_median = (prev_h + prev_l + prev_c) / 3
    prev_top = prev_median - prev_bottom + prev_median
    
    curr_bottom = (curr_h + curr_l) / 2
    curr_median = (curr_h + curr_l + curr_c) / 3
    curr_top = curr_median - curr_bottom + curr_median
    
    # Equation 1: PH+PL/2 < DH+DL+DC/3 - DH+DL/2 + DH+DL+DC/3
    condition1 = prev_bottom < curr_top
    
    # Equation 2: PH+PL/2 < DH+DL/2
    condition2 = prev_bottom < curr_bottom
    
    # Equation 3: PH+PL+PC/3 - PH+PL/2 + PH+PL+PC/3 > DH+DL+DC/3 - DH+DL/2 + DH+DL+DC/3
    condition3 = prev_top > curr_top
    
    # Equation 4: PH+PL+PC/3 - PH+PL/2 + PH+PL+PC/3 > DH+DL/2
    condition4 = prev_top > curr_bottom
    
    # Inside value requires all conditions to be met
    is_inside = condition1 and condition2 and condition3 and condition4
    
    return condition1, condition2, condition3, condition4, is_inside, prev_bottom, prev_top, curr_bottom, curr_top

def check_inside_value_conditions_set2(prev_h, prev_l, prev_c, curr_h, curr_l, curr_c):
    """
    Check the second set of inside value conditions.
    
    Equation 1: PH+PL/2 > DH+DL+DC/3 - DH+DL/2 + DH+DL+DC/3
    Equation 2: PH+PL/2 > DH+DL/2
    Equation 3: PH+PL+PC/3 - PH+PL/2 + PH+PL+PC/3 < DH+DL+DC/3 - DH+DL/2 + DH+DL+DC/3
    Equation 4: PH+PL+PC/3 - PH+PL/2 + PH+PL+PC/3 < DH+DL/2
    """
    # Calculate all values needed for the equations
    prev_bottom = (prev_h + prev_l) / 2
    prev_median = (prev_h + prev_l + prev_c) / 3
    prev_top = prev_median - prev_bottom + prev_median
    
    curr_bottom = (curr_h + curr_l) / 2
    curr_median = (curr_h + curr_l + curr_c) / 3
    curr_top = curr_median - curr_bottom + curr_median
    
    # Equation 1: PH+PL/2 > DH+DL+DC/3 - DH+DL/2 + DH+DL+DC/3
    condition1 = prev_bottom > curr_top
    
    # Equation 2: PH+PL/2 > DH+DL/2
    condition2 = prev_bottom > curr_bottom
    
    # Equation 3: PH+PL+PC/3 - PH+PL/2 + PH+PL+PC/3 < DH+DL+DC/3 - DH+DL/2 + DH+DL+DC/3
    condition3 = prev_top < curr_top
    
    # Equation 4: PH+PL+PC/3 - PH+PL/2 + PH+PL+PC/3 < DH+DL/2
    condition4 = prev_top < curr_bottom
    
    # Inside value requires all conditions to be met
    is_inside = condition1 and condition2 and condition3 and condition4
    
    return condition1, condition2, condition3, condition4, is_inside, prev_bottom, prev_top, curr_bottom, curr_top

def get_ltp_safely(tsl, symbol, max_retries=3, delay=1):
    """
    Get LTP with retry mechanism and rate limiting protection.
    
    Args:
        tsl: Tradehull instance
        symbol: Stock symbol
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        float: LTP value or 0 if unavailable
    """
    for attempt in range(max_retries):
        try:
            # Add delay to avoid rate limiting
            time.sleep(delay)
            ltp_data = tsl.get_ltp_data(names=[symbol])
            ltp = ltp_data.get(symbol, 0)
            
            # Log only non-zero values to avoid log spam
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

def get_atm_option_info(tsl, symbol, option_type="CE", expiry=0):
    """
    Get the ATM option details for a stock.
    
    Args:
        tsl: Tradehull instance
        symbol: Stock symbol
        option_type: Option type ("CE" for Call, "PE" for Put)
        expiry: Expiry index (0 = current month, 1 = next month)
        
    Returns:
        tuple: (option_symbol, strike_price, ltp)
    """
    try:
        # Get ATM strike for the symbol
        CE_symbol, PE_symbol, strike = tsl.ATM_Strike_Selection(Underlying=symbol, Expiry=expiry)
        
        # Get the correct option symbol based on option_type
        option_symbol = CE_symbol if option_type == "CE" else PE_symbol
        
        # Get option price
        ltp = get_ltp_safely(tsl, option_symbol)
        
        # Return the option symbol, strike price, and ltp
        return option_symbol, strike, ltp
    except Exception as e:
        logger.error(f"Error getting ATM {option_type} option for {symbol}: {e}", exc_info=True)
        return None, None, 0

def get_current_day_candle(tsl, symbol, exchange, timeframe="15"):
    """
    Construct the current day's running candle from intraday data.
    
    Args:
        tsl: Tradehull instance
        symbol: Stock symbol
        exchange: Exchange code (NSE, NFO, etc.)
        timeframe: Intraday timeframe (1, 5, 15 minutes)
        
    Returns:
        dict: Current day's running candle with high, low, open, close
    """
    try:
        # Get intraday data
        intraday_data = tsl.get_historical_data(tradingsymbol=symbol, exchange=exchange, timeframe=timeframe)
        
        if intraday_data is None or len(intraday_data) == 0:
            logger.warning(f"No intraday data available for {symbol}")
            return None
        
        # Log the structure of the data to understand what we're working with
        logger.debug(f"Intraday data for {symbol} - columns: {intraday_data.columns.tolist()}")
        logger.debug(f"Intraday data for {symbol} - first row: {intraday_data.iloc[0].to_dict()}")
        
        # Get today's date
        today = datetime.now().date()
        
        # Check for various possible date column names
        date_columns = ['date', 'datetime', 'timestamp', 'time', 'candle_time']
        found_date_column = None
        
        # Try to find a date column
        for col in date_columns:
            if col in intraday_data.columns:
                found_date_column = col
                break
        
        # If we found a date column, use it
        if found_date_column:
            date_index = pd.to_datetime(intraday_data[found_date_column]).dt.date
            today_candles = intraday_data[date_index == today]
        else:
            # If the index is a datetime
            if hasattr(intraday_data.index, 'date'):
                date_index = intraday_data.index.date
                today_mask = [d == today for d in date_index]
                today_candles = intraday_data.iloc[today_mask]
            else:
                # As a fallback, just use the most recent data (last 15-30 candles)
                logger.warning(f"Cannot determine date information for {symbol} intraday data - using recent candles")
                today_candles = intraday_data.iloc[-30:]  # Use last 30 candles
        
        if len(today_candles) == 0:
            logger.warning(f"No intraday data available for {symbol} today")
            return None
        
        # Construct running candle
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

def check_intraday_inside_value(tsl, symbol, exchange):
    """
    Check for inside value pattern using previous day and current running day.
    
    Args:
        tsl: Tradehull instance
        symbol: Stock symbol
        exchange: Exchange code
        
    Returns:
        tuple: (is_inside_value, yesterday_median, entry_threshold, details)
    """
    try:
        # Get previous day's completed candle
        daily_data = tsl.get_historical_data(tradingsymbol=symbol, exchange=exchange, timeframe="DAY")
        
        if daily_data is None or len(daily_data) < 1:
            logger.warning(f"Not enough daily data for {symbol}")
            return False, 0, 0, {}
        
        # Previous day's candle
        yesterday = daily_data.iloc[-1]  # Last completed day
        
        # Get current day's running candle
        today_running = get_current_day_candle(tsl, symbol, exchange)
        
        if today_running is None:
            return False, 0, 0, {}
        
        # Check inside value conditions using both sets
        prev_h, prev_l, prev_c = yesterday['high'], yesterday['low'], yesterday['close']
        curr_h, curr_l, curr_c = today_running['high'], today_running['low'], today_running['close']
        
        # Using set 1 equation
        cond1_set1, cond2_set1, cond3_set1, cond4_set1, is_inside_set1, prev_bottom, prev_top, curr_bottom, curr_top = check_inside_value_conditions_set1(
            prev_h, prev_l, prev_c, curr_h, curr_l, curr_c
        )
        
        # Using set 2 equation
        cond1_set2, cond2_set2, cond3_set2, cond4_set2, is_inside_set2, prev_bottom, prev_top, curr_bottom, curr_top = check_inside_value_conditions_set2(
            prev_h, prev_l, prev_c, curr_h, curr_l, curr_c
        )
        
        # Combined result
        is_inside_combined = is_inside_set1 or is_inside_set2
        
        # Calculate yesterday's median and entry threshold
        yesterday_median = (prev_h + prev_l + prev_c) / 3
        entry_threshold = yesterday_median * 1.01
        
        # Current market price
        ltp = get_ltp_safely(tsl, symbol)
        
        # Store details for logging and alerts
        details = {
            'Symbol': symbol,
            'Exchange': exchange,
            'Inside Value (Combined)': 'Yes' if is_inside_combined else 'No',
            'Inside Value (Set 1)': 'Yes' if is_inside_set1 else 'No',
            'Inside Value (Set 2)': 'Yes' if is_inside_set2 else 'No',
            
            # Yesterday's data
            'Yesterday_High': prev_h,
            'Yesterday_Low': prev_l,
            'Yesterday_Close': prev_c,
            'Yesterday_Median': yesterday_median,
            
            # Today's running data
            'Today_High': curr_h,
            'Today_Low': curr_l,
            'Today_Open': today_running['open'],
            'Today_Current': curr_c,
            
            # Entry threshold and current price
            'Entry_Threshold': entry_threshold,
            'Current_Price': ltp,
            'Above_Threshold': ltp >= entry_threshold,
            
            # Last updated time
            'Last_Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            
            # Set 1 conditions details
            'Set1_Condition1': 'True' if cond1_set1 else 'False',
            'Set1_Condition2': 'True' if cond2_set1 else 'False',
            'Set1_Condition3': 'True' if cond3_set1 else 'False',
            'Set1_Condition4': 'True' if cond4_set1 else 'False',
            
            # Set 2 conditions details
            'Set2_Condition1': 'True' if cond1_set2 else 'False',
            'Set2_Condition2': 'True' if cond2_set2 else 'False',
            'Set2_Condition3': 'True' if cond3_set2 else 'False',
            'Set2_Condition4': 'True' if cond4_set2 else 'False',
        }
        
        return is_inside_combined, yesterday_median, entry_threshold, details
        
    except Exception as e:
        logger.error(f"Error checking intraday inside value for {symbol}: {e}", exc_info=True)
        return False, 0, 0, {}

def generate_inside_value_alert_message(stock_details):
    """
    Generate an alert message for inside value pattern detection.
    """
    symbol = stock_details.get('Symbol', 'Unknown')
    
    # Basic message
    message = f"🔍 INSIDE VALUE PATTERN DETECTED - {symbol}\n\n"
    
    # Pattern details
    message += "📊 Pattern Detection:\n"
    message += f"- Inside Value: {stock_details.get('Inside Value (Combined)', 'No')}\n"
    
    if stock_details.get('Inside Value (Set 1)') == 'Yes':
        message += "- Pattern Type: Set 1 Equations\n"
    if stock_details.get('Inside Value (Set 2)') == 'Yes':
        message += "- Pattern Type: Set 2 Equations\n"
    
    # Price details
    message += f"\n💰 Price Analysis:\n"
    message += f"- Yesterday's Median: ₹{stock_details.get('Yesterday_Median', 0):.2f}\n"
    message += f"- Entry Threshold (1%): ₹{stock_details.get('Entry_Threshold', 0):.2f}\n"
    message += f"- Current Price: ₹{stock_details.get('Current_Price', 0):.2f}\n"
    
    # Current time
    message += f"\n⏰ Last Updated: {stock_details.get('Last_Updated', '')}"
    message += f"\n\n📣 Will alert when price crosses threshold!"
    
    return message

def generate_threshold_alert_message(stock_details):
    """
    Generate an alert message for threshold crossing.
    """
    symbol = stock_details.get('Symbol', 'Unknown')
    current_price = stock_details.get('Current_Price', 0)
    threshold = stock_details.get('Entry_Threshold', 0)
    
    # Basic message
    message = f"🎯 ENTRY SIGNAL TRIGGERED - {symbol}\n\n"
    
    # Price details
    message += f"💰 Price Analysis:\n"
    message += f"- Entry Threshold: ₹{threshold:.2f}\n"
    message += f"- Current Price: ₹{current_price:.2f}\n"
    message += f"- Price crossed threshold by: ₹{current_price - threshold:.2f} ({(current_price - threshold) / threshold * 100:.2f}%)\n"
    
    # Add trade details
    message += f"\n📈 Trade Details:\n"
    
    # Futures details
    future_details = stock_details.get('Future_Details', {})
    if future_details:
        message += f"- FUTURES TRADE:\n"
        message += f"  • Buy {symbol} Future @ ₹{current_price:.2f}\n"
        message += f"  • Quantity: {future_details.get('Quantity', 0)}\n"
        message += f"  • Target: ₹{current_price * 1.01:.2f} (+1%)\n"
        message += f"  • Stop-Loss: ₹{current_price * 0.99:.2f} (-1%)\n"
    
    # Option details
    option_details = stock_details.get('Option_Details', {})
    if option_details:
        option_symbol = option_details.get('Symbol', 'Unknown')
        option_price = option_details.get('Price', 0)
        strike = option_details.get('Strike', 0)
        
        message += f"\n- OPTIONS TRADE:\n"
        message += f"  • Buy {option_symbol} @ ₹{option_price:.2f} (Strike: {strike})\n"
        message += f"  • Quantity: {option_details.get('Quantity', 0)}\n"
        message += f"  • Target: ₹{option_price * 1.20:.2f} (+20%)\n"
        message += f"  • Stop-Loss: ₹{option_price * 0.90:.2f} (-10%)\n"
    
    # Current time
    message += f"\n⏰ Last Updated: {stock_details.get('Last_Updated', '')}"
    
    return message

def generate_stop_loss_alert_message(stock_details, position_type, flip_details=None):
    """
    Generate an alert message for stop loss hit and position flip.
    
    Args:
        stock_details: Dictionary with original position details
        position_type: Type of position that hit stop loss ("FUTURES" or "OPTIONS")
        flip_details: Dictionary with new position details after flip
    """
    symbol = stock_details.get('Symbol', 'Unknown')
    
    # Basic message
    message = f"⚠️ STOP LOSS TRIGGERED - {symbol} {position_type}\n\n"
    
    # Stop loss details
    if position_type == "FUTURES":
        entry_price = stock_details.get('Future_Details', {}).get('Entry_Price', 0)
        sl_price = stock_details.get('Future_Details', {}).get('Stop_Loss', 0)
        quantity = stock_details.get('Future_Details', {}).get('Quantity', 0)
        loss_pct = abs((sl_price - entry_price) / entry_price * 100)
        
        message += f"💰 Position Details:\n"
        message += f"- Entry Price: ₹{entry_price:.2f}\n"
        message += f"- Stop Loss Price: ₹{sl_price:.2f}\n"
        message += f"- Quantity: {quantity}\n"
        message += f"- Loss: {loss_pct:.2f}%\n"
    else:  # OPTIONS
        entry_price = stock_details.get('Option_Details', {}).get('Entry_Price', 0)
        sl_price = stock_details.get('Option_Details', {}).get('Stop_Loss', 0)
        option_symbol = stock_details.get('Option_Details', {}).get('Symbol', 'Unknown')
        quantity = stock_details.get('Option_Details', {}).get('Quantity', 0)
        loss_pct = abs((sl_price - entry_price) / entry_price * 100)
        
        message += f"💰 Position Details:\n"
        message += f"- Option: {option_symbol}\n"
        message += f"- Entry Price: ₹{entry_price:.2f}\n"
        message += f"- Stop Loss Price: ₹{sl_price:.2f}\n"
        message += f"- Quantity: {quantity}\n"
        message += f"- Loss: {loss_pct:.2f}%\n"
    
    # Position flip details
    if flip_details:
        message += f"\n🔄 POSITION FLIPPED\n"
        
        if position_type == "FUTURES":
            flip_price = flip_details.get('Entry_Price', 0)
            flip_sl = flip_details.get('Stop_Loss', 0)
            flip_target = flip_details.get('Target', 0)
            flip_quantity = flip_details.get('Quantity', 0)
            
            message += f"- New Position: SHORT {symbol} Futures\n"
            message += f"- Entry Price: ₹{flip_price:.2f}\n"
            message += f"- Quantity: {flip_quantity}\n"
            message += f"- Stop Loss: ₹{flip_sl:.2f} (+1%)\n"
            message += f"- Target: ₹{flip_target:.2f} (-1%)\n"
        else:  # OPTIONS
            flip_symbol = flip_details.get('Symbol', 'Unknown')
            flip_price = flip_details.get('Entry_Price', 0)
            flip_sl = flip_details.get('Stop_Loss', 0)
            flip_target = flip_details.get('Target', 0)
            flip_quantity = flip_details.get('Quantity', 0)
            
            message += f"- New Position: BUY {flip_symbol} (PUT Option)\n"
            message += f"- Entry Price: ₹{flip_price:.2f}\n"
            message += f"- Quantity: {flip_quantity}\n"
            message += f"- Stop Loss: ₹{flip_sl:.2f} (-10%)\n"
            message += f"- Target: ₹{flip_target:.2f} (+20%)\n"
    
    # Current time
    message += f"\n⏰ Triggered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    return message

def generate_target_hit_message(stock_details, position_type, is_flip_position=False):
    """
    Generate an alert message for target price hit.
    
    Args:
        stock_details: Dictionary with position details
        position_type: Type of position that hit target ("FUTURES" or "OPTIONS")
        is_flip_position: Whether this is a flipped position after stop loss
    """
    symbol = stock_details.get('Symbol', 'Unknown')
    
    # Basic message
    message = f"🎉 TARGET ACHIEVED - {symbol} {position_type}\n\n"
    if is_flip_position:
        message = f"🎉 FLIP POSITION TARGET ACHIEVED - {symbol} {position_type}\n\n"
    
    # Target details
    if position_type == "FUTURES":
        position_key = 'Flip_Future_Details' if is_flip_position else 'Future_Details'
        entry_price = stock_details.get(position_key, {}).get('Entry_Price', 0)
        target_price = stock_details.get(position_key, {}).get('Target', 0)
        quantity = stock_details.get(position_key, {}).get('Quantity', 0)
        
        # For flip position (short), profit is entry - target
        if is_flip_position:
            profit = entry_price - target_price
            profit_pct = (profit / entry_price) * 100
        else:
            profit = target_price - entry_price
            profit_pct = (profit / entry_price) * 100
        
        message += f"💰 Position Details:\n"
        message += f"- {'Short' if is_flip_position else 'Long'} {symbol} Futures\n"
        message += f"- Entry Price: ₹{entry_price:.2f}\n"
        message += f"- Target Price: ₹{target_price:.2f}\n"
        message += f"- Quantity: {quantity}\n"
        message += f"- Profit: ₹{profit * quantity:.2f} ({profit_pct:.2f}%)\n"
    else:  # OPTIONS
        position_key = 'Flip_Option_Details' if is_flip_position else 'Option_Details'
        entry_price = stock_details.get(position_key, {}).get('Entry_Price', 0)
        target_price = stock_details.get(position_key, {}).get('Target', 0)
        option_symbol = stock_details.get(position_key, {}).get('Symbol', 'Unknown')
        quantity = stock_details.get(position_key, {}).get('Quantity', 0)
        profit_pct = ((target_price - entry_price) / entry_price) * 100
        
        message += f"💰 Position Details:\n"
        message += f"- Option: {option_symbol}\n"
        message += f"- Entry Price: ₹{entry_price:.2f}\n"
        message += f"- Target Price: ₹{target_price:.2f}\n"
        message += f"- Quantity: {quantity}\n"
        message += f"- Profit: ₹{(target_price - entry_price) * quantity:.2f} ({profit_pct:.2f}%)\n"
    
    # Current time
    message += f"\n⏰ Triggered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    return message

def save_signal_details(signal_data, filename=None):
    """
    Save signal details to a JSON file for tracking.
    
    Args:
        signal_data: Dictionary with signal details
        filename: Optional custom filename
        
    Returns:
        str: Path to the saved file
    """
    if not signal_data:
        return None
    
    # Generate filename with timestamp if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"inside_value_signals_{timestamp}.json"

    # Create signals directory if it doesn't exist
    if not os.path.exists('signals'):
        os.makedirs('signals')
    
    filepath = os.path.join('signals', filename)
    
    # Function to convert NumPy types to Python native types
    def convert_numpy_types(obj):
        if isinstance(obj, (list, tuple)):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        elif hasattr(obj, 'item'):  # NumPy scalars have an 'item' method
            return obj.item()       # Convert to Python native type
        else:
            return obj
    
    # If file exists, load and update
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                existing_data = json.load(f)
                
                # Check if this symbol already exists
                symbol = signal_data.get('Symbol')
                updated = False
                
                for i, signal in enumerate(existing_data):
                    if signal.get('Symbol') == symbol:
                        # Convert NumPy types to standard Python types
                        existing_data[i] = convert_numpy_types(signal_data)
                        updated = True
                        break
                
                if not updated:
                    # Convert NumPy types to standard Python types
                    existing_data.append(convert_numpy_types(signal_data))
                
                signal_data_to_save = existing_data
            except:
                # Convert NumPy types to standard Python types
                signal_data_to_save = [convert_numpy_types(signal_data)]
    else:
        # Convert NumPy types to standard Python types
        signal_data_to_save = [convert_numpy_types(signal_data)]
    
    # Save to JSON file
    with open(filepath, 'w') as f:
        json.dump(signal_data_to_save, f, indent=4)
    
    return filepath

def generate_daily_report(signals_data):
    """
    Generate a daily report of the inside value signals.
    
    Args:
        signals_data: List of signal dictionaries
        
    Returns:
        str: Path to the generated report
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    report_file = f"inside_value_report_{timestamp}.txt"
    
    # Create reports directory if it doesn't exist
    if not os.path.exists('reports'):
        os.makedirs('reports')
    
    filepath = os.path.join('reports', report_file)
    
    # Count inside value stocks
    inside_value_count = sum(1 for signal in signals_data if signal.get('Inside Value (Combined)') == 'Yes')
    triggered_count = sum(1 for signal in signals_data if signal.get('Inside Value (Combined)') == 'Yes' and signal.get('Above_Threshold', False))
    
    # Write report
    with open(filepath, 'w') as f:
        f.write(f"==== INSIDE VALUE INTRADAY SCANNER - DAILY REPORT ====\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n")
        
        f.write("--- SCAN RESULTS ---\n")
        f.write(f"Total stocks scanned: {len(signals_data)}\n")
        f.write(f"Inside value stocks identified: {inside_value_count}\n")
        f.write(f"Entry signals triggered: {triggered_count}\n\n")
        
        # List inside value stocks
        f.write("Inside Value Stocks:\n")
        for signal in signals_data:
            if signal.get('Inside Value (Combined)') == 'Yes':
                symbol = signal.get('Symbol', 'Unknown')
                median = signal.get('Yesterday_Median', 0)
                threshold = signal.get('Entry_Threshold', 0)
                current = signal.get('Current_Price', 0)
                triggered = "✓" if signal.get('Above_Threshold', False) else "-"
                
                f.write(f"{triggered} {symbol}: Median={median:.2f}, Threshold={threshold:.2f}, Current={current:.2f}\n")
        f.write("\n")
        
        # Triggered signals
        if triggered_count > 0:
            f.write("--- TRIGGERED SIGNALS ---\n")
            for signal in signals_data:
                if signal.get('Inside Value (Combined)') == 'Yes' and signal.get('Above_Threshold', False):
                    symbol = signal.get('Symbol', 'Unknown')
                    threshold = signal.get('Entry_Threshold', 0)
                    current = signal.get('Current_Price', 0)
                    pct_above = (current - threshold) / threshold * 100
                    
                    f.write(f"- {symbol}: Price={current:.2f}, Above threshold by {pct_above:.2f}%\n")
            f.write("\n")
        
        # Trade summary
        trades_executed = [s for s in signals_data if s.get('Trades_Executed', False)]
        if trades_executed:
            f.write("--- TRADES EXECUTED ---\n")
            for trade in trades_executed:
                symbol = trade.get('Symbol', 'Unknown')
                f.write(f"- {symbol}:\n")
                
                future_details = trade.get('Future_Details', {})
                option_details = trade.get('Option_Details', {})
                
                if future_details:
                    entry_price = future_details.get('Entry_Price', 0)
                    quantity = future_details.get('Quantity', 0)
                    f.write(f"  * Future: {quantity} @ ₹{entry_price:.2f}\n")
                
                if option_details:
                    option_symbol = option_details.get('Symbol', 'Unknown')
                    entry_price = option_details.get('Entry_Price', 0)
                    quantity = option_details.get('Quantity', 0)
                    f.write(f"  * Option: {option_symbol} - {quantity} @ ₹{entry_price:.2f}\n")
                
                # Flip trades
                flip_future = trade.get('Flip_Future_Details', {})
                flip_option = trade.get('Flip_Option_Details', {})
                
                if flip_future or flip_option:
                    f.write(f"  * Position Flipped: Yes\n")
    
    logger.info(f"Daily report generated: {filepath}")
    return filepath

def check_market_hours():
    """
    Check if the current time is within market hours.
    
    Returns:
        bool: True if within market hours, False otherwise
    """
    now = datetime.now()
    
    # Check if it's a weekday (0 = Monday, 4 = Friday)
    if now.weekday() > 4:
        return False
    
    # Market hours are 9:15 AM to 3:30 PM
    market_start = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 09:15:00", "%Y-%m-%d %H:%M:%S")
    market_end = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 15:30:00", "%Y-%m-%d %H:%M:%S")
    
    return market_start <= now <= market_end

def get_min_quantity(tsl, symbol, exchange, is_option=False):
    """
    Get the minimum quantity for a trade based on lot size.
    
    Args:
        tsl: Tradehull instance
        symbol: Trading symbol
        exchange: Exchange code
        is_option: Whether this is an option symbol
        
    Returns:
        int: Minimum quantity for the trade
    """
    try:
        # For options and futures, get lot size
        if is_option or exchange == "NFO":
            lot_size = tsl.get_lot_size(symbol)
            # Return lot size if valid, otherwise default to 1
            return max(1, lot_size) if lot_size else 1
        else:
            # For equities, minimum quantity is 1
            return 1
    except Exception as e:
        logger.error(f"Error getting minimum quantity for {symbol}: {e}")
        return 1  # Default to 1 in case of error

def place_entry_orders(tsl, stock_details):
    """
    Place the initial entry orders (both futures and options).
    
    Args:
        tsl: Tradehull instance
        stock_details: Dictionary with stock details
        
    Returns:
        tuple: (updated_stock_details, success)
    """
    symbol = stock_details.get('Symbol')
    exchange = stock_details.get('Exchange')
    current_price = stock_details.get('Current_Price')
    entry_threshold = stock_details.get('Entry_Threshold')
    
    try:
        # Make a copy of stock details to update
        updated_details = stock_details.copy()
        success = False
        
        # Get minimum quantities
        futures_quantity = get_min_quantity(tsl, symbol, exchange)
        
        # Place futures order - STOPMARKET to trigger when price crosses threshold
        futures_order_id = tsl.order_placement(
            tradingsymbol=symbol,
            exchange=exchange,
            quantity=futures_quantity,
            price=0,  # Market price when triggered
            trigger_price=entry_threshold,  # Only triggers when price crosses this threshold
            order_type='STOPMARKET',
            transaction_type='BUY',
            trade_type='MIS'
        )
        
        if futures_order_id:
            logger.info(f"Futures entry order placed for {symbol} - Order ID: {futures_order_id}")
            trade_logger.info(f"ORDER | FUTURES ENTRY | {symbol} | Quantity: {futures_quantity} | Trigger: {entry_threshold} | Order ID: {futures_order_id}")
            
            # Store futures order details
            updated_details['Future_Details'] = {
                'Order_ID': futures_order_id,
                'Quantity': futures_quantity,
                'Trigger_Price': entry_threshold,
                'Status': 'PENDING',
                'Entry_Price': None,  # Will be updated after execution
                'Stop_Loss': None,    # Will be calculated after execution
                'Target': None,       # Will be calculated after execution
                'Stop_Loss_Order_ID': None,
                'Target_Order_ID': None
            }
            
            success = True
        else:
            logger.error(f"Failed to place futures entry order for {symbol}")
        
        # Place options order
        # Get ATM Call option details
        option_symbol, strike, option_price = get_atm_option_info(tsl, symbol, option_type="CE")
        
        if option_symbol and option_price > 0:
            # Get option quantity (in lots)
            option_quantity = get_min_quantity(tsl, option_symbol, "NFO", is_option=True)
            
            # Place option order - using STOPMARKET for consistency with futures
            option_order_id = tsl.order_placement(
                tradingsymbol=option_symbol,
                exchange="NFO",
                quantity=option_quantity,
                price=0,  # Market price when triggered
                trigger_price=entry_threshold,  # Trigger when the underlying crosses threshold
                order_type='STOPMARKET',
                transaction_type='BUY',
                trade_type='MIS'
            )
            
            if option_order_id:
                logger.info(f"Option entry order placed for {option_symbol} - Order ID: {option_order_id}")
                trade_logger.info(f"ORDER | OPTION ENTRY | {option_symbol} | Quantity: {option_quantity} | Trigger: {entry_threshold} | Order ID: {option_order_id}")
                
                # Store option order details
                updated_details['Option_Details'] = {
                    'Symbol': option_symbol,
                    'Strike': strike,
                    'Estimated_Price': option_price,
                    'Order_ID': option_order_id,
                    'Quantity': option_quantity,
                    'Status': 'PENDING',
                    'Entry_Price': None,  # Will be updated after execution
                    'Stop_Loss': None,    # Will be calculated after execution
                    'Target': None,       # Will be calculated after execution
                    'Stop_Loss_Order_ID': None,
                    'Target_Order_ID': None
                }
                
                success = success and True  # Both orders must succeed
            else:
                logger.error(f"Failed to place option entry order for {option_symbol}")
                # If option order fails but futures succeeded, we'll still continue
        else:
            logger.error(f"Failed to get option details for {symbol}")
            # If we can't get option details, we'll still continue with futures only
        
        # Mark the stock as having trades placed
        updated_details['Trades_Placed'] = success
        updated_details['Trades_Placed_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return updated_details, success
    
    except Exception as e:
        logger.error(f"Error placing entry orders for {symbol}: {e}", exc_info=True)
        return stock_details, False

def monitor_order_execution(tsl, stock_details):
    """
    Monitor order execution status and place stop loss and target orders when entry orders are executed.
    
    Args:
        tsl: Tradehull instance
        stock_details: Dictionary with stock details
        
    Returns:
        tuple: (updated_stock_details, status_changed)
    """
    symbol = stock_details.get('Symbol')
    updated = False
    
    try:
        # Make a copy of stock details to update
        updated_details = stock_details.copy()
        
        # Check futures order status
        if 'Future_Details' in updated_details and updated_details['Future_Details'].get('Status') == 'PENDING':
            futures_order_id = updated_details['Future_Details'].get('Order_ID')
            
            if futures_order_id:
                order_status = tsl.get_order_status(futures_order_id)
                
                if order_status == "Completed":
                    # Order executed - update status and get execution price
                    execution_price = tsl.get_executed_price(futures_order_id)
                    
                    updated_details['Future_Details']['Status'] = 'EXECUTED'
                    updated_details['Future_Details']['Entry_Price'] = execution_price
                    
                    # Calculate stop loss (1% below entry) and target (1% above entry)
                    stop_loss_price = round(execution_price * 0.99, 2)
                    target_price = round(execution_price * 1.01, 2)
                    
                    updated_details['Future_Details']['Stop_Loss'] = stop_loss_price
                    updated_details['Future_Details']['Target'] = target_price
                    
                    # Place stop loss order
                    quantity = updated_details['Future_Details'].get('Quantity')
                    
                    stop_loss_order_id = tsl.order_placement(
                        tradingsymbol=symbol,
                        exchange=updated_details.get('Exchange'),
                        quantity=quantity,
                        price=0,  # Market price when triggered
                        trigger_price=stop_loss_price,
                        order_type='STOPMARKET',
                        transaction_type='SELL',
                        trade_type='MIS'
                    )
                    
                    if stop_loss_order_id:
                        updated_details['Future_Details']['Stop_Loss_Order_ID'] = stop_loss_order_id
                        logger.info(f"Stop loss order placed for {symbol} futures - Order ID: {stop_loss_order_id}")
                        trade_logger.info(f"ORDER | FUTURES SL | {symbol} | Price: {stop_loss_price} | Order ID: {stop_loss_order_id}")
                    
                    # Place target order
                    target_order_id = tsl.order_placement(
                        tradingsymbol=symbol,
                        exchange=updated_details.get('Exchange'),
                        quantity=quantity,
                        price=target_price,
                        trigger_price=0,
                        order_type='LIMIT',
                        transaction_type='SELL',
                        trade_type='MIS'
                    )
                    
                    if target_order_id:
                        updated_details['Future_Details']['Target_Order_ID'] = target_order_id
                        logger.info(f"Target order placed for {symbol} futures - Order ID: {target_order_id}")
                        trade_logger.info(f"ORDER | FUTURES TARGET | {symbol} | Price: {target_price} | Order ID: {target_order_id}")
                    
                    updated = True
                    logger.info(f"Futures order executed for {symbol} at {execution_price}")
                    trade_logger.info(f"EXECUTED | FUTURES | {symbol} | Price: {execution_price} | Quantity: {quantity}")
                
                elif order_status == "Rejected" or order_status == "Cancelled":
                    # Order rejected or cancelled
                    updated_details['Future_Details']['Status'] = 'FAILED'
                    logger.warning(f"Futures order failed for {symbol} - Status: {order_status}")
                    updated = True
        
        # Check options order status
        if 'Option_Details' in updated_details and updated_details['Option_Details'].get('Status') == 'PENDING':
            option_order_id = updated_details['Option_Details'].get('Order_ID')
            
            if option_order_id:
                order_status = tsl.get_order_status(option_order_id)
                
                if order_status == "Completed":
                    # Order executed - update status and get execution price
                    execution_price = tsl.get_executed_price(option_order_id)
                    option_symbol = updated_details['Option_Details'].get('Symbol')
                    
                    updated_details['Option_Details']['Status'] = 'EXECUTED'
                    updated_details['Option_Details']['Entry_Price'] = execution_price
                    
                    # Calculate stop loss (10% below entry) and target (20% above entry)
                    stop_loss_price = round(execution_price * 0.90, 2)
                    target_price = round(execution_price * 1.20, 2)
                    
                    updated_details['Option_Details']['Stop_Loss'] = stop_loss_price
                    updated_details['Option_Details']['Target'] = target_price
                    
                    # Place stop loss order
                    quantity = updated_details['Option_Details'].get('Quantity')
                    
                    stop_loss_order_id = tsl.order_placement(
                        tradingsymbol=option_symbol,
                        exchange="NFO",
                        quantity=quantity,
                        price=0,  # Market price when triggered
                        trigger_price=stop_loss_price,
                        order_type='STOPMARKET',
                        transaction_type='SELL',
                        trade_type='MIS'
                    )
                    
                    if stop_loss_order_id:
                        updated_details['Option_Details']['Stop_Loss_Order_ID'] = stop_loss_order_id
                        logger.info(f"Stop loss order placed for {option_symbol} - Order ID: {stop_loss_order_id}")
                        trade_logger.info(f"ORDER | OPTION SL | {option_symbol} | Price: {stop_loss_price} | Order ID: {stop_loss_order_id}")
                    
                    # Place target order
                    target_order_id = tsl.order_placement(
                        tradingsymbol=option_symbol,
                        exchange="NFO",
                        quantity=quantity,
                        price=target_price,
                        trigger_price=0,
                        order_type='LIMIT',
                        transaction_type='SELL',
                        trade_type='MIS'
                    )
                    
                    if target_order_id:
                        updated_details['Option_Details']['Target_Order_ID'] = target_order_id
                        logger.info(f"Target order placed for {option_symbol} - Order ID: {target_order_id}")
                        trade_logger.info(f"ORDER | OPTION TARGET | {option_symbol} | Price: {target_price} | Order ID: {target_order_id}")
                    
                    updated = True
                    logger.info(f"Option order executed for {option_symbol} at {execution_price}")
                    trade_logger.info(f"EXECUTED | OPTION | {option_symbol} | Price: {execution_price} | Quantity: {quantity}")
                
                elif order_status == "Rejected" or order_status == "Cancelled":
                    # Order rejected or cancelled
                    updated_details['Option_Details']['Status'] = 'FAILED'
                    logger.warning(f"Option order failed for {updated_details['Option_Details'].get('Symbol')} - Status: {order_status}")
                    updated = True
        
        # Check if both futures and options orders have been executed/failed
        future_status = updated_details.get('Future_Details', {}).get('Status')
        option_status = updated_details.get('Option_Details', {}).get('Status')
        
        if (future_status in ['EXECUTED', 'FAILED']) and (option_status in ['EXECUTED', 'FAILED'] or 'Option_Details' not in updated_details):
            updated_details['Trades_Executed'] = True
            updated_details['Trades_Executed_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return updated_details, updated
    
    except Exception as e:
        logger.error(f"Error monitoring order execution for {symbol}: {e}", exc_info=True)
        return stock_details, False

def monitor_stop_loss_and_target(tsl, stock_details):
    """
    Monitor stop loss and target orders for executed trades.
    
    Args:
        tsl: Tradehull instance
        stock_details: Dictionary with stock details
        
    Returns:
        tuple: (updated_stock_details, status_changed, event_type)
    """
    symbol = stock_details.get('Symbol')
    updated = False
    event_type = None
    
    try:
        # Make a copy of stock details to update
        updated_details = stock_details.copy()
        
        # Check futures stop loss and target
        if 'Future_Details' in updated_details and updated_details['Future_Details'].get('Status') == 'EXECUTED':
            # Check stop loss order
            sl_order_id = updated_details['Future_Details'].get('Stop_Loss_Order_ID')
            
            if sl_order_id:
                sl_status = tsl.get_order_status(sl_order_id)
                
                if sl_status == "Completed":
                    # Stop loss hit
                    updated_details['Future_Details']['Status'] = 'STOP_LOSS_HIT'
                    updated_details['Future_Details']['Exit_Price'] = updated_details['Future_Details'].get('Stop_Loss')
                    updated_details['Future_Details']['Exit_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Cancel the target order
                    target_order_id = updated_details['Future_Details'].get('Target_Order_ID')
                    if target_order_id:
                        try:
                            tsl.cancel_order(target_order_id)
                            logger.info(f"Cancelled target order for {symbol} futures - Order ID: {target_order_id}")
                        except Exception as e:
                            logger.error(f"Error cancelling target order for {symbol} futures: {e}")
                    
                    # Flip position to short (if not already done)
                    if not updated_details.get('Flip_Future_Details'):
                        updated_details = flip_future_position(tsl, updated_details)
                    
                    updated = True
                    event_type = 'FUTURE_STOP_LOSS'
                    logger.info(f"Futures stop loss hit for {symbol}")
                    trade_logger.info(f"STOP_LOSS | FUTURES | {symbol} | Price: {updated_details['Future_Details'].get('Stop_Loss')}")
            
            # Check target order
            target_order_id = updated_details['Future_Details'].get('Target_Order_ID')
            
            if target_order_id:
                target_status = tsl.get_order_status(target_order_id)
                
                if target_status == "Completed":
                    # Target hit
                    updated_details['Future_Details']['Status'] = 'TARGET_HIT'
                    updated_details['Future_Details']['Exit_Price'] = updated_details['Future_Details'].get('Target')
                    updated_details['Future_Details']['Exit_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Cancel the stop loss order
                    if sl_order_id:
                        try:
                            tsl.cancel_order(sl_order_id)
                            logger.info(f"Cancelled stop loss order for {symbol} futures - Order ID: {sl_order_id}")
                        except Exception as e:
                            logger.error(f"Error cancelling stop loss order for {symbol} futures: {e}")
                    
                    updated = True
                    event_type = 'FUTURE_TARGET'
                    logger.info(f"Futures target hit for {symbol}")
                    trade_logger.info(f"TARGET | FUTURES | {symbol} | Price: {updated_details['Future_Details'].get('Target')}")
        
        # Check options stop loss and target
        if 'Option_Details' in updated_details and updated_details['Option_Details'].get('Status') == 'EXECUTED':
            option_symbol = updated_details['Option_Details'].get('Symbol')
            
            # Check stop loss order
            sl_order_id = updated_details['Option_Details'].get('Stop_Loss_Order_ID')
            
            if sl_order_id:
                sl_status = tsl.get_order_status(sl_order_id)
                
                if sl_status == "Completed":
                    # Stop loss hit
                    updated_details['Option_Details']['Status'] = 'STOP_LOSS_HIT'
                    updated_details['Option_Details']['Exit_Price'] = updated_details['Option_Details'].get('Stop_Loss')
                    updated_details['Option_Details']['Exit_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Cancel the target order
                    target_order_id = updated_details['Option_Details'].get('Target_Order_ID')
                    if target_order_id:
                        try:
                            tsl.cancel_order(target_order_id)
                            logger.info(f"Cancelled target order for {option_symbol} - Order ID: {target_order_id}")
                        except Exception as e:
                            logger.error(f"Error cancelling target order for {option_symbol}: {e}")
                    
                    # Flip position to put option (if not already done)
                    if not updated_details.get('Flip_Option_Details'):
                        updated_details = flip_option_position(tsl, updated_details)
                    
                    updated = True
                    event_type = 'OPTION_STOP_LOSS'
                    logger.info(f"Option stop loss hit for {option_symbol}")
                    trade_logger.info(f"STOP_LOSS | OPTION | {option_symbol} | Price: {updated_details['Option_Details'].get('Stop_Loss')}")
            
            # Check target order
            target_order_id = updated_details['Option_Details'].get('Target_Order_ID')
            
            if target_order_id:
                target_status = tsl.get_order_status(target_order_id)
                
                if target_status == "Completed":
                    # Target hit
                    updated_details['Option_Details']['Status'] = 'TARGET_HIT'
                    updated_details['Option_Details']['Exit_Price'] = updated_details['Option_Details'].get('Target')
                    updated_details['Option_Details']['Exit_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Cancel the stop loss order
                    if sl_order_id:
                        try:
                            tsl.cancel_order(sl_order_id)
                            logger.info(f"Cancelled stop loss order for {option_symbol} - Order ID: {sl_order_id}")
                        except Exception as e:
                            logger.error(f"Error cancelling stop loss order for {option_symbol}: {e}")
                    
                    updated = True
                    event_type = 'OPTION_TARGET'
                    logger.info(f"Option target hit for {option_symbol}")
                    trade_logger.info(f"TARGET | OPTION | {option_symbol} | Price: {updated_details['Option_Details'].get('Target')}")
        
        # Check flipped futures position
        if 'Flip_Future_Details' in updated_details and updated_details['Flip_Future_Details'].get('Status') == 'EXECUTED':
            # Check stop loss order
            sl_order_id = updated_details['Flip_Future_Details'].get('Stop_Loss_Order_ID')
            
            if sl_order_id:
                sl_status = tsl.get_order_status(sl_order_id)
                
                if sl_status == "Completed":
                    # Stop loss hit
                    updated_details['Flip_Future_Details']['Status'] = 'STOP_LOSS_HIT'
                    updated_details['Flip_Future_Details']['Exit_Price'] = updated_details['Flip_Future_Details'].get('Stop_Loss')
                    updated_details['Flip_Future_Details']['Exit_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Cancel the target order
                    target_order_id = updated_details['Flip_Future_Details'].get('Target_Order_ID')
                    if target_order_id:
                        try:
                            tsl.cancel_order(target_order_id)
                            logger.info(f"Cancelled target order for flipped {symbol} futures - Order ID: {target_order_id}")
                        except Exception as e:
                            logger.error(f"Error cancelling target order for flipped {symbol} futures: {e}")
                    
                    updated = True
                    event_type = 'FLIP_FUTURE_STOP_LOSS'
                    logger.info(f"Flipped futures stop loss hit for {symbol}")
                    trade_logger.info(f"STOP_LOSS | FLIP_FUTURES | {symbol} | Price: {updated_details['Flip_Future_Details'].get('Stop_Loss')}")
            
            # Check target order
            target_order_id = updated_details['Flip_Future_Details'].get('Target_Order_ID')
            
            if target_order_id:
                target_status = tsl.get_order_status(target_order_id)
                
                if target_status == "Completed":
                    # Target hit
                    updated_details['Flip_Future_Details']['Status'] = 'TARGET_HIT'
                    updated_details['Flip_Future_Details']['Exit_Price'] = updated_details['Flip_Future_Details'].get('Target')
                    updated_details['Flip_Future_Details']['Exit_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Cancel the stop loss order
                    if sl_order_id:
                        try:
                            tsl.cancel_order(sl_order_id)
                            logger.info(f"Cancelled stop loss order for flipped {symbol} futures - Order ID: {sl_order_id}")
                        except Exception as e:
                            logger.error(f"Error cancelling stop loss order for flipped {symbol} futures: {e}")
                    
                    updated = True
                    event_type = 'FLIP_FUTURE_TARGET'
                    logger.info(f"Flipped futures target hit for {symbol}")
                    trade_logger.info(f"TARGET | FLIP_FUTURES | {symbol} | Price: {updated_details['Flip_Future_Details'].get('Target')}")
        
        # Check flipped options position
        if 'Flip_Option_Details' in updated_details and updated_details['Flip_Option_Details'].get('Status') == 'EXECUTED':
            option_symbol = updated_details['Flip_Option_Details'].get('Symbol')
            
            # Check stop loss order
            sl_order_id = updated_details['Flip_Option_Details'].get('Stop_Loss_Order_ID')
            
            if sl_order_id:
                sl_status = tsl.get_order_status(sl_order_id)
                
                if sl_status == "Completed":
                    # Stop loss hit
                    updated_details['Flip_Option_Details']['Status'] = 'STOP_LOSS_HIT'
                    updated_details['Flip_Option_Details']['Exit_Price'] = updated_details['Flip_Option_Details'].get('Stop_Loss')
                    updated_details['Flip_Option_Details']['Exit_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Cancel the target order
                    target_order_id = updated_details['Flip_Option_Details'].get('Target_Order_ID')
                    if target_order_id:
                        try:
                            tsl.cancel_order(target_order_id)
                            logger.info(f"Cancelled target order for flipped {option_symbol} - Order ID: {target_order_id}")
                        except Exception as e:
                            logger.error(f"Error cancelling target order for flipped {option_symbol}: {e}")
                    
                    updated = True
                    event_type = 'FLIP_OPTION_STOP_LOSS'
                    logger.info(f"Flipped option stop loss hit for {option_symbol}")
                    trade_logger.info(f"STOP_LOSS | FLIP_OPTION | {option_symbol} | Price: {updated_details['Flip_Option_Details'].get('Stop_Loss')}")
            
            # Check target order
            target_order_id = updated_details['Flip_Option_Details'].get('Target_Order_ID')
            
            if target_order_id:
                target_status = tsl.get_order_status(target_order_id)
                
                if target_status == "Completed":
                    # Target hit
                    updated_details['Flip_Option_Details']['Status'] = 'TARGET_HIT'
                    updated_details['Flip_Option_Details']['Exit_Price'] = updated_details['Flip_Option_Details'].get('Target')
                    updated_details['Flip_Option_Details']['Exit_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Cancel the stop loss order
                    if sl_order_id:
                        try:
                            tsl.cancel_order(sl_order_id)
                            logger.info(f"Cancelled stop loss order for flipped {option_symbol} - Order ID: {sl_order_id}")
                        except Exception as e:
                            logger.error(f"Error cancelling stop loss order for flipped {option_symbol}: {e}")
                    
                    updated = True
                    event_type = 'FLIP_OPTION_TARGET'
                    logger.info(f"Flipped option target hit for {option_symbol}")
                    trade_logger.info(f"TARGET | FLIP_OPTION | {option_symbol} | Price: {updated_details['Flip_Option_Details'].get('Target')}")
        
        # Check if all trades are completed
        all_positions_closed = True
        
        # Check original positions
        if 'Future_Details' in updated_details and updated_details['Future_Details'].get('Status') == 'EXECUTED':
            all_positions_closed = False
        if 'Option_Details' in updated_details and updated_details['Option_Details'].get('Status') == 'EXECUTED':
            all_positions_closed = False
        
        # Check flipped positions
        if 'Flip_Future_Details' in updated_details and updated_details['Flip_Future_Details'].get('Status') == 'EXECUTED':
            all_positions_closed = False
        if 'Flip_Option_Details' in updated_details and updated_details['Flip_Option_Details'].get('Status') == 'EXECUTED':
            all_positions_closed = False
        
        if all_positions_closed:
            updated_details['All_Positions_Closed'] = True
            updated_details['Positions_Closed_Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return updated_details, updated, event_type
    
    except Exception as e:
        logger.error(f"Error monitoring stop loss and target for {symbol}: {e}", exc_info=True)
        return stock_details, False, None

def flip_future_position(tsl, stock_details):
    """
    Flip a futures position from long to short after stop loss is hit.
    
    Args:
        tsl: Tradehull instance
        stock_details: Dictionary with stock details
        
    Returns:
        dict: Updated stock details with flip position information
    """
    symbol = stock_details.get('Symbol')
    exchange = stock_details.get('Exchange')
    
    try:
        # Get quantity from original position
        quantity = stock_details.get('Future_Details', {}).get('Quantity', 0)
        
        if quantity <= 0:
            logger.error(f"Invalid quantity for flipping futures position for {symbol}")
            return stock_details
        
        # Place short futures order
        short_order_id = tsl.order_placement(
            tradingsymbol=symbol,
            exchange=exchange,
            quantity=quantity,
            price=0,  # Market price
            trigger_price=0,
            order_type='MARKET',
            transaction_type='SELL',
            trade_type='MIS'
        )
        
        if not short_order_id:
            logger.error(f"Failed to place short futures order for {symbol}")
            return stock_details
        
        logger.info(f"Short futures order placed for {symbol} - Order ID: {short_order_id}")
        trade_logger.info(f"ORDER | FLIP_FUTURES_ENTRY | {symbol} | Quantity: {quantity} | Order ID: {short_order_id}")
        
        # Wait for order execution
        execution_price = None
        max_retries = 10
        
        for retry in range(max_retries):
            order_status = tsl.get_order_status(short_order_id)
            
            if order_status == "Completed":
                execution_price = tsl.get_executed_price(short_order_id)
                logger.info(f"Short futures order executed for {symbol} at {execution_price}")
                trade_logger.info(f"EXECUTED | FLIP_FUTURES | {symbol} | Price: {execution_price} | Quantity: {quantity}")
                break
            
            if order_status == "Rejected" or order_status == "Cancelled":
                logger.warning(f"Short futures order failed for {symbol} - Status: {order_status}")
                return stock_details
            
            # Wait before checking again
            time.sleep(2)
        
        if not execution_price:
            logger.warning(f"Timed out waiting for short futures order execution for {symbol}")
            return stock_details
        
        # Calculate stop loss (1% above entry for short) and target (1% below entry for short)
        stop_loss_price = round(execution_price * 1.01, 2)
        target_price = round(execution_price * 0.99, 2)
        
        # Place stop loss order (buy to cover)
        stop_loss_order_id = tsl.order_placement(
            tradingsymbol=symbol,
            exchange=exchange,
            quantity=quantity,
            price=0,  # Market price when triggered
            trigger_price=stop_loss_price,
            order_type='STOPMARKET',
            transaction_type='BUY',  # Buy to cover
            trade_type='MIS'
        )
        
        if not stop_loss_order_id:
            logger.error(f"Failed to place stop loss order for short futures for {symbol}")
        else:
            logger.info(f"Stop loss order placed for short futures for {symbol} - Order ID: {stop_loss_order_id}")
            trade_logger.info(f"ORDER | FLIP_FUTURES_SL | {symbol} | Price: {stop_loss_price} | Order ID: {stop_loss_order_id}")
        
        # Place target order (buy to cover)
        target_order_id = tsl.order_placement(
            tradingsymbol=symbol,
            exchange=exchange,
            quantity=quantity,
            price=target_price,
            trigger_price=0,
            order_type='LIMIT',
            transaction_type='BUY',  # Buy to cover
            trade_type='MIS'
        )
        
        if not target_order_id:
            logger.error(f"Failed to place target order for short futures for {symbol}")
        else:
            logger.info(f"Target order placed for short futures for {symbol} - Order ID: {target_order_id}")
            trade_logger.info(f"ORDER | FLIP_FUTURES_TARGET | {symbol} | Price: {target_price} | Order ID: {target_order_id}")
        
        # Update stock details with flip position information
        stock_details['Flip_Future_Details'] = {
            'Order_ID': short_order_id,
            'Status': 'EXECUTED',
            'Quantity': quantity,
            'Entry_Price': execution_price,
            'Stop_Loss': stop_loss_price,
            'Target': target_price,
            'Stop_Loss_Order_ID': stop_loss_order_id,
            'Target_Order_ID': target_order_id,
            'Entry_Time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return stock_details
    
    except Exception as e:
        logger.error(f"Error flipping futures position for {symbol}: {e}", exc_info=True)
        return stock_details

def flip_option_position(tsl, stock_details):
    """
    Flip an option position from call to put after stop loss is hit.
    
    Args:
        tsl: Tradehull instance
        stock_details: Dictionary with stock details
        
    Returns:
        dict: Updated stock details with flip position information
    """
    symbol = stock_details.get('Symbol')
    
    try:
        # Get ATM Put option
        option_symbol, strike, option_price = get_atm_option_info(tsl, symbol, option_type="PE")
        
        if not option_symbol or option_price <= 0:
            logger.error(f"Failed to get put option details for {symbol}")
            return stock_details
        
        # Get quantity based on the original call option
        quantity = stock_details.get('Option_Details', {}).get('Quantity', 0)
        
        if quantity <= 0:
            logger.error(f"Invalid quantity for flipping option position for {symbol}")
            return stock_details
        
        # Place put option order
        put_order_id = tsl.order_placement(
            tradingsymbol=option_symbol,
            exchange="NFO",
            quantity=quantity,
            price=0,  # Market price
            trigger_price=0,
            order_type='MARKET',
            transaction_type='BUY',
            trade_type='MIS'
        )
        
        if not put_order_id:
            logger.error(f"Failed to place put option order for {option_symbol}")
            return stock_details
        
        logger.info(f"Put option order placed for {option_symbol} - Order ID: {put_order_id}")
        trade_logger.info(f"ORDER | FLIP_OPTION_ENTRY | {option_symbol} | Quantity: {quantity} | Order ID: {put_order_id}")
        
        # Wait for order execution
        execution_price = None
        max_retries = 10
        
        for retry in range(max_retries):
            order_status = tsl.get_order_status(put_order_id)
            
            if order_status == "Completed":
                execution_price = tsl.get_executed_price(put_order_id)
                logger.info(f"Put option order executed for {option_symbol} at {execution_price}")
                trade_logger.info(f"EXECUTED | FLIP_OPTION | {option_symbol} | Price: {execution_price} | Quantity: {quantity}")
                break
            
            if order_status == "Rejected" or order_status == "Cancelled":
                logger.warning(f"Put option order failed for {option_symbol} - Status: {order_status}")
                return stock_details
            
            # Wait before checking again
            time.sleep(2)
        
        if not execution_price:
            logger.warning(f"Timed out waiting for put option order execution for {option_symbol}")
            return stock_details
        
        # Calculate stop loss (10% below entry) and target (20% above entry)
        stop_loss_price = round(execution_price * 0.90, 2)
        target_price = round(execution_price * 1.20, 2)
        
        # Place stop loss order
        stop_loss_order_id = tsl.order_placement(
            tradingsymbol=option_symbol,
            exchange="NFO",
            quantity=quantity,
            price=0,  # Market price when triggered
            trigger_price=stop_loss_price,
            order_type='STOPMARKET',
            transaction_type='SELL',
            trade_type='MIS'
        )
        
        if not stop_loss_order_id:
            logger.error(f"Failed to place stop loss order for put option for {option_symbol}")
        else:
            logger.info(f"Stop loss order placed for put option for {option_symbol} - Order ID: {stop_loss_order_id}")
            trade_logger.info(f"ORDER | FLIP_OPTION_SL | {option_symbol} | Price: {stop_loss_price} | Order ID: {stop_loss_order_id}")
        
        # Place target order
        target_order_id = tsl.order_placement(
            tradingsymbol=option_symbol,
            exchange="NFO",
            quantity=quantity,
            price=target_price,
            trigger_price=0,
            order_type='LIMIT',
            transaction_type='SELL',
            trade_type='MIS'
        )
        
        if not target_order_id:
            logger.error(f"Failed to place target order for put option for {option_symbol}")
        else:
            logger.info(f"Target order placed for put option for {option_symbol} - Order ID: {target_order_id}")
            trade_logger.info(f"ORDER | FLIP_OPTION_TARGET | {option_symbol} | Price: {target_price} | Order ID: {target_order_id}")
        
        # Update stock details with flip position information
        stock_details['Flip_Option_Details'] = {
            'Symbol': option_symbol,
            'Strike': strike,
            'Order_ID': put_order_id,
            'Status': 'EXECUTED',
            'Quantity': quantity,
            'Entry_Price': execution_price,
            'Stop_Loss': stop_loss_price,
            'Target': target_price,
            'Stop_Loss_Order_ID': stop_loss_order_id,
            'Target_Order_ID': target_order_id,
            'Entry_Time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return stock_details
    
    except Exception as e:
        logger.error(f"Error flipping option position for {symbol}: {e}", exc_info=True)
        return stock_details

def send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs):
    """
    Send Telegram alerts using multiple different bots.
    
    Args:
        tsl: Tradehull instance
        message: Alert message text
        bot_configs: List of dictionaries with bot_token and chat_id
        
    Returns:
        bool: True if all alerts were sent successfully
    """
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

def scan_stocks_continuous_multi_bots(client_code, token_id, watchlist, bot_configs, scan_interval=10, hot_list_interval=30, active_trades_interval=5):
    """
    Continuously scan stocks for inside value patterns, manage trades, and send alerts using multiple bots.
    
    Args:
        client_code: Dhan client code
        token_id: Dhan authentication token
        watchlist: List of stock symbols to monitor
        bot_configs: List of dictionaries with bot_token and chat_id
        scan_interval: Seconds between full scans
        hot_list_interval: Seconds between hot list scans
        active_trades_interval: Seconds between active trades monitoring
        
    Returns:
        None
    """
    # Initialize Tradehull client
    tsl = Tradehull(client_code, token_id)
    
    # Send startup message
    startup_message = f"🚀 Inside Value Intraday Scanner Started\n\nMonitoring {len(watchlist)} stocks\nScan interval: {scan_interval} seconds\nHot list scan interval: {hot_list_interval} seconds\nActive trades scan interval: {active_trades_interval} seconds"
    send_telegram_alerts_to_multiple_bots(tsl, startup_message, bot_configs)
    
    # Track already alerted stocks to avoid duplicate alerts
    inside_value_alerted_stocks = set()  # For inside value pattern alerts
    threshold_alerted_stocks = set()     # For threshold crossing alerts
    traded_stocks = set()                # For stocks that have been traded today
    all_signals = []
    
    # Create watchlists
    main_watchlist = watchlist  # Full list of stocks to scan
    hot_watchlist = {}          # Stocks with inside value pattern but haven't crossed threshold
    active_trades = {}          # Stocks with active trades
    
    # Track the last time each list was scanned
    last_full_scan = datetime.now() - timedelta(seconds=scan_interval)  # Force immediate first scan
    last_hot_scan = datetime.now() - timedelta(seconds=hot_list_interval)  # Force immediate first scan
    last_active_scan = datetime.now() - timedelta(seconds=active_trades_interval)  # Force immediate first scan
    
    # Run continuous scanning loop during market hours
    while check_market_hours():
        current_time = datetime.now()
        
        # Determine which lists to scan
        scan_full_list = (current_time - last_full_scan).total_seconds() >= scan_interval
        scan_hot_list = (current_time - last_hot_scan).total_seconds() >= hot_list_interval
        scan_active_list = (current_time - last_active_scan).total_seconds() >= active_trades_interval
        
        # Scan active trades (highest priority, most frequent)
        if scan_active_list and active_trades:
            logger.info(f"Monitoring active trades at {current_time.strftime('%H:%M:%S')} - {len(active_trades)} stocks")
            
            for symbol, details in list(active_trades.items()):
                try:
                    # Monitor order execution and stop loss/target
                    updated_details, status_changed = monitor_order_execution(tsl, details)
                    
                    if status_changed:
                        # Update the active trade details
                        active_trades[symbol] = updated_details
                        # Also save to signals data
                        save_signal_details(updated_details)
                    
                    # Monitor stop loss and target
                    updated_details, status_changed, event_type = monitor_stop_loss_and_target(tsl, updated_details)
                    
                    if status_changed:
                        # Update the active trade details
                        active_trades[symbol] = updated_details
                        # Also save to signals data
                        save_signal_details(updated_details)
                        
                        # Send alerts based on event type
                        if event_type:
                            if event_type == 'FUTURE_STOP_LOSS':
                                # Stop loss hit for futures position
                                message = generate_stop_loss_alert_message(
                                    updated_details, 
                                    'FUTURES', 
                                    updated_details.get('Flip_Future_Details')
                                )
                                send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                            
                            elif event_type == 'FUTURE_TARGET':
                                # Target hit for futures position
                                message = generate_target_hit_message(updated_details, 'FUTURES')
                                send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                            
                            elif event_type == 'OPTION_STOP_LOSS':
                                # Stop loss hit for options position
                                message = generate_stop_loss_alert_message(
                                    updated_details, 
                                    'OPTIONS', 
                                    updated_details.get('Flip_Option_Details')
                                )
                                send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                            
                            elif event_type == 'OPTION_TARGET':
                                # Target hit for options position
                                message = generate_target_hit_message(updated_details, 'OPTIONS')
                                send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                            
                            elif event_type == 'FLIP_FUTURE_STOP_LOSS':
                                # Stop loss hit for flipped futures position
                                message = generate_stop_loss_alert_message(
                                    updated_details, 
                                    'FLIP_FUTURES', 
                                    None
                                )
                                send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                            
                            elif event_type == 'FLIP_FUTURE_TARGET':
                                # Target hit for flipped futures position
                                message = generate_target_hit_message(updated_details, 'FUTURES', True)
                                send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                            
                            elif event_type == 'FLIP_OPTION_STOP_LOSS':
                                # Stop loss hit for flipped options position
                                message = generate_stop_loss_alert_message(
                                    updated_details, 
                                    'FLIP_OPTIONS', 
                                    None
                                )
                                send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                            
                            elif event_type == 'FLIP_OPTION_TARGET':
                                # Target hit for flipped options position
                                message = generate_target_hit_message(updated_details, 'OPTIONS', True)
                                send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                    
                    # Check if all positions are closed
                    if updated_details.get('All_Positions_Closed'):
                        logger.info(f"All positions closed for {symbol}")
                        # Remove from active trades
                        active_trades.pop(symbol)
                
                except Exception as e:
                    logger.error(f"Error monitoring active trade for {symbol}: {e}", exc_info=True)
                
                # Add a small delay between stocks
                time.sleep(1)
            
            last_active_scan = current_time
        
        # Scan hot list (medium priority, medium frequency)
        if scan_hot_list and hot_watchlist:
            logger.info(f"Scanning hot list at {current_time.strftime('%H:%M:%S')} - {len(hot_watchlist)} stocks")
            
            for symbol, details in list(hot_watchlist.items()):
                try:
                    # Skip if already traded today
                    if symbol in traded_stocks:
                        continue
                    
                    # Get current price
                    current_price = get_ltp_safely(tsl, symbol)
                    threshold = details.get('Entry_Threshold', 0)
                    
                    # Update current price in details
                    details['Current_Price'] = current_price
                    details['Last_Updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    details['Above_Threshold'] = current_price >= threshold
                    
                    # Check if price has crossed threshold
                    if current_price >= threshold:
                        logger.info(f"Threshold crossed for {symbol} - Current: {current_price}, Threshold: {threshold}")
                        
                        # Place orders if not already alerted
                        if symbol not in threshold_alerted_stocks:
                            # Place entry orders
                            updated_details, success = place_entry_orders(tsl, details)
                            
                            if success:
                                # Add to active trades
                                active_trades[symbol] = updated_details
                                # Add to traded stocks
                                traded_stocks.add(symbol)
                                # Add to alerted stocks
                                threshold_alerted_stocks.add(symbol)
                                
                                # Send alert
                                message = generate_threshold_alert_message(updated_details)
                                send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                                
                                # Save signal data
                                save_signal_details(updated_details)
                                
                                # Log threshold crossing
                                signal_logger.info(f"THRESHOLD CROSSED | {symbol} | Current: {current_price} | Threshold: {threshold}")
                                
                                # Remove from hot watchlist
                                hot_watchlist.pop(symbol)
                        else:
                            # Already alerted, update hot watchlist with latest price
                            hot_watchlist[symbol] = details
                    else:
                        # Check if still inside value pattern
                        is_inside, _, _, updated_details = check_intraday_inside_value(tsl, symbol, details.get('Exchange'))
                        
                        if is_inside:
                            # Update details with latest
                            hot_watchlist[symbol] = updated_details
                        else:
                            # No longer inside value pattern, remove from hot watchlist
                            logger.info(f"Inside value pattern no longer valid for {symbol}")
                            hot_watchlist.pop(symbol)
                
                except Exception as e:
                    logger.error(f"Error processing hot list stock {symbol}: {e}", exc_info=True)
                
                # Add a small delay between stocks
                time.sleep(1)
            
            last_hot_scan = current_time
        
        # Full scan (lowest priority, least frequent)
        if scan_full_list:
            logger.info(f"Starting full scan at {current_time.strftime('%H:%M:%S')}")
            
            # Process watchlist in batches to avoid rate limiting
            batch_size = 10
            signals_this_cycle = []
            
            for i in range(0, len(main_watchlist), batch_size):
                batch = main_watchlist[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(main_watchlist)-1)//batch_size + 1} ({len(batch)} stocks)...")
                
                for symbol in batch:
                    try:
                        # Skip if already traded today
                        if symbol in traded_stocks:
                            continue
                        
                        # Determine exchange
                        exchange = "INDEX" if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"] else "NSE"
                        
                        # Check for inside value pattern
                        is_inside, median, threshold, details = check_intraday_inside_value(tsl, symbol, exchange)
                        
                        if is_inside:
                            # Store signal details
                            signals_this_cycle.append(details)
                            
                            # Check if already in hot watchlist
                            if symbol not in hot_watchlist:
                                # Add to hot watchlist
                                hot_watchlist[symbol] = details
                                logger.info(f"Added {symbol} to hot watchlist")
                                
                                # Send alert if not already sent
                                if symbol not in inside_value_alerted_stocks:
                                    message = generate_inside_value_alert_message(details)
                                    send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                                    
                                    # Mark as alerted
                                    inside_value_alerted_stocks.add(symbol)
                                    
                                    # Log inside value pattern
                                    signal_logger.info(f"INSIDE VALUE | {symbol} | Median: {median} | Threshold: {threshold}")
                            else:
                                # Update details in hot watchlist
                                hot_watchlist[symbol] = details
                            
                            # Check if price has already crossed threshold
                            current_price = details.get('Current_Price', 0)
                            if current_price >= threshold and symbol not in threshold_alerted_stocks:
                                # Place entry orders
                                updated_details, success = place_entry_orders(tsl, details)
                                
                                if success:
                                    # Add to active trades
                                    active_trades[symbol] = updated_details
                                    # Add to traded stocks
                                    traded_stocks.add(symbol)
                                    # Add to alerted stocks
                                    threshold_alerted_stocks.add(symbol)
                                    
                                    # Send alert
                                    message = generate_threshold_alert_message(updated_details)
                                    send_telegram_alerts_to_multiple_bots(tsl, message, bot_configs)
                                    
                                    # Save signal data
                                    save_signal_details(updated_details)
                                    
                                    # Log threshold crossing
                                    signal_logger.info(f"THRESHOLD CROSSED | {symbol} | Current: {current_price} | Threshold: {threshold}")
                                    
                                    # Remove from hot watchlist
                                    hot_watchlist.pop(symbol)
                        
                    except Exception as e:
                        logger.error(f"Error processing {symbol} during full scan: {e}", exc_info=True)
                    
                    # Add a small delay between stocks
                    time.sleep(1)
                
                # Add a longer delay between batches
                time.sleep(5)
            
            # Save signals from this cycle
            if signals_this_cycle:
                all_signals.extend(signals_this_cycle)
                save_signal_details(signals_this_cycle)
            
            last_full_scan = current_time
        
        # Small sleep to prevent CPU hogging
        time.sleep(1)
    
    # End of day - generate report and send summary
    if all_signals:
        report_path = generate_daily_report(all_signals)
        
        # Send end of day summary
        end_day_message = f"📊 TRADING DAY SUMMARY\n\n"
        end_day_message += f"Total stocks scanned: {len(main_watchlist)}\n"
        end_day_message += f"Inside value patterns found: {len(inside_value_alerted_stocks)}\n"
        end_day_message += f"Entry signals triggered: {len(threshold_alerted_stocks)}\n"
        end_day_message += f"Stocks traded: {len(traded_stocks)}\n\n"
        end_day_message += f"Detailed report saved to: {report_path}"
        
        send_telegram_alerts_to_multiple_bots(tsl, end_day_message, bot_configs)
    
    logger.info("Market closed. Scanning stopped.")

def main():
    """
    Main function to run the inside value intraday scanner.
    """
    # Replace with your actual credentials
    client_code = "1106534888"
    token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"
   
    # Telegram settings for multiple bots
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
    
    # Define your watchlist of stocks to scan
    watchlist = [

        'ABB', 'AUBANK', 'AARTIIND', 'ADANIENT', 'ADANIGREEN', 
        # 'ADANIPORTS', 'AMBUJACEM', 
        # 'ASHOKLEY', 'ASIANPAINT', 'AUROPHARMA', 'AXISBANK', 'BSOFT', 
        # 'BSE', 'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BANDHANBNK', 'BANKBARODA', 
        # 'BEL', 'BHARATFORG', 'BHEL', 'BPCL', 'BHARTIARTL', 
        # 'BRITANNIA', 'CANBK', 'CDSL', 'TORNTPOWER', 
        # 'CIPLA', 'COALINDIA', 'COFORGE',  
        # 'DLF', 'DABUR', 'DIVISLAB', 'DIXON', 
        # 'DRREDDY', 'GAIL',  
        # 'GODREJPROP', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE', 
        # 'HEROMOTOCO', 'HINDALCO', 'HAL', 'HINDPETRO', 'HINDUNILVR', 
        # 'ICICIBANK', 'IDFCFIRSTB', 'ITC', 
        # 'IOC', 'IRCTC', 'IRFC', 'INDUSTOWER', 'INDUSINDBK', 'INFY', 
        # 'INDIGO', 'JSWSTEEL', 'JINDALSTEL', 'JIOFIN',  
        # 'KOTAKBANK', 'LICHSGFIN', 'LTIM', 'LT', 
        # 'LUPIN', 'M&MFIN', 'M&M', 'MANAPPURAM', 
        # 'MARUTI', 'MCX',  
        # 'NMDC', 'NTPC', 'NATIONALUM', 'ONGC', 'OFSS',  
        # 'PERSISTENT', 'PETRONET',  
        # 'PFC', 'POWERGRID', 'PNB', 'RECLTD', 
        # 'RELIANCE', 'SBICARD', 'SBILIFE', 'MOTHERSON',  
        # 'SIEMENS', 'SBIN', 'SAIL', 'SUNPHARMA',  
        # 'TATACONSUM', 'TATACHEM', 'TCS', 'TATAMOTORS', 
        # 'TATAPOWER', 'TATASTEEL', 'TECHM', 'FEDERALBNK', 'INDHOTEL',  
        # 'TITAN', 'TRENT', 'UPL', 'ULTRACEMCO', 
        # 'VBL', 'VEDL', 'IDEA', 'VOLTAS', 'WIPRO', 'ZOMATO'

    ]
    
    # Check if it's market hours
    if not check_market_hours():
        logger.info("Outside market hours. Exiting.")
        return
    
    # Run the continuous scanner
    scan_stocks_continuous_multi_bots(
        client_code=client_code,
        token_id=token_id,
        watchlist=watchlist,
        bot_configs=bot_configs,
        scan_interval=300,         # 5 minutes between full scans
        hot_list_interval=60,      # 1 minute between hot list scans
        active_trades_interval=10  # 10 seconds between active trades scans
    )

# Execute the main function if this script is run directly
if __name__ == "__main__":
    try:
        logger.info("Inside Value Intraday Scanner with Position Flip v1.0 - Starting")
        main()
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True)
        raise