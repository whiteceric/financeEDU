import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition, SlideTransition, CardTransition
from kivy.clock import Clock
from kivy_garden.graph import Graph, MeshLinePlot, LinePlot
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown

import json
from os.path import join

import stock_scrape
import layout_maker as lm
from layout_maker import CustomButton, CustomLayout, CustomLayoutItem
from stocks import Portfolio, Position, Share
from pygtrie import CharTrie

# Set the app size
Window.size = (414, 896)
lm.SCREEN_SIZE = Window.size

user_data = None
stock_data = None
symbol_data = None
tag_trie = None
save_portfolio = None

MAX_PORTFOLIOS = 5

# state
prev_screens = []
prev_screen_transitions = []
current_stock_symbol = None
current_portfolio_index = 0
current_portfolio = None
portfolio_changed = True
current_trade = None
trade_mode = 'BUY'

# some design constants
button_size = Window.size[0] * .22

# helpers
def color_from_hex(hex, alpha=1):
    return tuple(int(hex[i:i+2], 16)/255 for i in range(1, 7, 2)) + (alpha,)

SLIDE_RIGHT = SlideTransition(direction='right')
SLIDE_LEFT = SlideTransition(direction='left')
SLIDE_UP = SlideTransition(direction='up')
SLIDE_DOWN = SlideTransition(direction='down')
reverse_transitions = {SLIDE_LEFT: SLIDE_RIGHT, SLIDE_RIGHT: SLIDE_LEFT, SLIDE_DOWN: SLIDE_UP, SLIDE_UP: SLIDE_DOWN}

def screen_transition(screen_manager, old_screen, new_screen, transition):
    screen_manager.transition = transition
    if old_screen:
        prev_screens.append(old_screen)
        prev_screen_transitions.append(reverse_transitions.get(transition, NoTransition()))
    screen_manager.current = new_screen

def back(screen_manager):
    """
    Return to the previous screen
    """
    screen_transition(screen_manager, None, prev_screens.pop(), prev_screen_transitions.pop())

def load_portfolio(index):
    """
    Loads a different portfolio given its index in the user_data json file
    """
    global current_portfolio_index
    global current_portfolio
    global portfolio_changed
    current_portfolio_index = index
    current_portfolio = Portfolio.load_portfolio(user_data['PORTFOLIOS'][index])
    portfolio_changed = True
    return current_portfolio

# Color Pallete
DARK_GREEN = color_from_hex('#016933')
LIGHT_GREEN = color_from_hex('#00d632')
TRANSPARENT = (0,0,0,0)
WHITE = (1,1,1,1)
RED = (1,0,0,1)

# define some screens
# courtesy of John Anderson via StackOverflow
class DummyScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.switch_screen)

    def switch_screen(self, dt):
        self.manager.transition = NoTransition()  
        self.manager.current = 'home' 
        self.manager.transition = SlideTransition(direction='left')

class HomeScreen(Screen):

    def __init__(self, **kwargs):
        super(HomeScreen, self).__init__(**kwargs)
        self.reload()

    def on_pre_enter(self):
        if user_data is None:
            return
        if portfolio_changed:
            self.display_portfolio()

    def reload(self):
        """
        Reset the home screen with a new CustomLayout
        """
        self.layout = CustomLayout(scrollable=False)

        # menu button
        menu_img = lm.createImage(source='images/menu.png', rel_size=lm.rel_square(rel_width=.1))
        self.layout.add_item(CustomButton(menu_img, on_release_func=self.show_menu, alignment='left'))

        self.personal_value = lm.createLabel(text= "$-,---.--", font_size= 50, rel_size=(1, .1))
        self.personal_value_change = lm.createLabel(text= "+0.00%", font_size= 25, rel_size=(1, .05))
        self.cash_value = lm.createLabel(text= "$---.--", font_size= 50, rel_size=(1, .1))
        
        self.layout.add_item(self.personal_value)
        self.layout.add_item(self.personal_value_change)

        self.layout.add_item(lm.createLabel(text='Personal Value', font_size=20, 
                                        rel_size=(1, .05), color= DARK_GREEN))
        self.layout.add_item(self.cash_value)
        self.layout.add_item(lm.createLabel(text='Cash', font_size=20, 
                                        rel_size=(1, .05), color= DARK_GREEN))
        self.rendered_layout = self.layout.create(size_hint=(1,.3), pos_hint={"top": 1})
        self.add_widget(self.rendered_layout)
        self.share_section = None

    def display_portfolio(self):
        # Create a button for each position:
        share_section = CustomLayout()
        row = []
        for position in current_portfolio.positions:
            if row and len(row) % 3 == 0:
                share_section.add_widget_row((.33, .25), *row, alignment='left')
                row = []  
            # get position info          
            position.update_price()
            tag = position.tag
            num_shares = position.num_shares
            day_change = position.day_change
            current_price = position.current_price

            #get the right arrow image based on day change
            icon = 'images/up_arrow.png' if day_change >= 0 else 'images/down_arrow.png'

            # each position will have a CustomButton
            col = self.create_share_button(icon, tag, f'${current_price:,.2f}', f'(${day_change:+,.2f})')
            row.append(col)

        if row and len(row) % 3 == 0:
            share_section.add_widget_row((.33, .25), *row, alignment='left')
            row = []  

        col = self.create_share_button('images/plus.png', 'Buy', 'Stocks', '')     
        row.append(col)
        share_section.add_widget_row((.33, .25), *row, alignment='left')

        # add the share section to the page
        if self.share_section:
            self.remove_widget(self.share_section)
        self.share_section = share_section.create(size_hint=(1,.60), pos_hint={"top": .60})
        self.add_widget(self.share_section)
        # update personal value label
        current_portfolio.update_value()
        self.personal_value.widget.text = f'${current_portfolio.current_value:,.2f}'
        self.personal_value_change.widget.text = f'{"+" if current_portfolio.total_gain_loss >= 0 else "-"}${abs(current_portfolio.total_gain_loss):,.2f}' 
        if current_portfolio.total_gain_loss < 0:
            self.personal_value_change.widget.color = RED
        else:
            self.personal_value_change.widget.color = WHITE

        self.cash_value.widget.text = f'${current_portfolio.cash:,.2f}'
        portfolio_changed = False

    def create_share_button(self, icon, symbol, *labels):
        col = []
        font_size = 20
        col.append(lm.createLabel(text=symbol, font_size=font_size, rel_size=(.1,.02)))
        col.append(lm.createImage(icon, rel_size=lm.rel_square(rel_width=.3)))        
        for label in labels:
            col.append(lm.createLabel(text=label, font_size=font_size, rel_size=(.1, .02)))
            font_size *= .5
        out = CustomButton(*col, spacing=0, padding=0)
        out.bind_on_release(lambda: self.share_pressed(symbol))
        return out

    def share_pressed(self, symbol):
        global current_stock_symbol
        if symbol == 'Buy':
            global trade_mode
            trade_mode = 'BUY'
            to = 'trade'
            current_stock_symbol = None
        else:
            to = 'detail'
            current_stock_symbol = symbol
        
        screen_transition(self.manager, 'home', to, SLIDE_LEFT)

    def show_menu(self):
        """
        Transition to the menu screen
        """
        screen_transition(self.manager, 'home', 'menu', SLIDE_DOWN)

class StockDetailScreen(Screen):
    def __init__(self, **kwargs):
        super(StockDetailScreen, self).__init__(**kwargs)

        self.layout = CustomLayout()
        back_img = lm.createImage(source='images/back.png', rel_size=lm.rel_square(rel_width=.1))
        self.layout.add_item(CustomButton(back_img, on_release_func=lambda: back(self.manager), alignment='left'))

        self.stock_name = lm.createLabel(bold= False, rel_size= (1, .1), text_rel_size = (.95, .1), halign='center', valign='middle')
        self.layout.add_item(self.stock_name)

        self.layout.add_widget(Button(text="TRADE", bold=True, font_size=40,
                                        background_color=DARK_GREEN, on_release=self.trade),                                        
                                        rel_size=(.8, .1))

        self.current_price = lm.createLabel(font_size= 50, rel_size= (1, .1))

        self.layout.add_item(self.current_price)
        self.center_image = lm.createImage(source='images/up_arrow.png', rel_size=lm.rel_square(rel_width=.5))
        self.layout.add_item(self.center_image)

        self.stock_symbol = lm.createLabel(font_size= 50, rel_size= (1, .1))
        self.layout.add_item(self.stock_symbol)

        self.num_shares = lm.createLabel(font_size= 28, rel_size= (1, .1))
        self.layout.add_item(self.num_shares)

        self.layout.add_item(lm.createLabel(text = 'Past Week Performace', font_size= 28, rel_size= (1, .1)))

        # graph
        self.graph = Graph(x_ticks_major=1, tick_color = (0,0,0,.5), xlabel='Days',
              y_grid_label=True, x_grid_label=True, precision='%.2f', padding=5,
              x_grid=True, y_grid=True, xmin=-5, xmax=-1, ymin=0, ymax=100,
              border_color = (0,0,0,0), label_options = {'color': (0,0,0,1)})        

        self.plot = [(i-7, .3*i*100) for i in range(7)]

        self.layout.add_widget(self.graph, rel_size=(.90, .3))

        self.add_widget(self.layout.create())

    def on_pre_enter(self):
        position = Position(current_stock_symbol)
        position.update_price()
        self.stock_name.widget.text = symbol_data[position.tag]['NAME']
        self.current_price.widget.text = f'${position.current_price:,.2f}'
        self.stock_symbol.widget.text = position.tag
        self.center_image.widget.source = 'images/up_arrow.png' if position.day_change >= 0 else 'images/down_arrow.png'
        share_count = current_portfolio[position.tag].num_shares if current_portfolio[position.tag] else 0
        self.num_shares.widget.text = f'You own {share_count} share{"s" if share_count != 1 else ""}'
        self.plot_data(position.get_prev_week_data())

    def plot_data(self, data):
        """
        Change the data shown on the stock graph.
        data should be a list of tuples showing (x,y) pairs on the graph.
        """
        self.graph.ymax = max(price for _,price in data) * 1.01
        self.graph.ymin = min(price for _,price in data) * .99
        self.graph.y_ticks_major = (self.graph.ymax - self.graph.ymin) / 4
        self.graph.remove_plot(self.plot)
        self.plot = LinePlot(color=WHITE, line_width=3)
        self.plot.points = data
        self.graph.add_plot(self.plot)

    def trade(self, trade_button):
        """
        Enter the trade screen
        """
        global trade_mode
        trade_mode = 'BUY'
        screen_transition(self.manager, 'detail', 'trade', SLIDE_LEFT)

class SymbolSearch(TextInput):
    def __init__(self, trade_screen=None, **kwargs):
        super(SymbolSearch, self).__init__(**kwargs)
        self.font_size = 40
        self.multiline = False
        self.dropdown = DropDown()
        self.dropdown_items = []
        self.dropdown.max_height = Window.size[1] * .2
        self.dropdown.background_color = (1,1,1,1)
        self.trade_screen = trade_screen

    def update_dropdown_items(self):
        """
        Create the buttons for the dropdown menu
        """        
        try:
            self.dropdown.clear_widgets()
            if self.text != '':
                self.dropdown_items = tag_trie.items(prefix=self.text)
            else:
                raise ValueError()
        except:
            self.dropdown_items = []
        if len(self.dropdown_items) > 50:
            self.dropdown_items = self.dropdown_items[:50]
        for tag,_ in self.dropdown_items:
            button = Button(text=tag, bold=True, size_hint_y=None, height=Window.size[1] * .04,
                            background_color=DARK_GREEN, on_press=lambda btn: self.dropdown_selected(btn))
            self.dropdown.add_widget(button)

    def on_focus(self, text_input, focused):
        """
        Engage the drop down menu to search for a position
        """
        prior = self.text
        if prior == 'Search':
            self.text = ''
        if focused:
            self.update_dropdown_items()
            self.dropdown.open(self)
        else:
            if self.text == '':
                self.trade_screen.display_no_symbol()
            else:
                self.trade_screen.display_symbol(self.text)
        self.trade_screen.more_info_button.disabled = self.text == ''


    def on_text(self, text_input, text):
        """
        Update the dropdown list to reflect the new search text
        """
        self.update_dropdown_items()
        try:
            self.dropdown.open()
        except:
            pass
    
    def insert_text(self, substring, from_undo=False):
        new_text = substring.upper()
        return super(SymbolSearch, self).insert_text(new_text, from_undo=from_undo)
    
    def dropdown_selected(self, button):
        """
        Make the selection from the dropdown menu
        """
        if self.trade_screen:
            self.text = button.text
            self.trade_screen.display_symbol(button.text)
            self.trade_screen.update_estimated_value()
            self.trade_screen.check_confirm_button()
        self.text = button.text
        self.dropdown.select(button)        

class ShareQuantityInput(TextInput):
    def __init__(self, trade_screen=None, **kwargs):
        super(ShareQuantityInput, self).__init__(**kwargs)
        self.font_size = 40
        self.trade_screen = trade_screen

    def on_focus(self, text_input, focused):
        """
        Update the estimates value based on the number of shares
        """
        if not focused:
            self.trade_screen.update_estimated_value()
            self.trade_screen.check_confirm_button()

    def insert_text(self, substring, from_undo=False):
        """
        Make the sure the text is an integer and truncate the text to 3 digits.
        """
        try:
            num = int(substring)
            if len(self.text) >= 3:
                substring = ''
        except:
            substring = ''
        return super(ShareQuantityInput, self).insert_text(substring, from_undo=from_undo)

class TradeScreen(Screen):
    def __init__(self, **kwargs):
        super(TradeScreen, self).__init__(**kwargs)
        self.current_symbol = current_stock_symbol
        self.layout = CustomLayout()

        back_img = lm.createImage(source='images/back.png', rel_size=lm.rel_square(rel_width=.1))
        self.layout.add_item(CustomButton(back_img, on_release_func=lambda: back(self.manager), alignment='left'))

        self.cash_value = lm.createLabel(text= "$---.--", font_size= 50, rel_size=(1, .06))
        self.layout.add_item(self.cash_value)
        self.layout.add_item(lm.createLabel(text='Cash', font_size=20, 
                                        rel_size=(1, .05), color= DARK_GREEN))

        self.buy_button = Button(text="BUY", bold=True, font_size=40, background_normal='',
                                        background_color=DARK_GREEN, on_release=self.buy_sell_button)
        self.sell_button = Button(text="SELL", bold=True, font_size=40, background_normal='',
                                        background_color=DARK_GREEN, on_release=self.buy_sell_button)

        self.layout.add_widget_row((.4, .1), self.buy_button, self.sell_button)
        self.symbol_search = SymbolSearch(text='Search', trade_screen=self) 
        self.layout.add_item(lm.createSpace((1,.05)))
        self.layout.add_widget(self.symbol_search, rel_size=(.8, .06))

        self.current_price_label = lm.createLabel(font_size= 50, rel_size= (1, .1))
        self.current_price = 0
        self.layout.add_item(self.current_price_label)

        self.more_info_button = Button(text="More Info", bold=True, font_size=12, background_normal='',
                                        background_color=DARK_GREEN, on_release=self.more_info, disabled=True)
        self.layout.add_widget(self.more_info_button, rel_size=(.2, .04))

        # You own ## Shares
        self.num_shares = 0
        self.num_shares_owned = lm.createLabel(rel_size= (1, .1))
        self.layout.add_item(self.num_shares_owned)
        self.num_of_shares_label = lm.createLabel(text_rel_size=(.5, .1))
        self.num_share_selection = CustomLayoutItem(ShareQuantityInput(trade_screen=self), rel_size=(.225, .06))
        anchor = AnchorLayout(size_hint=(.5, .1), anchor_x='center')
        anchor.add_widget(self.num_share_selection.widget)
        anchor_item = CustomLayoutItem(anchor, rel_size=(.5, .07))
        self.layout.add_item_row((1, .1), self.num_of_shares_label, anchor_item, alignment='center')

        # Estimated Value: $##.##
        self.estimated_value_label = lm.createLabel(rel_size= (1, .1), font_size=20)
        self.layout.add_item(self.estimated_value_label)

        self.confirm_button = Button(text="Confirm", bold=True, font_size=40, background_normal='',
                                        background_color=DARK_GREEN, on_release=self.confirm_trade)
        self.layout.add_widget(self.confirm_button, rel_size=(.7, .1))

        self.add_widget(self.layout.create())

    def on_pre_enter(self):
        self.update_cash_value()
        self.update_estimated_value()
        self.update_trade_mode()        
        if current_stock_symbol:
            self.display_symbol(current_stock_symbol)
        else:
            self.display_no_symbol()
        self.check_confirm_button()

    def update_cash_value(self):
        """
        Display the cash value of this portfolio
        """
        self.cash_value.widget.text = f'${current_portfolio.cash:,.2f}'

    def display_no_symbol(self):
        """
        Show no symbol on the trade screen
        """
        self.current_symbol = None
        self.symbol_search.text = 'Search'
        self.current_price_label.widget.text = f'$0'
        self.current_price = 0
        self.more_info_button.disabled = True
        self.share_count = 0
        self.num_shares_owned.widget.text = f'You own {self.share_count} share{"s" if self.share_count != 1 else ""}'        
        self.num_share_selection.widget.text = '0'
        self.num_shares = 0

    def display_symbol(self, symbol):
        """
        Show a symbol on the trade screen
        """
        position = Position(symbol)
        position.update_price()
        if position.current_price <= 0:
            self.display_no_symbol()
            return
        self.current_symbol = symbol
        self.update_cash_value()
        self.symbol_search.text = self.current_symbol
        self.current_price_label.widget.text = f'${position.current_price:,.2f}'
        self.current_price = position.current_price
        self.more_info_button.disabled = False
        self.share_count = current_portfolio[position.tag].num_shares if current_portfolio[position.tag] else 0
        self.num_shares_owned.widget.text = f'You own {self.share_count} share{"s" if self.share_count != 1 else ""}'

    def buy_sell_button(self, button):
        """
        Change the trade mode based on which button was pressed
        """
        if button == self.buy_button:
            self.update_trade_mode('BUY')
        elif button == self.sell_button:
            self.update_trade_mode('SELL')
        self.check_confirm_button()

    def update_trade_mode(self, mode=None):
        """
        Updates the trade page to reflect a buy/sale 
        """
        global trade_mode
        if mode:        
            trade_mode = mode
        if trade_mode == 'BUY':
            self.buy_button.background_color = WHITE
            self.buy_button.color = DARK_GREEN
            self.sell_button.background_color = DARK_GREEN
            self.sell_button.color = WHITE            
        elif trade_mode == 'SELL':
            self.buy_button.background_color = DARK_GREEN
            self.buy_button.color = WHITE
            self.sell_button.background_color = WHITE
            self.sell_button.color = DARK_GREEN
        self.num_of_shares_label.widget.text = 'How many shares to buy:' if trade_mode =='BUY' else 'How many shares to sell:'
        

    def update_estimated_value(self):
        """
        Update the estimated value based on the number of shares being bought/sold
        """
        try:
            self.num_shares = int(self.num_share_selection.widget.text)
        except:
            self.num_shares = 0        
        self.estimated_value = self.num_shares*self.current_price
        self.estimated_value_label.widget.text = f'Estimated Value: ${self.estimated_value:,.2f}'
        
    def check_confirm_button(self):
        """
        disable the confirm button if the estimated value is higher than the current cash value or
        if the number of shares selected is higher than the number of shares owned.
        """
        self.confirm_button.disabled = self.current_symbol == None or self.num_shares <= 0 or (trade_mode == 'BUY' and self.estimated_value > current_portfolio.cash) or (trade_mode == 'SELL' and (self.share_count == 0 or self.num_shares > self.share_count))

    def more_info(self, button):
        """
        Transition to the detail page for the current stock
        """
        global current_stock_symbol
        current_stock_symbol = self.current_symbol        
        screen_transition(self.manager, 'trade', 'detail', SLIDE_LEFT)

    def confirm_trade(self, button):
        """
        Transition to the confirm trade screen
        """
        global current_trade
        current_trade = (trade_mode, self.current_symbol, self.num_shares)
        screen_transition(self.manager, 'trade', 'confirm_trade', SLIDE_LEFT)

class ConfirmTradeScreen(Screen):
    def __init__(self, **kwargs):
        super(ConfirmTradeScreen, self).__init__(**kwargs)
        self.layout = CustomLayout()

        back_img = lm.createImage(source='images/back.png', rel_size=lm.rel_square(rel_width=.1))
        self.layout.add_item(CustomButton(back_img, on_release_func=lambda: back(self.manager), alignment='left'))

        self.label = lm.createLabel(font_size = 20, rel_size=(.9, .3))
        self.layout.add_item(self.label)

        self.yes_button = Button(text="YES", bold=True, font_size=40, background_normal='',
                                    background_color=DARK_GREEN, on_release=self.trade_confirmed)
        self.no_button = Button(text="BACK", bold=True, font_size=40, background_normal='',
                                    background_color=DARK_GREEN, on_release=lambda btn: back(self.manager))

        self.layout.add_widget_row((.3, .08), self.yes_button, self.no_button)

        self.add_widget(self.layout.create())

    def on_pre_enter(self):
        self.label.widget.text = f'{current_trade[0]} {current_trade[2]} share{"s" if current_trade[2] != 1 else ""} of {current_trade[1]}?'

    def trade_confirmed(self, button):
        """
        Execute current_trade
        """
        op, tag, quantity = current_trade
        if op == 'BUY':
            current_portfolio.buy_shares(tag, quantity)
        elif op == 'SELL':
            current_portfolio.sell_shares(tag, quantity)
        save_portfolio()
        # go to the home screen when we make a trade
        screen_transition(self.manager, None, 'home', SLIDE_RIGHT)

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)

        self.layout = CustomLayout(scrollable=True)

        # back home button
        back_up_img = lm.createImage(source='images/back.png', rel_size=lm.rel_square(rel_width=.1))
        self.layout.add_item(CustomButton(back_up_img, on_release_func=lambda: back(self.manager), alignment='left'))

        self.layout.add_item(lm.createLabel(text='TryInvest', font_size=30, rel_size=(1, .2)))
        self.layout.add_item(lm.createLabel(text='Portfolios', font_size=30, color=DARK_GREEN, rel_size=(1, .08), alignment='left'))

        # Portfolio Buttons
        self.portfolio_buttons = []
        for i in range(MAX_PORTFOLIOS):
            self.portfolio_buttons.append(Button(text="Empty", bold=False, font_size=28, background_normal='',
                                    background_color=TRANSPARENT, on_release=self.portfolio_selected))
            self.layout.add_widget(self.portfolio_buttons[i], rel_size=(1, .05), alignment='left')

        # Add portfolio Button
        self.add_portfolio_button = Button(text="+ New Portfolio", bold=False, font_size=28, background_normal='',
                background_color=TRANSPARENT, on_release=self.new_portfolio)

        self.layout.add_widget(self.add_portfolio_button, rel_size=(1, .1))

        self.layout.add_item(lm.createSpace(rel_size=(1, .1)))
        # Delete portfolio Button
        self.delete_portfolio_button = Button(text="Delete Portfolio", bold=False, font_size=28, color=RED, background_normal='',
                background_color=TRANSPARENT, on_release=self.delete_portfolio)
        self.layout.add_widget(self.delete_portfolio_button, rel_size=(1, .1))
        self.layout.add_item(lm.createLabel(text='About', font_size=30, rel_size=(1, .08)))
        self.add_widget(self.layout.create())
        
    def on_pre_enter(self):
        portfolios = user_data['PORTFOLIOS']
        for i in range(MAX_PORTFOLIOS):
            self.portfolio_buttons[i].text = portfolios[i]['NAME'] if i < len(portfolios) else 'Empty'
            self.portfolio_buttons[i].disabled = i >= len(portfolios)
            if i == current_portfolio_index:
                self.portfolio_buttons[i].background_color = DARK_GREEN
            else:
                self.portfolio_buttons[i].background_color = TRANSPARENT
        self.add_portfolio_button.disabled = len(portfolios) >= MAX_PORTFOLIOS

    def portfolio_selected(self, button):
        """
        Save the current portfolio then load the selected one then return to the home screen
        """
        save_portfolio()
        load_portfolio(self.portfolio_buttons.index(button))
        back(self.manager)

    def new_portfolio(self, button):
        """
        Transition to create portfolio screen
        """
        screen_transition(self.manager, 'menu', 'new_portfolio', SLIDE_UP)

    def delete_portfolio(self, button):
        """
        Transition to the confirm delete screen
        """
        screen_transition(self.manager, 'menu', 'confirm_delete', SLIDE_LEFT)
        
class ConfirmDeleteScreen(Screen):
    def __init__(self, **kwargs):
        super(ConfirmDeleteScreen, self).__init__(**kwargs)

        self.layout = CustomLayout()

        back_img = lm.createImage(source='images/back.png', rel_size=lm.rel_square(rel_width=.1))
        self.layout.add_item(CustomButton(back_img, on_release_func=lambda: back(self.manager), alignment='left'))

        self.label = lm.createLabel(font_size = 20, rel_size=(.9, .3))
        self.layout.add_item(self.label)

        self.delete_button = Button(text="DELETE", bold=True, font_size=40, background_normal='',
                                    background_color=RED, on_release=self.delete)
        self.no_button = Button(text="BACK", bold=True, font_size=40, background_normal='',
                                    background_color=DARK_GREEN, on_release=lambda btn: back(self.manager))

        self.layout.add_widget_row((.4, .08), self.delete_button, self.no_button)

        self.add_widget(self.layout.create())

    def on_pre_enter(self):
        self.label.widget.text = f'Delete \'{current_portfolio.name}\'?'

    def delete(self, button):
        """
        Delete the current portfolio and load another one
        """
        user_data['PORTFOLIOS'].pop(current_portfolio_index)
        load_portfolio(0)
        save_portfolio()
        back(self.manager)


class NewPortfolioScreen(Screen):
    def __init__(self, **kwargs):
        super(NewPortfolioScreen, self).__init__(**kwargs)

        self.layout = CustomLayout(scrollable=True)

        # back button
        back_img = lm.createImage(source='images/back.png', rel_size=lm.rel_square(rel_width=.1))
        self.layout.add_item(CustomButton(back_img, on_release_func=lambda: back(self.manager), alignment='left'))

        self.layout.add_item(lm.createLabel(text='Create Portfolio', font_size=35, rel_size=(1, .1)))

        self.layout.add_item(lm.createLabel(text='Name:', font_size=30, rel_size=(1, .05)))

        self.name_input = TextInput(text=f"New Portfolio", font_size=32)
        self.layout.add_widget(self.name_input, rel_size=(.8, .06))

        self.layout.add_item(lm.createLabel(text='Starting Cash:', font_size=30, rel_size=(1, .05)))

        self.starting_cash_input = TextInput(font_size=32)
        self.layout.add_widget(self.starting_cash_input, rel_size=(.8, .06))

        self.layout.add_item(lm.createSpace(rel_size=(1, .15)))
        self.create_button = Button(text="Create", bold=True, font_size=40, background_normal='',
                                        background_color=DARK_GREEN, on_release=self.create)
        self.layout.add_widget(self.create_button, rel_size=(.7, .1))

        self.add_widget(self.layout.create())

    def on_pre_enter(self):
        self.name_input.text = f'Portfolio {len(user_data["PORTFOLIOS"])+1}'
        self.starting_cash_input.text = "$1,000.00"

    def create(self, button):
        """
        Create the new portfolio
        """
        name = self.name_input.text
        starting_cash = float(self.starting_cash_input.text[1:].replace(',', ''))
        new_portfolio = Portfolio(name, starting_cash)
        user_data['PORTFOLIOS'].append(new_portfolio.get_save_dict())
        load_portfolio(len(user_data['PORTFOLIOS']) - 1)
        screen_transition(self.manager, None, 'home', SLIDE_UP)
        save_portfolio()

class WindowManager(ScreenManager):
    pass

kv = Builder.load_file('main.kv')
class TryInvestApp(App):
    def build(self):
        Window.clearcolor = color_from_hex('#00d632')
        return kv

    def on_start(self):
        global user_data
        global stock_data
        global symbol_data
        global tag_trie
        global save_portfolio
        user_data = self.load_storage_data('data.json')
        if user_data is None: # first time opening the app
            user_data = {'PORTFOLIOS': [Portfolio('My First Portfolio', 10000).get_save_dict()]}
            stock_data = {}
            symbol_json = open('symbols.json')
            symbol_data = json.load(symbol_json)
            symbol_json.close()
            self.save_storage_data(user_data, 'data.json')
            self.save_storage_data(stock_data, 'stocks.json')
            self.save_storage_data(symbol_data, 'symbols.json')
        else:
            stock_data = self.load_storage_data('stocks.json')
            symbol_data = self.load_storage_data('symbols.json')
        
        tag_trie = CharTrie()
        for tag in symbol_data:
            tag_trie[tag] = True
        stock_scrape.stock_data_cache = stock_data
        stock_scrape.stock_data_save_func = lambda data: self.save_storage_data(data, 'stocks.json')
        load_portfolio(0)
        def _save_portfolio_func():
            global portfolio_changed
            portfolio_changed = True
            user_data['PORTFOLIOS'][current_portfolio_index] = current_portfolio.get_save_dict()
            self.save_storage_data(user_data, 'data.json')
        save_portfolio = _save_portfolio_func

    def storage_file_path(self, filename):
        """
        Get the path where local data is to be stored
        """
        return join(self.user_data_dir, filename)

    def load_storage_data(self, filename, file_type='JSON'):
        """
        Gets a file from the App's storage directory
        """
        data = None
        try:
            with open(self.storage_file_path(filename), 'r') as data:
                if file_type == 'JSON': 
                    data = json.load(data)
        except: # fnf
            pass
        return data

    def save_storage_data(self, data, filename, file_type='JSON'):
        """
        Saves a file in the App's storage directory
        """
        with open(self.storage_file_path(filename), 'w') as save_file:
            if file_type == 'JSON':
                json.dump(data, save_file)


if __name__ == '__main__':
    TryInvestApp().run()
