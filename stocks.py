import stock_scrape

class Portfolio():
    @staticmethod
    def load_portfolio(data):
        """
        Creates a portfolio object from a python dictionary in the form returned by get_save_dict
        """
        portfolio = Portfolio(data['NAME'], data['CASH'], data['INITIAL_VALUE'], data.get('CURRENT_VALUE', None))
        for position_dict in data['POSITIONS']:
            portfolio.add_position(Position.load_position(position_dict))
        return portfolio

    def __init__(self, name, cash, initial_value=None, current_value=None):
        self.name = name
        self.positions = []
        self.cash = cash
        if initial_value is None:
            self.initial_value = cash
        else:
            self.initial_value = initial_value

        if current_value is None:
            self.update_value()
        else:
            self.current_value = current_value

        self.update_value()
        

    def __getitem__(self, tag):
        for position in self.positions:
            if position.tag == tag:
                return position
        return None

    def add_position(self, *new_positions):
        """
        Adds a position to this portfolio, combining positions that already exists to prevent duplicates.
        """
        for new_position in new_positions:
            found = False
            for position in self.positions:
                found = position.add_position(new_position)
                if found:
                    break

            if not found:
                self.positions.append(new_position)

    def buy_shares(self, tag, quantity):
        """
        Purchase a certain amount of shares, subtracting the value of the new position from cash
        """
        position = Position(tag)
        position.add_share(num_shares=quantity)
        self.cash -= quantity * position.current_price
        self.add_position(position)

    def sell_shares(self, tag, quantity):
        """
        Sell a certain amount of shares, adding the value of the new position to cash
        """
        position = [pos for pos in self.positions if pos.tag == tag][0]
        position.update_price()
        shares = [position.remove_share() for _ in range(quantity)]
        self.cash += position.current_price * quantity
        if position.num_shares == 0:
            self.positions.remove(position)

    def update_value(self):
        """
        Updates the total value of this portfolio by checking current prices
        """
        self.current_value = sum(position.get_value() for position in self.positions) + self.cash
        self.total_gain_loss = self.current_value - self.initial_value

    def get_save_dict(self):
        """
        Returns a python dictionary representing this portfolio.

        Ex: A portfolio called Portfolio 1 that started with $1000 and has $500 cash and 3 Disney shares bought on March 5, 2021 for $190 each and 1 Apple share 
        bought on February 28, 2021 for $85 would return:
        {"NAME": "Portfolio 1", 
        "POSITIONS": [
            {"TAG": "DIS", "NUM_SHARES": 3, "TOTAL_COST_BASIS": 570, "SHARES": [{"COST_BASIS": 190, "BUY_DATE": "2021/03/05"},
                                                                      {"COST_BASIS": 190, "BUY_DATE": "2021/03/05"},
                                                                      {"COST_BASIS": 190, "BUY_DATE": "2021/03/05"}]},
            {"TAG": "AAPL", "NUM_SHARES": 1, "TOTAL_COST_BASIS": 85, "SHARES": [{"COST_BASIS": 85, "BUY_DATE": "2021/02/28"}]}
            ],
        "CASH": 500,
        "CURRENT_VALUE": 1155
        "INITIAL_VALUE": 1000
        }
        """
        return {"NAME": self.name, 
                "POSITIONS": [position.get_save_dict() for position in self.positions],
                "CASH": self.cash,
                "CURRENT_VALUE": self.current_value,
                "INITIAL_VALUE": self.initial_value,
                "CURRENT_VALUE": self.current_value}

class Position():
    @staticmethod
    def load_position(data):
        """
        Creates a position object from a python dictionary in the form returned by get_save_dict
        """
        position = Position(data['TAG'])
        for share_dict in data['SHARES']:
            position.add_share(share_dict['COST_BASIS'], share_dict['BUY_DATE'])
        return position

    def __init__(self, tag):
        self.tag = tag
        self.shares = []
        self.total_cost_basis = 0

    def add_share(self, cost=None, date=None, num_shares=1):
        """
        Adds a share to this position
        """
        if cost is None:
            self.update_price()
            cost = self.current_price
        if date is None:
            date = stock_scrape.get_date_str(stock_scrape.today())
        for _ in range(num_shares):
            self.shares.append(Share(self.tag + ":" + str(len(self.shares) + 1), cost, date))
            self.total_cost_basis += cost

    def add_position(self, position):
        """
        Combines this position with another one if it has the same tag as this one.
        """
        if self.tag == position.tag:
            self.shares.extend(position.shares)
            return True
        return False

    def remove_share(self):
        """
        Removes the oldest share from this position and returns it.
        """
        return self.shares.pop(0)

    def get_value(self):
        """
        Updates the current price and returns the total value of this position
        """
        self.update_price
        return self.current_price * self.num_shares

    def update_price(self):
        """
        Updates the current price, and day change for this stock
        """
        self.current_price, self.day_change = stock_scrape.get_current_price(self.tag, get_day_change=True) 

    @property
    def num_shares(self):
        return len(self.shares)

    def get_prev_week_data(self):
        """
        Returns the closing prices from the previous week for this Stock
        """
        return stock_scrape.get_prev_week_endpoints(self.tag)

    def get_save_dict(self):
        """
        Returns a python dictionary representing this position.

        Ex: 3 Disney shares bought on March 5, 2021 for $190 each would return:
        {"TAG": "DIS", "NUM_SHARES": 3, "TOTAL_COST_BASIS": 570, "SHARES": [{"COST_BASIS": 190, "BUY_DATE": "2021/03/05"},
                                                                      {"COST_BASIS": 190, "BUY_DATE": "2021/03/05"},
                                                                      {"COST_BASIS": 190, "BUY_DATE": "2021/03/05"}]}
        """
        return {"TAG": self.tag,
                "SHARES": len(self.shares), 
                "TOTAL_COST_BASIS": self.total_cost_basis,
                "SHARES": [share.get_save_dict() for share in self.shares],
                }

class Share():
    """
    represents exactly one share of one company/index
    """
    def __init__(self, id, cost_basis, buy_date):
        self.id = id
        self.cost_basis = cost_basis
        self.buy_date = buy_date

    def get_save_dict(self):
        """
        Returns a python dictionary representing this share.

        Ex: a Disney share bought on March 5, 2021 for $190 would return:
        {"COST_BASIS": 190, "BUY_DATE": "2021/03/05"}
        """
        return {"COST_BASIS": self.cost_basis, "BUY_DATE": self.buy_date}
