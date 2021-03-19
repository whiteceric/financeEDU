import os
from datetime import datetime, timedelta
from pytz import timezone
from iexfinance.stocks import Stock, get_historical_data
# Set IEX Finance API Token (Test)
os.environ['IEX_API_VERSION'] = 'iexcloud-sandbox'
os.environ['IEX_TOKEN'] = 'Tpk_84a4b5d22681427a8b8557be6e1e4f49'

stock_data_cache = {}
stock_data_save_func = None

def get_date_str(date):
    """
    Returns the given date in YYYY/MM/DD format. date is the object returned by datetime.today()
    """
    return date.strftime('%Y/%m/%d')

def today():
    """
    For debugging, allows me to change what 'today' is.
    """
    return datetime.now(timezone('EST'))

def market_open():
    """
    Checks if the time is between 9:30am  and 4pm EST on a weekday.
    """
    time = today() # DEBUG: CHANGE BACK TO getting regular datetime.now()
    time = time.hour + time.minute/60
    return today().weekday() < 5 and time >= 9.5 and time  < 16

def check_stock_cache(tag, date):
    """
    Returns the price of a stock at the end of a given date if that information is stored in the
    cache, else returns none.
    """
    if date in stock_data_cache and tag in stock_data_cache[date]:
        return stock_data_cache[date][tag]

def get_prev_day_close(tag):
    """
    Returns the price of the stock tag at the close of the previous day.
    """
    yesterday = get_date_str(today() - timedelta(1)) 
    cached = check_stock_cache(tag, yesterday)
    if cached is not None:
        return cached
    try:
        close_price = Stock(tag).get_previous_day_prices()['close'].tolist()[0]
    except:
        close_price = 0
    stock_data_cache.setdefault(yesterday, {})
    stock_data_cache[yesterday][tag] = close_price
    if stock_data_save_func:
        stock_data_save_func(stock_data_cache)
    return close_price

def get_current_price(tag):
    """
    Returns the current price of a stock
    """
    try:
        return Stock(tag).get_price()[tag].tolist()[0]
    except:
        return 0

def get_price_on_date(tag, date):
    """
    Returns the price of a stock on a given date.
    'date' should be a string in the form: YYYY/MM/DD

    Note: this is separate from the get_prev_day_close() function 
    because 'historical' data API calls (i.e. calls with a date given)
    are much more expensive than getting the previous day close.
    """
    cached = check_stock_cache(tag, date)
    if cached is not None:
        return cached
    date_obj = datetime(*[int(tok) for tok in date.split('/')])
    try:
        close_price = get_historical_data(tag, date_obj, date_obj, close_only=True).values.tolist()[0][0]
    except:
        close_price = 0 # change this later

    stock_data_cache.setdefault(date, {})
    stock_data_cache[date][tag] = close_price
    if stock_data_save_func:
        stock_data_save_func(stock_data_cache)
    return close_price


def get_prev_week_endpoints(tag):
    """
    Returns a list of tuples representing the past 7 closing prices for a stock
    The format for the list is:
    [(-7, 80.54), (-6, 81.2), ... (-1, 85.32)]
    """
    ref_date = today()
    # get 7 previous open days
    dates = []
    dt = -1
    while len(dates) < 7:
        prev = ref_date + timedelta(dt)
        if prev.weekday() < 5:
            dates.append(get_date_str(prev))
        dt -= 1
    return [(_dt, get_price_on_date(tag, date)) for _dt, date in zip(range(-7, 0), dates[::-1])]

# for testing 
import json

def load_stock_data():
    """
    Gets "stocks.json" as a python dictionary from user data directory
    """
    with open('stocks.json', 'r') as data:
        data = json.load(data)
    global stock_data_cache
    stock_data_cache = data

def save_stock_data():
    """
    Saves a python dictionary to "data.json" as the user data. Note that "data.json" is overwritten when saved.
    """
    with open('stocks.json', 'w') as data_file:
        json.dump(stock_data_cache, data_file)

if __name__ == '__main__':
    #load_stock_data()
    #print(get_prev_day_close('DIS'))
    #save_stock_data()
    #print(get_price_on_date('DIS', '2021/03/01'))
    #print(get_prev_week_endpoints('PINS'))
    print(get_current_price('NASDAQ'))
    print(get_current_price('Dow Jones'))