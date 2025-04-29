import time
from datetime import datetime, timedelta
from Dhan_Tradehull import Tradehull

def is_market_open():
    now = datetime.now()
    if now.weekday() > 4:
        return False
    
    market_open = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 09:15:00", "%Y-%m-%d %H:%M:%S")
    market_close = datetime.strptime(f"{now.strftime('%Y-%m-%d')} 15:30:00", "%Y-%m-%d %H:%M:%S")
    
    return market_open <= now <= market_close

def get_ltp(tsl, symbol):
    try:
        ltp_data = tsl.get_ltp_data(names=[symbol])
        price = ltp_data.get(symbol, 0)
        return price if price and price > 0 else None
    except Exception:
        return None

def get_min_quantity(tsl, symbol, exchange):
    try:
        return 1 if exchange == "NSE" else max(1, tsl.get_lot_size(symbol) or 1)
    except Exception:
        return 1

def place_single_order_with_sl_target(tsl, symbol, exchange, quantity, transaction_type):
    try:
        current_price = get_ltp(tsl, symbol)
        if not current_price:
            return None

        primary_order_id = tsl.order_placement(
            tradingsymbol=symbol,
            exchange=exchange,
            quantity=quantity,
            price=0,
            trigger_price=0,
            order_type='MARKET',
            transaction_type=transaction_type,
            trade_type='MIS'
        )

        if not primary_order_id:
            return None

        time.sleep(1)  # Wait for order execution
        order_status = tsl.get_order_status(primary_order_id)
        
        if order_status not in ["TRADED", "Completed", "COMPLETE", "Complete"]:
            return None

        try:
            exec_price = tsl.get_executed_price(primary_order_id)
        except:
            exec_price = current_price

        exit_type = "SELL" if transaction_type == "BUY" else "BUY"
        
        def round_to_tick_size(price, tick_size=0.10):
            return round(price / tick_size) * tick_size

        if transaction_type == "BUY":
            sl_price = round_to_tick_size(exec_price * 0.99)
            target_price = round_to_tick_size(exec_price * 1.01)
        else:
            sl_price = round_to_tick_size(exec_price * 1.01)
            target_price = round_to_tick_size(exec_price * 0.99)

        sl_order_id = tsl.order_placement(
            tradingsymbol=symbol,
            exchange=exchange,
            quantity=quantity,
            price=0,
            trigger_price=sl_price,
            order_type='STOPMARKET',
            transaction_type=exit_type,
            trade_type='MIS'
        )

        target_order_id = tsl.order_placement(
            tradingsymbol=symbol,
            exchange=exchange,
            quantity=quantity,
            price=target_price,
            trigger_price=0,
            order_type='LIMIT',
            transaction_type=exit_type,
            trade_type='MIS'
        )

        return {
            "primary_order_id": primary_order_id,
            "sl_order_id": sl_order_id,
            "target_order_id": target_order_id,
            "execution_price": exec_price,
            "sl_price": sl_price,
            "target_price": target_price
        }
    except Exception:
        return None

def check_inside_value_conditions(yesterday, today_running):
    try:
        prev_h, prev_l, prev_c = yesterday['high'], yesterday['low'], yesterday['close']
        curr_h, curr_l, curr_c = today_running['high'], today_running['low'], today_running['close']

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

        return condition1 and condition2 and condition3 and condition4
    except Exception:
        return False

def get_current_day_candle(tsl, symbol, exchange):
    try:
        intraday_data = tsl.get_historical_data(tradingsymbol=symbol, exchange=exchange, timeframe="15")
        
        if intraday_data is None or len(intraday_data) == 0:
            return None
        
        today = datetime.now().date()
        date_columns = ['date', 'datetime', 'timestamp', 'time', 'candle_time']
        found_date_column = None
        
        for col in date_columns:
            if col in intraday_data.columns:
                found_date_column = col
                break
        
        if found_date_column:
            date_index = intraday_data[found_date_column].dt.date
            today_candles = intraday_data[date_index == today]
        else:
            today_candles = intraday_data.iloc[-30:]  # Use last 30 candles
        
        if len(today_candles) == 0:
            return None
        
        return {
            'open': today_candles.iloc[0]['open'],
            'high': today_candles['high'].max(),
            'low': today_candles['low'].min(),
            'close': today_candles.iloc[-1]['close']
        }
    except Exception:
        return None

def main():
    client_code = "1106534888"
    token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ3NjQ2MDMzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjUzNDg4OCJ9.TrT8U_uS3TEqqF23VGBgc1_SHk9f3S0e6yp_tbRdZ97A_93bZuYNcUul9JvGxme4_8bd3rvgyUnuzdNa9Y8QYA"
    
    watchlist = [
        'SBIN', 'INFY', 'RELIANCE', 'TCS', 'HDFC', 
        'ICICIBANK', 'AXIS', 'MARUTI', 'BAJFINANCE'
    ]
    
    try:
        tsl = Tradehull(client_code, token_id)
        
        while is_market_open():
            for symbol in watchlist:
                try:
                    exchange = "NSE"
                    
                    daily_data = tsl.get_historical_data(tradingsymbol=symbol, exchange=exchange, timeframe="DAY")
                    
                    if daily_data is None or len(daily_data) < 1:
                        continue
                    
                    yesterday = daily_data.iloc[-1]
                    today_running = get_current_day_candle(tsl, symbol, exchange)
                    
                    if today_running is None:
                        continue
                    
                    if check_inside_value_conditions(yesterday, today_running):
                        current_price = get_ltp(tsl, symbol)
                        
                        if not current_price:
                            continue
                        
                        yesterday_median = (yesterday['high'] + yesterday['low'] + yesterday['close']) / 3
                        threshold = yesterday_median * 1.01
                        
                        if current_price >= threshold:
                            quantity = get_min_quantity(tsl, symbol, exchange)
                            
                            order_result = place_single_order_with_sl_target(
                                tsl, symbol, exchange, quantity, "BUY"
                            )
                        
                        elif current_price <= (yesterday_median * 0.99):
                            quantity = get_min_quantity(tsl, symbol, exchange)
                            
                            order_result = place_single_order_with_sl_target(
                                tsl, symbol, exchange, quantity, "SELL"
                            )
                
                except Exception:
                    pass
                
                time.sleep(1)
            
            time.sleep(60)  # Wait for a minute before next scan
    
    except Exception:
        pass

if __name__ == "__main__":
    main()