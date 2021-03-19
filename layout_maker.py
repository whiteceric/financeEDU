import kivy
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Rectangle

SCREEN_SIZE = (0, 0)

class CustomLayout():
    """
    A wrapper class that uses multiple layouts to create a page in the app
    """
    def __init__(self, scrollable=True):
        self.items = []
        self.scrollable = scrollable

    def add_widget(self, widget, rel_size=None, alignment='center'):
        """
        Adds a widget to this layout in its own row.
        """
        self.items.append(CustomLayoutItem(widget, rel_size, alignment))

    def add_item(self, item):
        """
        Adds a CustomLayoutItem to this layout
        """
        self.items.append(item)

    def add_widget_row(self, rel_size, *widgets, alignment='center'):
        """
        Adds a row of widgets to this layout.
        Each widget will have the rel_size given
        """
        items = [CustomLayoutItem(widget, rel_size) for widget in widgets]
        self.add_item_row((1, rel_size[1]), *items, alignment=alignment)

    def add_item_row(self, rel_size, *items, alignment='center'):
        """
        Adds a row of CustomLayoutItem objects to this layout.
        """
        self.items.append(CustomLayoutRow(rel_size, alignment, *items))

    def create(self, size_hint=(1,1), pos_hint={"top": 1}):
        """
        Creates a layout using the items added to this instance so far.
        """
        total_height = sum(item.absolute_size[1] for item in self.items) * 1.01

        if self.scrollable:
            grid = GridLayout(cols = 1, size_hint=(1,None), height = total_height)
            top_view = ScrollView(size_hint=size_hint, pos_hint=pos_hint)
            top_view.add_widget(grid)
        else:
            grid = GridLayout(cols = 1, size_hint=size_hint, pos_hint=pos_hint)
            top_view = grid
        
        for item in self.items:
            grid.add_widget(item.create())
        
        return top_view

    

class CustomLayoutItem():
    def __init__(self, widget, rel_size=None, h_alignment='center'):
        """
        Represents a single item (a widget) in the layout. rel_width and rel_height
        determine the size relative to the screen size.
        """
        self.widget = widget
        self.rel_size = rel_size
        self.h_alignment = h_alignment
        if rel_size:
            widget.size_hint = (None, None)
            size = self.absolute_size
            widget.width = size[0]
            widget.height = size[1]

    def create(self, **kwargs):
        """ 
        Creates this item as a AnchorLayout containing the widget
        """
        new_args = {'size_hint': (1, None),
                    'height': SCREEN_SIZE[1] * self.rel_size[1] if self.rel_size else None,
                    'anchor_x': self.h_alignment}
        for var, val in new_args.items():
            if var not in kwargs and val is not None:
                kwargs[var] = val

        anchor = AnchorLayout(**kwargs)
        anchor.add_widget(self.widget)
        return anchor

    @property
    def absolute_size(self):
        if self.rel_size:
            return SCREEN_SIZE[0] * self.rel_size[0], SCREEN_SIZE[1] * self.rel_size[1]

class CustomLayoutRow(CustomLayoutItem):
    def __init__(self, rel_size, h_alignment='center', *items):
        self.items = items
        self.rel_size = rel_size
        self.h_alignment = h_alignment

    def create(self, **kwargs):
        """ 
        Creates this row as a BoxLayout containing the widgets
        """
        new_args = {'size_hint': (None, None),
                    'width': SCREEN_SIZE[0] * self.rel_size[0],
                    'height': SCREEN_SIZE[1] * self.rel_size[1],
                    'orientation': 'horizontal'}
        for var, val in new_args.items():
            if var not in kwargs:
                kwargs[var] = val

        box = BoxLayout(**kwargs)
        for item in self.items:
            if self.h_alignment == 'center':
                anchor = AnchorLayout(size_hint=(item.rel_size[0] / self.rel_size[0],1), anchor_x = self.h_alignment)
                anchor.add_widget(item.widget)
                box.add_widget(anchor)
            elif self.h_alignment == 'left':
                item.widget.pos_hint = {'top': 1}
                box.add_widget(item.widget)
        return box

class CustomButton(ButtonBehavior, BoxLayout):
    def __init__(self, *elements, on_release_func=None, orientation='vertical', alignment='center', background_color=(0,0,0,0), **kwargs):
        """
        Creates a button with a BoxLayout to hold elements vertically.
        'elements' should contain CustomLayoutItems
        """
        super(CustomButton, self).__init__(**kwargs)        
        self.items = elements
        self.on_press_func = None
        self.on_release_func = on_release_func
        self.orientation = orientation

        alignment_map = {'center': {'center_x': .5}, 'left': {'x': 0}}
        self.size_hint_y = None
        height = 0
        for item in self.items:
            item.widget.pos_hint = alignment_map[alignment]
            height += item.absolute_size[1]
            self.add_widget(item.widget)
        self.height = height

        with self.canvas:
            Color(*background_color)
            Rectangle(pos=self.pos, size=self.size)

    @property
    def absolute_size(self):
        return (max(item.absolute_size[0] for item in self.items), 
                sum(item.absolute_size[1] for item in self.items))

    def create(self):
        return self

    def on_press(self):
        if self.on_press_func:
            self.on_press_func()

    def on_release(self):
        if self.on_release_func:
            self.on_release_func()

    def bind_on_press(self, func):
        self.on_press_func = func

    def bind_on_release(self, func):
        self.on_release_func = func

def createLabel(text='---', color=(1,1,1,1), background_color=(0,0,0,0), bold=True, font_size=32, rel_size=(1,1), alignment='center', text_rel_size = None, halign='center', valign = 'middle', **kwargs):
    """
    Creates a CustomLayoutItem representing a label.
    """
    kwargs['text'] = text
    kwargs['color'] = color
    kwargs['bold'] = bold
    kwargs['font_size'] = font_size
    if text_rel_size is not None:
        kwargs['text_size'] = (text_rel_size[0] * SCREEN_SIZE[0], text_rel_size[1] * SCREEN_SIZE[1])
        kwargs['halign'] = halign
        kwargs['valign'] = valign
    label = Label(**kwargs)
    with label.canvas.after:
        Color(*background_color)
        Rectangle(pos=label.pos, size=label.size)
    return CustomLayoutItem(label, rel_size, alignment)

def createSpace(rel_size=(1,1)):
    """ 
    Creates a blank space via an empty label
    """
    return createLabel(text='', rel_size=rel_size)

def createImage(source = '', rel_size=None):
    """
    Creates a CustomLayoutItem representing an image
    """
    return CustomLayoutItem(Image(source=source), rel_size)

def rel_square(rel_width = None, rel_height = None):
    """
    Returns the length and width of a square in pixels according to
    the screen dimensions
    """
    if rel_width:
        return (rel_width, rel_width * SCREEN_SIZE[0] / SCREEN_SIZE[1])
    return (rel_height * SCREEN_SIZE[1] / SCREEN_SIZE[0], rel_height)