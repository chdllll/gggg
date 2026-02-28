import sys
import os
import json
import asyncio
from threading import Thread

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

def get_font_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'data', 'fonts', 'msyh.ttc')
    elif os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'fonts', 'msyh.ttc')):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'fonts', 'msyh.ttc')
    elif os.name == 'nt':
        return 'C:/Windows/Fonts/msyh.ttc'
    else:
        return 'DroidSansFallback'

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.spinner import Spinner
from kivy.uix.dropdown import DropDown
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.widget import Widget

from database.db_manager import DatabaseManager
from api.deepseek_client import DeepSeekClient
from core.dialogue_manager import DialogueManager
from core.background_selector import BackgroundSelector

WINDOW_WIDTH = 400
WINDOW_HEIGHT = 880

Window.size = (WINDOW_WIDTH, WINDOW_HEIGHT)
Window.clearcolor = (1, 1, 1, 1)

FONT_NAME = get_font_path()

COLORS = {
    'primary': (0.2, 0.4, 0.8, 1),
    'primary_light': (0.4, 0.6, 0.9, 1),
    'background': (0.95, 0.95, 0.97, 1),
    'surface': (1, 1, 1, 1),
    'surface_light': (0.98, 0.98, 0.98, 1),
    'text': (0.1, 0.1, 0.1, 1),
    'text_secondary': (0.4, 0.4, 0.4, 1),
    'text_hint': (0.6, 0.6, 0.6, 1),
    'divider': (0.9, 0.9, 0.9, 1),
    'accent': (0.8, 0.2, 0.2, 1),
    'call_orange': (1.0, 0.6, 0.0, 1),
    'call_alert': (1.0, 0.2, 0.2, 1),
}


class SpinnerDropdown(DropDown):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_width = False


class ChineseSpinner(Spinner):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = FONT_NAME
    
    def _update_dropdown(self, *largs):
        if self._dropdown:
            self._dropdown.clear_widgets()
            self._dropdown.auto_width = False
            self._dropdown.width = Window.width - dp(32)
            for value in self.values:
                item = Button(
                    text=value,
                    font_name=FONT_NAME,
                    font_size=self.font_size,
                    size_hint=(None, None),
                    width=Window.width - dp(32),
                    height=dp(44),
                    background_normal='',
                    background_color=(0.95, 0.95, 0.95, 1),
                    color=COLORS['text']
                )
                item.bind(on_release=lambda btn: self._dropdown.select(btn.text))
                self._dropdown.add_widget(item)


def create_confirm_popup(message, on_confirm, confirm_text='确定', cancel_text='取消', is_danger=False):
    content = BoxLayout(orientation='vertical', spacing=dp(16), padding=dp(20))
    
    with content.canvas.before:
        Color(1, 1, 1, 1)
        _bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(12)])
    content.bind(pos=lambda i, v: setattr(_bg, 'pos', v), size=lambda i, v: setattr(_bg, 'size', v))
    
    msg_label = Label(
        text=message,
        font_name=FONT_NAME,
        font_size=dp(16),
        color=COLORS['text'],
        halign='center',
        valign='middle',
        size_hint_y=None,
        height=dp(60)
    )
    msg_label.bind(size=msg_label.setter('text_size'))
    content.add_widget(msg_label)
    
    btn_layout = BoxLayout(spacing=dp(12), size_hint_y=None, height=dp(48))
    
    cancel_btn = Button(
        text=cancel_text,
        font_name=FONT_NAME,
        font_size=dp(16),
        background_normal='',
        background_color=COLORS['text_hint']
    )
    
    confirm_btn_color = COLORS['accent'] if is_danger else COLORS['primary']
    confirm_btn = Button(
        text=confirm_text,
        font_name=FONT_NAME,
        font_size=dp(16),
        background_normal='',
        background_color=confirm_btn_color
    )
    
    btn_layout.add_widget(cancel_btn)
    btn_layout.add_widget(confirm_btn)
    content.add_widget(btn_layout)
    
    popup = Popup(
        title='',
        content=content,
        size_hint=(0.85, None),
        height=dp(160),
        auto_dismiss=False,
        background='',
        separator_color=(0, 0, 0, 0)
    )
    
    with popup.canvas.before:
        Color(1, 1, 1, 1)
        popup._bg_rect = RoundedRectangle(pos=popup.pos, size=popup.size, radius=[dp(16)])
    popup.bind(pos=lambda i, v: setattr(popup._bg_rect, 'pos', v), size=lambda i, v: setattr(popup._bg_rect, 'size', v))
    
    cancel_btn.bind(on_press=popup.dismiss)
    confirm_btn.bind(on_press=lambda x: on_confirm(popup))
    
    return popup


def create_message_popup(message):
    content = BoxLayout(orientation='vertical', spacing=dp(16), padding=dp(20))
    
    with content.canvas.before:
        Color(1, 1, 1, 1)
        _bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(12)])
    content.bind(pos=lambda i, v: setattr(_bg, 'pos', v), size=lambda i, v: setattr(_bg, 'size', v))
    
    msg_label = Label(
        text=message,
        font_name=FONT_NAME,
        font_size=dp(16),
        color=COLORS['text'],
        halign='center',
        valign='middle'
    )
    msg_label.bind(size=msg_label.setter('text_size'))
    content.add_widget(msg_label)
    
    popup = Popup(
        title='',
        content=content,
        size_hint=(0.7, None),
        height=dp(120),
        auto_dismiss=True,
        background='',
        separator_color=(0, 0, 0, 0)
    )
    
    with popup.canvas.before:
        Color(1, 1, 1, 1)
        popup._bg_rect = RoundedRectangle(pos=popup.pos, size=popup.size, radius=[dp(16)])
    popup.bind(pos=lambda i, v: setattr(popup._bg_rect, 'pos', v), size=lambda i, v: setattr(popup._bg_rect, 'size', v))
    
    return popup


def create_input_popup(hint_text, on_confirm, initial_value='', confirm_text='确定', title_text=''):
    content = BoxLayout(orientation='vertical', spacing=dp(16), padding=dp(20))
    
    with content.canvas.before:
        Color(1, 1, 1, 1)
        _bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(12)])
    content.bind(pos=lambda i, v: setattr(_bg, 'pos', v), size=lambda i, v: setattr(_bg, 'size', v))
    
    if title_text:
        title_label = Label(
            text=title_text,
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['text'],
            size_hint_y=None,
            height=dp(30)
        )
        content.add_widget(title_label)
    
    input_container = BoxLayout(size_hint_y=None, height=dp(48), padding=dp(2))
    with input_container.canvas.before:
        Color(0.9, 0.9, 0.9, 1)
        input_bg = RoundedRectangle(pos=input_container.pos, size=input_container.size, radius=[dp(8)])
    input_container.bind(pos=lambda i, v: setattr(input_bg, 'pos', v), size=lambda i, v: setattr(input_bg, 'size', v))
    
    text_input = TextInput(
        text=initial_value,
        hint_text=hint_text,
        font_name=FONT_NAME,
        font_size=dp(16),
        multiline=False,
        background_normal='',
        background_active='',
        background_color=(0, 0, 0, 0),
        foreground_color=COLORS['text'],
        padding=[dp(12), dp(14), dp(12), dp(14)]
    )
    input_container.add_widget(text_input)
    content.add_widget(input_container)
    
    btn_layout = BoxLayout(spacing=dp(12), size_hint_y=None, height=dp(48))
    
    cancel_btn = Button(
        text='取消',
        font_name=FONT_NAME,
        font_size=dp(16),
        background_normal='',
        background_color=COLORS['text_hint']
    )
    
    confirm_btn = Button(
        text=confirm_text,
        font_name=FONT_NAME,
        font_size=dp(16),
        background_normal='',
        background_color=COLORS['primary']
    )
    
    btn_layout.add_widget(cancel_btn)
    btn_layout.add_widget(confirm_btn)
    content.add_widget(btn_layout)
    
    popup = Popup(
        title='',
        content=content,
        size_hint=(0.85, None),
        height=dp(180),
        auto_dismiss=False,
        background='',
        separator_color=(0, 0, 0, 0)
    )
    
    with popup.canvas.before:
        Color(1, 1, 1, 1)
        popup._bg_rect = RoundedRectangle(pos=popup.pos, size=popup.size, radius=[dp(16)])
    popup.bind(pos=lambda i, v: setattr(popup._bg_rect, 'pos', v), size=lambda i, v: setattr(popup._bg_rect, 'size', v))
    
    cancel_btn.bind(on_press=popup.dismiss)
    confirm_btn.bind(on_press=lambda x: on_confirm(text_input.text, popup))
    
    return popup


class WorldCard(BoxLayout):
    def __init__(self, world, on_enter=None, on_edit=None, **kwargs):
        super().__init__(**kwargs)
        self.world = world
        self.on_enter = on_enter
        self.on_edit = on_edit
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(60)
        self.padding = [dp(16), dp(12)]
        
        self._long_press_triggered = False
        self._long_press_event = None
        
        with self.canvas.before:
            Color(*COLORS['surface'])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        inner = FloatLayout()
        
        name_label = Label(
            text=world.name,
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            valign='middle',
            pos_hint={'x': 0, 'center_y': 0.5},
            size_hint_x=0.7
        )
        name_label.bind(size=name_label.setter('text_size'))
        inner.add_widget(name_label)
        
        enter_label = Label(
            text='进入 >',
            font_size=dp(12),
            font_name=FONT_NAME,
            color=COLORS['primary'],
            halign='right',
            valign='middle',
            pos_hint={'right': 1, 'center_y': 0.5},
            size_hint_x=0.3
        )
        enter_label.bind(size=enter_label.setter('text_size'))
        inner.add_widget(enter_label)
        
        self.add_widget(inner)
    
    def _update_bg(self, instance, value):
        self._bg.pos = instance.pos
        self._bg.size = instance.size
    
    def _trigger_long_press(self, dt):
        self._long_press_triggered = True
        if self.on_edit:
            self.on_edit(self.world)
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._long_press_triggered = False
            self._long_press_event = Clock.schedule_once(self._trigger_long_press, 0.5)
            return True
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if self._long_press_event:
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        
        if self.collide_point(*touch.pos) and not self._long_press_triggered:
            if self.on_enter:
                self.on_enter(self.world)
            return True
        return super().on_touch_up(touch)
    
    def on_touch_move(self, touch):
        if self._long_press_event and not self.collide_point(*touch.pos):
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        return super().on_touch_move(touch)


class AutoExpandTextInput(BoxLayout):
    def __init__(self, hint_text='', initial_height=dp(100), **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = initial_height
        self.initial_height = initial_height
        self._focused = False
        
        with self.canvas.before:
            Color(*COLORS['surface_light'])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        with self.canvas.after:
            Color(0, 0, 0, 0)
            self._border_color = Color(0, 0, 0, 0)
            self._border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=dp(2))
        self.bind(pos=self._update_border, size=self._update_border)
        
        self.text_input = TextInput(
            hint_text=hint_text,
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=initial_height,
            background_normal='',
            background_color=(0, 0, 0, 0),
            foreground_color=COLORS['text'],
            hint_text_color=COLORS['text_hint'],
            padding=[dp(12), dp(12), dp(12), dp(12)],
            multiline=True
        )
        self.text_input.bind(text=self._adjust_height, focus=self._on_focus, size=self._on_size_change)
        self.add_widget(self.text_input)
    
    def _update_bg(self, instance, value):
        self._bg.pos = instance.pos
        self._bg.size = instance.size
    
    def _update_border(self, instance, value):
        self._border.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, dp(12))
    
    def _on_focus(self, instance, value):
        self._focused = value
        if value:
            self._border_color.rgba = (0, 0, 0, 1)
        else:
            self._border_color.rgba = (0, 0, 0, 0)
    
    def _on_size_change(self, instance, value):
        self._adjust_height(instance, instance.text)
    
    def _adjust_height(self, instance, value):
        Clock.schedule_once(self._do_adjust_height, 0)
    
    def _do_adjust_height(self, dt):
        text_height = self.text_input.minimum_height
        padding_total = dp(24)
        content_height = text_height + padding_total
        new_height = max(self.initial_height, content_height)
        self.height = new_height
        self.text_input.height = new_height
    
    @property
    def text(self):
        return self.text_input.text
    
    @text.setter
    def text(self, value):
        self.text_input.text = value


class WorldEditScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='世界名称',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        more_btn = Button(
            text='...',
            font_size=dp(18),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(50),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['text']
        )
        more_btn.bind(on_press=self.show_more_options)
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(more_btn)
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(16),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        name_label = Label(
            text='世界名称',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        name_label.bind(size=name_label.setter('text_size'))
        self.content_layout.add_widget(name_label)
        
        self.name_input = AutoExpandTextInput(
            hint_text='输入世界名称',
            initial_height=dp(50)
        )
        self.content_layout.add_widget(self.name_input)
        
        bg_label = Label(
            text='背景设定',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        bg_label.bind(size=bg_label.setter('text_size'))
        self.content_layout.add_widget(bg_label)
        
        self.background_input = AutoExpandTextInput(
            hint_text='描述这个世界的基本背景、历史、地理环境等...',
            initial_height=dp(120)
        )
        self.content_layout.add_widget(self.background_input)
        
        map_label = Label(
            text='世界地图',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        map_label.bind(size=map_label.setter('text_size'))
        self.content_layout.add_widget(map_label)
        
        self.map_preview = BoxLayout(
            size_hint_y=None,
            height=dp(100),
            orientation='vertical'
        )
        with self.map_preview.canvas.before:
            Color(*COLORS['surface_light'])
            self._map_bg = RoundedRectangle(pos=self.map_preview.pos, size=self.map_preview.size, radius=[dp(12)])
        self.map_preview.bind(pos=self._update_map_bg, size=self._update_map_bg)
        
        self.map_label = Label(
            text='点击上传地图图片',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_hint']
        )
        self.map_preview.add_widget(self.map_label)
        self.map_preview.bind(on_touch_down=self.on_map_touch)
        self.content_layout.add_widget(self.map_preview)
        
        self.content_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(16)))
        
        manage_label = Label(
            text='管理',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        manage_label.bind(size=manage_label.setter('text_size'))
        self.content_layout.add_widget(manage_label)
        
        character_btn = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            orientation='horizontal'
        )
        with character_btn.canvas.before:
            Color(*COLORS['surface'])
            self._char_bg = RoundedRectangle(pos=character_btn.pos, size=character_btn.size, radius=[dp(12)])
        character_btn.bind(pos=self._update_char_bg, size=self._update_char_bg)
        
        char_label = Label(
            text='角色管理',
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            valign='middle'
        )
        char_label.bind(size=char_label.setter('text_size'))
        character_btn.add_widget(char_label)
        
        char_arrow = Label(
            text='>',
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text_hint'],
            size_hint_x=None,
            width=dp(30)
        )
        character_btn.add_widget(char_arrow)
        
        character_btn.bind(on_touch_down=self.on_character_btn_touch)
        self.content_layout.add_widget(character_btn)
        
        location_btn = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            orientation='horizontal'
        )
        with location_btn.canvas.before:
            Color(*COLORS['surface'])
            self._loc_bg = RoundedRectangle(pos=location_btn.pos, size=location_btn.size, radius=[dp(12)])
        location_btn.bind(pos=self._update_loc_bg, size=self._update_loc_bg)
        
        loc_label = Label(
            text='位置管理',
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            valign='middle'
        )
        loc_label.bind(size=loc_label.setter('text_size'))
        location_btn.add_widget(loc_label)
        
        loc_arrow = Label(
            text='>',
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text_hint'],
            size_hint_x=None,
            width=dp(30)
        )
        location_btn.add_widget(loc_arrow)
        
        location_btn.bind(on_touch_down=self.on_location_btn_touch)
        self.content_layout.add_widget(location_btn)
        
        memory_btn = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            orientation='horizontal'
        )
        with memory_btn.canvas.before:
            Color(*COLORS['surface'])
            self._mem_bg = RoundedRectangle(pos=memory_btn.pos, size=memory_btn.size, radius=[dp(12)])
        memory_btn.bind(pos=self._update_mem_bg, size=self._update_mem_bg)
        
        mem_label = Label(
            text='世界记忆',
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            valign='middle'
        )
        mem_label.bind(size=mem_label.setter('text_size'))
        memory_btn.add_widget(mem_label)
        
        mem_arrow = Label(
            text='>',
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text_hint'],
            size_hint_x=None,
            width=dp(30)
        )
        memory_btn.add_widget(mem_arrow)
        
        memory_btn.bind(on_touch_down=self.on_memory_btn_touch)
        self.content_layout.add_widget(memory_btn)
        
        self.content_layout.add_widget(BoxLayout())
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        save_container = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        with save_container.canvas.before:
            Color(*COLORS['surface'])
            self._save_bg = RoundedRectangle(pos=save_container.pos, size=save_container.size)
        save_container.bind(pos=self._update_save_bg, size=self._update_save_bg)
        
        save_btn = Button(
            text='保存',
            font_size=dp(16),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        save_btn.bind(on_press=self.save_world)
        save_container.add_widget(save_btn)
        self.root_layout.add_widget(save_container)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_char_bg(self, instance, value):
        self._char_bg.pos = instance.pos
        self._char_bg.size = instance.size
    
    def _update_loc_bg(self, instance, value):
        self._loc_bg.pos = instance.pos
        self._loc_bg.size = instance.size
    
    def _update_mem_bg(self, instance, value):
        self._mem_bg.pos = instance.pos
        self._mem_bg.size = instance.size
    
    def _update_save_bg(self, instance, value):
        self._save_bg.pos = instance.pos
        self._save_bg.size = instance.size
    
    def _update_map_bg(self, instance, value):
        self._map_bg.pos = instance.pos
        self._map_bg.size = instance.size
    
    def set_world(self, world_id):
        self.world_id = world_id
        self.map_image_path = None
        if world_id:
            world = self.db.get_world(world_id)
            if world:
                self.title_label.text = world.name
                self.name_input.text = world.name or ''
                self.background_input.text = world.background or ''
                if world.map_image and os.path.exists(world.map_image):
                    self.map_image_path = world.map_image
                    self.map_label.text = '已设置地图'
                else:
                    self.map_label.text = '点击上传地图图片'
        else:
            self.title_label.text = '新世界'
            self.name_input.text = ''
            self.background_input.text = ''
            self.map_label.text = '点击上传地图图片'
    
    def on_map_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.upload_map()
            return True
        return False
    
    def upload_map(self):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title='选择地图图片',
            filetypes=[('图片文件', '*.png *.jpg *.jpeg *.gif *.bmp')]
        )
        root.destroy()
        
        if file_path:
            self.map_image_path = file_path
            self.map_label.text = '已设置地图'
    
    def on_character_btn_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            if hasattr(self.manager, 'character_list_screen'):
                self.manager.character_list_screen.set_world(self.world_id)
                self.manager.current = 'character_list'
            return True
        return False
    
    def on_location_btn_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            if hasattr(self.manager, 'location_list_screen'):
                self.manager.location_list_screen.set_world(self.world_id)
                self.manager.current = 'location_list'
            return True
        return False
    
    def on_memory_btn_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            if hasattr(self.manager, 'world_memory_screen') and self.world_id:
                self.manager.world_memory_screen.set_world(self.world_id)
                self.manager.current = 'world_memory'
            return True
        return False
    
    def save_world(self, instance):
        name = self.name_input.text.strip()
        if not name:
            popup = create_message_popup('请输入世界名称')
            popup.open()
            return
        
        background = self.background_input.text.strip()
        map_image = getattr(self, 'map_image_path', None)
        
        if self.world_id:
            self.db.update_world(self.world_id, name=name, background=background, map_image=map_image)
        else:
            world = self.db.create_world(name=name, background=background)
            self.world_id = world.id
            self.title_label.text = name
            if map_image:
                self.db.update_world(self.world_id, map_image=map_image)
        
        popup = create_message_popup('保存成功')
        popup.open()
    
    def show_more_options(self, instance):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        
        script_btn = Button(
            text='剧本设置',
            font_name=FONT_NAME,
            font_size=dp(14),
            background_normal='',
            background_color=COLORS['surface_light'],
            color=COLORS['text'],
            size_hint_y=None,
            height=dp(44)
        )
        script_btn.bind(on_press=self.open_script_settings)
        content.add_widget(script_btn)
        
        delete_btn = Button(
            text='删除世界',
            font_name=FONT_NAME,
            font_size=dp(14),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(44)
        )
        delete_btn.bind(on_press=self.delete_world)
        content.add_widget(delete_btn)
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(14),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(44)
        )
        
        popup = Popup(
            title='更多选项',
            content=content,
            size_hint=(0.8, None),
            height=dp(200),
            auto_dismiss=False
        )
        cancel_btn.bind(on_press=popup.dismiss)
        content.add_widget(cancel_btn)
        
        self._more_popup = popup
        popup.open()
    
    def open_script_settings(self, instance):
        if self._more_popup:
            self._more_popup.dismiss()
        
        if hasattr(self.manager, 'script_settings_screen'):
            self.manager.script_settings_screen.set_world(self.world_id)
            self.manager.current = 'script_settings'
    
    def delete_world(self, instance):
        if self._more_popup:
            self._more_popup.dismiss()
        
        if not self.world_id:
            return
        
        popup = create_confirm_popup(
            '确定要删除这个世界吗？\n此操作不可恢复',
            self._do_delete_world,
            confirm_text='删除',
            is_danger=True
        )
        popup.open()
    
    def _do_delete_world(self, popup):
        if self.world_id:
            self.db.delete_world(self.world_id)
            self.world_id = None
        popup.dismiss()
        self.manager.current = 'world_list'
    
    def go_back(self, instance):
        if hasattr(self.manager, 'world_list_screen'):
            self.manager.world_list_screen.load_worlds()
        self.manager.current = 'world_list'


class WorldListScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(16), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        title_container = BoxLayout()
        title = Label(
            text='旮旯GAME',
            font_size=dp(22),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['primary'],
            halign='center',
            valign='middle'
        )
        title.bind(size=title.setter('text_size'))
        title_container.add_widget(title)
        
        settings_btn = Button(
            text='设置',
            font_size=dp(12),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(50),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        settings_btn.bind(on_press=self.open_api_settings)
        
        header.add_widget(title_container)
        header.add_widget(settings_btn)
        
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.world_list = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(16), dp(8), dp(16), dp(8)]
        )
        self.world_list.bind(minimum_height=self.world_list.setter('height'))
        
        self.scroll_view.add_widget(self.world_list)
        self.root_layout.add_widget(self.scroll_view)
        
        add_btn_container = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        with add_btn_container.canvas.before:
            Color(*COLORS['surface'])
            self._add_btn_bg = RoundedRectangle(pos=add_btn_container.pos, size=add_btn_container.size)
        add_btn_container.bind(pos=self._update_add_btn_bg, size=self._update_add_btn_bg)
        
        add_btn = Button(
            text='+ 创建新世界',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        add_btn.bind(on_press=self.create_world)
        add_btn_container.add_widget(add_btn)
        self.root_layout.add_widget(add_btn_container)
        
        self.add_widget(self.root_layout)
        self.load_worlds()
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_add_btn_bg(self, instance, value):
        self._add_btn_bg.pos = instance.pos
        self._add_btn_bg.size = instance.size
    
    def load_worlds(self):
        self.world_list.clear_widgets()
        
        worlds = self.db.get_all_worlds()
        
        if not worlds:
            empty_label = Label(
                text='暂无世界\n点击下方按钮创建',
                font_size=dp(14),
                font_name=FONT_NAME,
                color=COLORS['text_hint'],
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(200)
            )
            empty_label.bind(size=empty_label.setter('text_size'))
            self.world_list.add_widget(empty_label)
        else:
            for world in worlds:
                world_card = WorldCard(world, on_enter=self.enter_world, on_edit=self.edit_world)
                self.world_list.add_widget(world_card)
    
    def on_enter(self):
        self.load_worlds()
    
    def enter_world(self, world):
        if hasattr(self.manager, 'chat_screen'):
            self.manager.chat_screen.set_world(world.id)
            self.manager.current = 'chat'
    
    def edit_world(self, world):
        if hasattr(self.manager, 'world_edit_screen'):
            self.manager.world_edit_screen.set_world(world.id)
            self.manager.current = 'world_edit'
    
    def create_world(self, instance):
        if hasattr(self.manager, 'world_edit_screen'):
            self.manager.world_edit_screen.set_world(None)
            self.manager.current = 'world_edit'
    
    def open_api_settings(self, instance):
        if hasattr(self.manager, 'api_settings_screen'):
            self.manager.current = 'api_settings'


class ApiSettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(16), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='< 返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(70),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        title = Label(
            text='API设置',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(title)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(70)))
        
        self.root_layout.add_widget(header)
        
        content = BoxLayout(
            orientation='vertical',
            spacing=dp(16),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        
        api1_title = Label(
            text='API 1 (对话生成)',
            font_size=dp(14),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        api1_title.bind(size=api1_title.setter('text_size'))
        content.add_widget(api1_title)
        
        self.api1_key_input = TextInput(
            hint_text='API Key',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            multiline=False,
            password=True
        )
        content.add_widget(self.api1_key_input)
        
        self.api1_model_input = TextInput(
            hint_text='Model (默认: deepseek-chat)',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            multiline=False
        )
        content.add_widget(self.api1_model_input)
        
        api2_title = Label(
            text='API 2 (记忆提取)',
            font_size=dp(14),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        api2_title.bind(size=api2_title.setter('text_size'))
        content.add_widget(api2_title)
        
        self.api2_key_input = TextInput(
            hint_text='API Key',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            multiline=False,
            password=True
        )
        content.add_widget(self.api2_key_input)
        
        self.api2_model_input = TextInput(
            hint_text='Model (默认: deepseek-chat)',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            multiline=False
        )
        content.add_widget(self.api2_model_input)
        
        content.add_widget(BoxLayout())
        
        save_btn = Button(
            text='保存设置',
            font_size=dp(16),
            font_name=FONT_NAME,
            size_hint_y=None,
            height=dp(48),
            background_normal='',
            background_color=COLORS['primary']
        )
        save_btn.bind(on_press=self.save_settings)
        content.add_widget(save_btn)
        
        self.root_layout.add_widget(content)
        self.add_widget(self.root_layout)
        
        self.load_settings()
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def load_settings(self):
        config = self.db.get_api_config()
        if config:
            self.api1_key_input.text = config.api1_key or ''
            self.api1_model_input.text = config.api1_model or ''
            self.api2_key_input.text = config.api2_key or ''
            self.api2_model_input.text = config.api2_model or ''
    
    def save_settings(self, instance):
        api1_key = self.api1_key_input.text.strip()
        api1_model = self.api1_model_input.text.strip() or 'deepseek-chat'
        api2_key = self.api2_key_input.text.strip()
        api2_model = self.api2_model_input.text.strip() or 'deepseek-chat'
        
        self.db.save_api_config(api1_key, api1_model, api2_key, api2_model)
        
        popup = create_message_popup('设置已保存')
        popup.open()
    
    def go_back(self, instance):
        self.manager.current = 'world_list'


class MessageBubble(BoxLayout):
    MAX_WIDTH = dp(250)
    
    def __init__(self, segments, max_width=None, is_on_call=False, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.size_hint_x = None
        self.padding = [dp(12), dp(10), dp(12), dp(10)]
        self.is_on_call = is_on_call
        
        if max_width:
            self.MAX_WIDTH = max_width
        
        with self.canvas.before:
            Color(0.3, 0.3, 0.3, 0.4)
            self._border = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            Color(1, 1, 1, 0.75)
            self._bg = RoundedRectangle(
                pos=(self.pos[0] + dp(1.5), self.pos[1] + dp(1.5)),
                size=(self.size[0] - dp(3), self.size[1] - dp(3)),
                radius=[dp(10)]
            )
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        text_parts = []
        for segment in segments:
            seg_type = segment.get('type', 'speech')
            seg_content = segment.get('content', '')
            if not seg_content:
                continue
            
            if seg_type == 'action':
                if is_on_call:
                    continue
                color_hex = '#4D66B3'
                prefix = '【动作】'
            elif seg_type == 'speech':
                color_hex = '#1A1A1A'
                prefix = ''
            elif seg_type == 'thought':
                color_hex = '#806699'
                prefix = '【心声】'
            else:
                color_hex = '#1A1A1A'
                prefix = ''
            
            text_parts.append(f'[color={color_hex}]{prefix}{seg_content}[/color]')
        
        full_text = '\n'.join(text_parts)
        
        self.content_label = Label(
            text=full_text,
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            halign='left',
            valign='top',
            size_hint=(None, None),
            markup=True
        )
        self.content_label.bind(
            texture_size=self._on_texture_size
        )
        
        self.add_widget(self.content_label)
    
    def _on_texture_size(self, instance, value):
        self.content_label.height = value[1]
        content_width = min(value[0], self.MAX_WIDTH)
        self.content_label.width = content_width
        self.content_label.text_size = (content_width, None)
        self.width = content_width + dp(24)
        self.height = value[1] + dp(20)
    
    def _update_bg(self, instance, value):
        self._border.pos = instance.pos
        self._border.size = instance.size
        self._bg.pos = (instance.pos[0] + dp(1.5), instance.pos[1] + dp(1.5))
        self._bg.size = (instance.size[0] - dp(3), instance.size[1] - dp(3))


class CharacterMessageGroup(BoxLayout):
    message_id = None
    on_rewind_callback = None
    on_avatar_click = None
    character_id = None
    
    def __init__(self, character_name, avatar_path, segments, message_id=None, on_rewind_callback=None, character_id=None, on_avatar_click=None, is_on_call=False, **kwargs):
        super().__init__(**kwargs)
        self.message_id = message_id
        self.on_rewind_callback = on_rewind_callback
        self.character_id = character_id
        self.on_avatar_click = on_avatar_click
        self._long_press_event = None
        self._touch_pos = None
        self.is_on_call = is_on_call
        
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding = [dp(0), dp(4), dp(8), dp(4)]
        self.spacing = dp(-40)
        
        top_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(10)
        )
        
        self.avatar_container = AnchorLayout(
            size_hint=(None, None),
            size=(dp(50), dp(50))
        )
        
        avatar_inner = BoxLayout(
            size_hint=(None, None),
            size=(dp(50), dp(50))
        )
        
        avatar_bg_color = COLORS['call_orange'] if is_on_call else COLORS['primary_light']
        with avatar_inner.canvas.before:
            Color(*avatar_bg_color)
            self._avatar_bg = RoundedRectangle(
                pos=avatar_inner.pos,
                size=avatar_inner.size,
                radius=[dp(25)]
            )
        avatar_inner.bind(pos=self._update_avatar_bg, size=self._update_avatar_bg)
        
        if avatar_path and os.path.exists(avatar_path):
            avatar_img = Image(
                source=avatar_path,
                size_hint=(None, None),
                size=(dp(50), dp(50)),
                allow_stretch=True
            )
            avatar_inner.add_widget(avatar_img)
        else:
            avatar_label = Label(
                text=character_name[0] if character_name else '?',
                font_name=FONT_NAME,
                font_size=dp(20),
                color=COLORS['text']
            )
            avatar_inner.add_widget(avatar_label)
        
        self.avatar_container.add_widget(avatar_inner)
        
        if self.on_avatar_click and self.character_id:
            avatar_btn = Button(
                size_hint=(None, None),
                size=(dp(50), dp(50)),
                background_normal='',
                background_color=(0, 0, 0, 0)
            )
            avatar_btn.bind(on_press=lambda x: self.on_avatar_click(self.character_id))
            self.avatar_container.add_widget(avatar_btn)
        
        top_row.add_widget(self.avatar_container)
        top_row.add_widget(BoxLayout(size_hint_x=1))
        
        self.add_widget(top_row)
        
        bubble_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(0)
        )
        
        spacer = BoxLayout(size_hint_x=None, width=dp(50))
        bubble_row.add_widget(spacer)
        
        bubble_container = BoxLayout(
            orientation='vertical', 
            size_hint_x=None, 
            size_hint_y=None, 
            spacing=dp(2)
        )
        
        name_label = Label(
            text=character_name,
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['call_orange'] if is_on_call else COLORS['text'],
            bold=True,
            halign='left',
            valign='middle',
            size_hint=(None, None),
            height=dp(15)
        )
        name_label.bind(size=name_label.setter('text_size'))
        bubble_container.add_widget(name_label)
        
        self.bubble = MessageBubble(segments, is_on_call=is_on_call)
        bubble_container.add_widget(self.bubble)
        
        bubble_row.add_widget(bubble_container)
        
        bubble_row.add_widget(BoxLayout(size_hint_x=1))
        
        right_spacer = BoxLayout(size_hint_x=None, width=dp(80))
        bubble_row.add_widget(right_spacer)
        
        self.add_widget(bubble_row)
        self.bubble.bind(height=self._on_bubble_height, width=self._on_bubble_width)
        self.bubble_container = bubble_container
        self.name_label = name_label
    
    def _on_bubble_width(self, instance, value):
        self.bubble_container.width = value
        self.name_label.width = value
    
    def _on_bubble_height(self, instance, value):
        self.bubble_container.height = value + dp(15)
        self.children[0].height = value + dp(15)
        self.height = dp(10) + value + dp(25)
    
    def _update_avatar_bg(self, instance, value):
        self._avatar_bg.pos = instance.pos
        self._avatar_bg.size = instance.size
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_pos = touch.pos
            self._long_press_event = Clock.schedule_once(self._on_long_press, 0.5)
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if self._long_press_event:
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        return super().on_touch_up(touch)
    
    def on_touch_move(self, touch):
        if self._long_press_event:
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        return super().on_touch_move(touch)
    
    def _on_long_press(self, dt):
        if self._touch_pos and self.message_id and self.on_rewind_callback:
            self._show_rewind_button(self._touch_pos)
    
    def _show_rewind_button(self, pos):
        parent = self.parent
        while parent and not hasattr(parent, 'root_layout'):
            parent = parent.parent
        
        if not parent:
            return
        
        rewind_btn = Button(
            text='回溯',
            font_name=FONT_NAME,
            font_size=dp(12),
            size_hint=(None, None),
            size=(dp(60), dp(32)),
            background_normal='',
            background_color=(1, 1, 1, 1),
            color=COLORS['text']
        )
        
        bubble_pos = self.bubble.to_window(*self.bubble.pos)
        bubble_right = bubble_pos[0] + self.bubble.width
        bubble_center_y = bubble_pos[1] + self.bubble.height / 2
        
        btn_x = bubble_right + dp(2)
        btn_y = bubble_center_y - dp(16)
        
        if btn_y < dp(10):
            btn_y = dp(10)
        if btn_y > Window.height - dp(42):
            btn_y = Window.height - dp(42)
        
        rewind_btn.pos = (btn_x, btn_y)
        
        rewind_btn.opacity = 0
        parent.root_layout.add_widget(rewind_btn)
        
        from kivy.animation import Animation
        Animation(opacity=1, duration=0.2).start(rewind_btn)
        
        def dismiss(*args):
            try:
                parent.root_layout.remove_widget(rewind_btn)
            except:
                pass
        
        def on_rewind_press(instance):
            dismiss()
            if self.on_rewind_callback:
                self.on_rewind_callback(self.message_id)
        
        rewind_btn.bind(on_press=on_rewind_press)
        
        Clock.schedule_once(lambda dt: self._setup_dismiss_listener(parent.root_layout, rewind_btn, dismiss), 0)
    
    def _setup_dismiss_listener(self, root_layout, rewind_btn, dismiss_callback):
        def on_any_touch(instance, touch):
            if not rewind_btn.collide_point(*touch.pos):
                dismiss_callback()
                Window.unbind(on_touch_down=on_any_touch)
        
        Window.bind(on_touch_down=on_any_touch)


class UserMessageGroup(BoxLayout):
    message_id = None
    on_rewind_callback = None
    
    def __init__(self, user_name, segments, message_id=None, on_rewind_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.message_id = message_id
        self.on_rewind_callback = on_rewind_callback
        self._long_press_event = None
        self._touch_pos = None
        
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding = [dp(8), dp(4), dp(8), dp(4)]
        
        top_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(10)
        )
        top_row.add_widget(BoxLayout(size_hint_x=1))
        self.add_widget(top_row)
        
        bubble_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(0)
        )
        
        bubble_row.add_widget(BoxLayout(size_hint_x=1))
        
        bubble_container = BoxLayout(
            orientation='vertical', 
            size_hint_x=None, 
            size_hint_y=None, 
            spacing=dp(2)
        )
        
        name_label = Label(
            text=user_name,
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            bold=True,
            halign='right',
            valign='middle',
            size_hint=(None, None),
            height=dp(15)
        )
        name_label.bind(size=name_label.setter('text_size'))
        bubble_container.add_widget(name_label)
        
        self.bubble = MessageBubble(segments)
        bubble_container.add_widget(self.bubble)
        
        bubble_row.add_widget(bubble_container)
        
        right_spacer = BoxLayout(size_hint_x=None, width=dp(15))
        bubble_row.add_widget(right_spacer)
        
        self.add_widget(bubble_row)
        self.bubble.bind(height=self._on_bubble_height, width=self._on_bubble_width)
        self.bubble_container = bubble_container
        self.name_label = name_label
    
    def _on_bubble_width(self, instance, value):
        self.bubble_container.width = value
        self.name_label.width = value
    
    def _on_bubble_height(self, instance, value):
        self.bubble_container.height = value + dp(15)
        self.children[0].height = value + dp(15)
        self.height = dp(10) + value + dp(25)
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_pos = touch.pos
            self._long_press_event = Clock.schedule_once(self._on_long_press, 0.5)
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if self._long_press_event:
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        return super().on_touch_up(touch)
    
    def on_touch_move(self, touch):
        if self._long_press_event:
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        return super().on_touch_move(touch)
    
    def _on_long_press(self, dt):
        if self._touch_pos and self.message_id and self.on_rewind_callback:
            self._show_rewind_button(self._touch_pos)
    
    def _show_rewind_button(self, pos):
        parent = self.parent
        while parent and not hasattr(parent, 'root_layout'):
            parent = parent.parent
        
        if not parent:
            return
        
        rewind_btn = Button(
            text='回溯',
            font_name=FONT_NAME,
            font_size=dp(12),
            size_hint=(None, None),
            size=(dp(60), dp(32)),
            background_normal='',
            background_color=(1, 1, 1, 1),
            color=COLORS['text']
        )
        
        bubble_pos = self.bubble.to_window(*self.bubble.pos)
        bubble_center_y = bubble_pos[1] + self.bubble.height / 2
        
        btn_x = bubble_pos[0] - dp(70)
        btn_y = bubble_center_y - dp(16)
        
        if btn_y < dp(10):
            btn_y = dp(10)
        if btn_y > Window.height - dp(42):
            btn_y = Window.height - dp(42)
        
        rewind_btn.pos = (btn_x, btn_y)
        
        rewind_btn.opacity = 0
        parent.root_layout.add_widget(rewind_btn)
        
        from kivy.animation import Animation
        Animation(opacity=1, duration=0.2).start(rewind_btn)
        
        def dismiss(*args):
            try:
                parent.root_layout.remove_widget(rewind_btn)
            except:
                pass
        
        def on_rewind_press(instance):
            dismiss()
            if self.on_rewind_callback:
                self.on_rewind_callback(self.message_id)
        
        rewind_btn.bind(on_press=on_rewind_press)
        
        Clock.schedule_once(lambda dt: self._setup_dismiss_listener(parent.root_layout, rewind_btn, dismiss), 0)
    
    def _setup_dismiss_listener(self, root_layout, rewind_btn, dismiss_callback):
        def on_any_touch(instance, touch):
            if not rewind_btn.collide_point(*touch.pos):
                dismiss_callback()
                Window.unbind(on_touch_down=on_any_touch)
        
        Window.bind(on_touch_down=on_any_touch)


class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.session_id = None
        self.characters = []
        self.character_map = {}
        self.is_processing = False
        self.dialogue_manager = None
        self.current_view_location = None
        self.is_viewing_other_location = False
        self.build_ui()
    
    def init_dialogue_manager(self):
        config = self.db.get_api_config()
        
        api1_key = config.api1_key if config else None
        api2_key = config.api2_key if config else None
        
        self.api1_client = None
        self.api2_client = None
        
        if api1_key:
            self.api1_client = DeepSeekClient(
                api1_key,
                "https://api.deepseek.com/v1"
            )
        
        if api2_key:
            self.api2_client = DeepSeekClient(
                api2_key,
                "https://api.deepseek.com/v1"
            )
        
        bg_client = self.api1_client if self.api1_client else self.api2_client
        
        if bg_client:
            self.bg_selector = BackgroundSelector(bg_client)
            self.dialogue_manager = DialogueManager(
                bg_client, self.db, self.bg_selector,
                self.api1_client, self.api2_client
            )
    
    def build_ui(self):
        self.root_layout = FloatLayout()
        
        self.background_layer = FloatLayout()
        self.root_layout.add_widget(self.background_layer)
        
        self.env_background = Image(
            source='',
            fit_mode='cover',
            size_hint=(1, 1)
        )
        self.background_layer.add_widget(self.env_background)
        
        self.character_background_container = AnchorLayout(
            anchor_x='center',
            anchor_y='bottom',
            size_hint=(1, 1),
            padding=[0, 0, 0, dp(60)]
        )
        self.character_background = Image(
            source='',
            fit_mode='contain',
            size_hint=(None, None),
            size=(Window.width, Window.height - dp(60))
        )
        self.character_background_container.add_widget(self.character_background)
        self.character_background_container.opacity = 0
        self.background_layer.add_widget(self.character_background_container)
        
        self.content_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(16), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_border = RoundedRectangle(pos=header.pos, size=header.size)
            Color(1, 1, 1, 0.95)
            self._header_bg = RoundedRectangle(
                pos=(header.pos[0] + dp(1), header.pos[1] + dp(1)),
                size=(header.size[0] - dp(2), header.size[1] - dp(2))
            )
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='< 返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(70),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.world_title = Label(
            text='世界名称',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        right_btns = BoxLayout(size_hint_x=None, width=dp(50), spacing=dp(4))
        
        menu_btn = Button(
            text='菜单',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(50),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        menu_btn.bind(on_press=self.open_menu)
        self.menu_btn = menu_btn
        right_btns.add_widget(menu_btn)
        
        header.add_widget(back_btn)
        header.add_widget(self.world_title)
        header.add_widget(right_btns)
        
        self.content_layout.add_widget(header)
        
        time_row = BoxLayout(
            size_hint_y=None,
            height=dp(32),
            padding=[dp(12), dp(2), dp(12), dp(2)]
        )
        
        with time_row.canvas.before:
            Color(0.98, 0.98, 0.98, 1)
            self._time_row_bg = RoundedRectangle(pos=time_row.pos, size=time_row.size)
        time_row.bind(pos=lambda i, v: setattr(self._time_row_bg, 'pos', v), size=lambda i, v: setattr(self._time_row_bg, 'size', v))
        
        self.time_label = Label(
            text='2024-01-01 08:00',
            font_name=FONT_NAME,
            font_size=dp(13),
            color=COLORS['text_secondary'],
            halign='center',
            valign='middle'
        )
        self.time_label.bind(size=self.time_label.setter('text_size'))
        time_row.add_widget(self.time_label)
        
        self.content_layout.add_widget(time_row)
        
        view_row = BoxLayout(
            size_hint_y=None,
            height=dp(44),
            padding=[dp(12), dp(2), dp(12), dp(6)]
        )
        
        view_label_container = BoxLayout(
            size_hint_x=None,
            width=dp(50),
            padding=[0, dp(4), 0, 0]
        )
        
        view_label = Label(
            text='视角:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text_secondary'],
            halign='left',
            valign='middle'
        )
        view_label.bind(size=view_label.setter('text_size'))
        
        view_label_container.add_widget(view_label)
        
        self.view_spinner = ChineseSpinner(
            text='当前位置',
            font_name=FONT_NAME,
            font_size=dp(13),
            size_hint_x=1,
            height=dp(36),
            values=[],
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1),
            color=COLORS['text']
        )
        self.view_spinner.bind(text=self.on_view_location_changed)
        
        view_row.add_widget(view_label_container)
        view_row.add_widget(self.view_spinner)
        
        self.content_layout.add_widget(view_row)
        
        character_activity_row = BoxLayout(
            size_hint_y=None,
            height=dp(44),
            padding=[dp(12), dp(2), dp(12), dp(6)]
        )
        
        activity_label_container = BoxLayout(
            size_hint_x=None,
            width=dp(50),
            padding=[0, dp(4), 0, 0]
        )
        
        activity_label = Label(
            text='发言:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text_secondary'],
            halign='left',
            valign='middle'
        )
        activity_label.bind(size=activity_label.setter('text_size'))
        activity_label_container.add_widget(activity_label)
        
        self.character_spinner = ChineseSpinner(
            text='自动选择',
            font_name=FONT_NAME,
            font_size=dp(13),
            size_hint_x=1,
            height=dp(36),
            values=['自动选择'],
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1),
            color=COLORS['text']
        )
        
        character_activity_row.add_widget(activity_label_container)
        character_activity_row.add_widget(self.character_spinner)
        
        self.content_layout.add_widget(character_activity_row)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.message_list = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=[dp(12), dp(8), dp(12), dp(8)]
        )
        self.message_list.bind(minimum_height=self.message_list.setter('height'))
        
        self.scroll_view.add_widget(self.message_list)
        self.content_layout.add_widget(self.scroll_view)
        
        input_container = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(8), dp(8), dp(8), dp(8)],
            spacing=dp(8)
        )
        with input_container.canvas.before:
            Color(*COLORS['surface'])
            self._input_border = RoundedRectangle(pos=input_container.pos, size=input_container.size)
            Color(1, 1, 1, 0.95)
            self._input_bg = RoundedRectangle(
                pos=(input_container.pos[0] + dp(1), input_container.pos[1] + dp(1)),
                size=(input_container.size[0] - dp(2), input_container.size[1] - dp(2))
            )
        input_container.bind(pos=self._update_input_bg, size=self._update_input_bg)
        
        self.message_input = TextInput(
            hint_text='输入消息...',
            font_name=FONT_NAME,
            font_size=dp(14),
            multiline=False,
            background_normal='',
            background_active='',
            background_color=(0.95, 0.95, 0.95, 1),
            foreground_color=COLORS['text'],
            padding=[dp(12), dp(14), dp(12), dp(14)]
        )
        input_container.add_widget(self.message_input)
        
        send_btn = Button(
            text='发送',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        send_btn.bind(on_press=self.send_message)
        input_container.add_widget(send_btn)
        
        listen_btn = Button(
            text='聆听',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        listen_btn.bind(on_press=self.listen_mode)
        input_container.add_widget(listen_btn)
        
        self.content_layout.add_widget(input_container)
        self.root_layout.add_widget(self.content_layout)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_border.pos = instance.pos
        self._header_border.size = instance.size
        self._header_bg.pos = (instance.pos[0] + dp(1), instance.pos[1] + dp(1))
        self._header_bg.size = (instance.size[0] - dp(2), instance.size[1] - dp(2))
    
    def _update_input_bg(self, instance, value):
        self._input_border.pos = instance.pos
        self._input_border.size = instance.size
        self._input_bg.pos = (instance.pos[0] + dp(1), instance.pos[1] + dp(1))
        self._input_bg.size = (instance.size[0] - dp(2), instance.size[1] - dp(2))
    
    def update_time_display(self, world):
        if hasattr(self, 'time_label') and world:
            self.time_label.text = f"{world.current_date} {world.current_time}"
    
    def set_world(self, world_id):
        self.world_id = world_id
        world = self.db.get_world(world_id)
        if world:
            self.world_title.text = world.name
            self.update_time_display(world)
            self.characters = self.db.get_characters_by_world(world_id)
            self.character_map = {c.id: c for c in self.characters}
            
            if world.background and os.path.exists(world.background):
                self.env_background.source = world.background
            
            sessions = self.db.get_chat_sessions_by_world(world_id)
            if sessions:
                self.session_id = sessions[-1].id
            
            self.init_dialogue_manager()
            self.load_view_locations()
            self.update_speaker_list()
            self.update_call_button_state()
            if world.user_location:
                self.set_location_background(world.user_location)
            self.load_messages()
    
    def get_available_characters(self, location_name, all_characters):
        locations = self.db.get_locations(self.world_id)
        location = next((loc for loc in locations if loc.name == location_name), None)
        
        if not location:
            return [c for c in all_characters if c.location == location_name]
        
        if location.parent_location_id is None:
            sub_locations = self.db.get_sub_locations(location.id)
            
            if sub_locations:
                sub_location_names = [sub_loc.name for sub_loc in sub_locations]
                return [c for c in all_characters if c.location in sub_location_names]
            else:
                return [c for c in all_characters if c.location == location_name]
        else:
            return [c for c in all_characters if c.location == location_name]
    
    def update_speaker_list(self):
        world = self.db.get_world(self.world_id)
        
        if self.is_viewing_other_location:
            view_location = self.current_view_location
        else:
            view_location = world.user_location if world and world.user_location else None
        
        all_characters = self.db.get_characters_by_world(self.world_id)
        active_calls = self.db.get_active_calls_by_world(self.world_id)
        call_character_ids = {call.character_id for call in active_calls}
        
        if view_location:
            characters = self.get_available_characters(view_location, all_characters)
        else:
            characters = all_characters
        
        for char in all_characters:
            if char.id in call_character_ids and char not in characters:
                characters.append(char)
        
        if not characters:
            self.character_spinner.values = ['自动选择']
            self.character_spinner.text = '自动选择'
            return
        
        import random
        auto_selected_char = None
        total_score = sum(c.activity_score for c in characters)
        if total_score == 0:
            auto_selected_char = characters[0]
        else:
            rand = random.randint(1, total_score)
            current = 0
            for char in characters:
                current += char.activity_score
                if rand <= current:
                    auto_selected_char = char
                    break
        
        sorted_characters = sorted(characters, key=lambda c: c.activity_score, reverse=True)
        
        spinner_values = []
        if auto_selected_char:
            call_marker = ' 📞' if auto_selected_char.id in call_character_ids else ''
            spinner_values.append(f'自动选择 ({auto_selected_char.name}){call_marker}')
        else:
            spinner_values.append('自动选择')
        
        for char in sorted_characters:
            call_marker = ' 📞' if char.id in call_character_ids else ''
            spinner_values.append(f'{char.name} (活跃度: {char.activity_score}){call_marker}')
        self.character_spinner.values = spinner_values
        self.character_spinner.text = spinner_values[0]
    
    def load_messages(self):
        self.message_list.clear_widgets()
        
        if not self.session_id:
            empty_label = Label(
                text='开始新的对话',
                font_size=dp(16),
                font_name=FONT_NAME,
                color=COLORS['text_hint'],
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(200)
            )
            empty_label.bind(size=empty_label.setter('text_size'))
            self.message_list.add_widget(empty_label)
            return
        
        location_filter = self.current_view_location if self.is_viewing_other_location else None
        messages = self.db.get_chat_messages_by_session(self.session_id, limit=100, location=location_filter)
        
        if not messages:
            empty_label = Label(
                text='开始新的对话',
                font_size=dp(16),
                font_name=FONT_NAME,
                color=COLORS['text_hint'],
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(200)
            )
            empty_label.bind(size=empty_label.setter('text_size'))
            self.message_list.add_widget(empty_label)
            return
        
        for msg in messages:
            if msg.is_time_separator:
                continue
            
            character_name = msg.character_name or '你'
            avatar_path = msg.avatar_path
            background_image_path = None
            
            if msg.character_id and msg.character_id in self.character_map:
                char = self.character_map[msg.character_id]
                character_name = char.name
                if char.avatar_path and os.path.exists(char.avatar_path):
                    avatar_path = char.avatar_path
                
                if msg.background_image_id:
                    bg_images = self.db.get_background_images(char.id)
                    bg_image = next((img for img in bg_images if img.id == msg.background_image_id), None)
                    if bg_image and bg_image.image_path and os.path.exists(bg_image.image_path):
                        background_image_path = bg_image.image_path
            
            segments = []
            if msg.segments:
                try:
                    parsed_segments = json.loads(msg.segments)
                    if isinstance(parsed_segments, list):
                        segments = parsed_segments
                except:
                    pass
            
            if not segments:
                if msg.action:
                    segments.append({'type': 'action', 'content': msg.action})
                if msg.content:
                    segments.append({'type': 'speech', 'content': msg.content})
            
            if segments:
                if msg.character_id is None:
                    self.add_user_message('你', segments, msg.id)
                else:
                    self.add_character_message(character_name, avatar_path, segments, background_image_path, msg.id, msg.character_id)
    
    def add_character_message(self, character_name, avatar_path, segments, background_image_path=None, message_id=None, character_id=None):
        if background_image_path:
            self.set_character_background(background_image_path)
        
        is_on_call = False
        if character_id:
            is_on_call = self.db.is_character_on_call(character_id)
        
        msg_group = CharacterMessageGroup(
            character_name, 
            avatar_path, 
            segments, 
            message_id=message_id, 
            on_rewind_callback=self.on_rewind_message,
            character_id=character_id,
            on_avatar_click=self.on_avatar_click,
            is_on_call=is_on_call
        )
        self.message_list.add_widget(msg_group)
        
        Clock.schedule_once(lambda dt: self.scroll_view.scroll_to(msg_group), 0.1)
    
    def add_user_message(self, user_name, segments, message_id=None):
        msg_group = UserMessageGroup(user_name, segments, message_id=message_id, on_rewind_callback=self.on_rewind_message)
        self.message_list.add_widget(msg_group)
        
        Clock.schedule_once(lambda dt: self.scroll_view.scroll_to(msg_group), 0.1)
    
    def on_rewind_message(self, message_id):
        world = self.db.get_world(self.world_id)
        if self.is_viewing_other_location:
            current_location = self.current_view_location
        else:
            current_location = world.user_location if world and world.user_location else None
        
        chat_messages = self.db.get_chat_messages_by_session(self.session_id, limit=100, location=current_location)
        
        selected_index = None
        for i, msg in enumerate(chat_messages):
            if msg.id == message_id:
                selected_index = i
                break
        
        if selected_index is None:
            self._show_toast('未找到该消息')
            return
        
        self._perform_rewind(chat_messages, selected_index)
    
    def _perform_rewind(self, chat_messages, selected_index):
        try:
            target_segment = (selected_index // 7) + 1
            
            max_segment = self.db.get_max_segment(self.world_id)
            
            if max_segment >= target_segment:
                self.db.delete_memories_from_segment(self.world_id, target_segment)
            
            selected_message = chat_messages[selected_index]
            
            world = self.db.get_world(self.world_id)
            if self.is_viewing_other_location:
                current_location = self.current_view_location
            else:
                current_location = world.user_location if world and world.user_location else None
            
            self.db.delete_chat_messages_after(self.session_id, selected_message.id, current_location)
            
            self.load_messages()
            self._show_toast('已回溯到该消息')
        except Exception as e:
            self._show_toast(f'回溯失败: {str(e)}')
    
    def send_message(self, instance):
        if self.is_processing:
            return
        
        text = self.message_input.text.strip()
        if not text:
            return
        
        self.message_input.text = ''
        self.is_processing = True
        self.message_input.disabled = True
        
        world = self.db.get_world(self.world_id)
        user_location = world.user_location if world else None
        
        self.processing_thread = ProcessingThread(
            self.dialogue_manager, self.world_id, self.session_id, text, user_location
        )
        self.processing_thread.response_ready = self.handle_ai_response
        self.processing_thread.start()
    
    def handle_ai_response(self, responses, timeline_events):
        self.characters = self.db.get_characters_by_world(self.world_id)
        self.character_map = {c.id: c for c in self.characters}
        self.update_speaker_list()
        world = self.db.get_world(self.world_id)
        self.update_time_display(world)
        self.load_messages()
        self.is_processing = False
        self.message_input.disabled = False
    
    def listen_mode(self, instance):
        if self.is_processing or not self.dialogue_manager:
            return
        
        self.is_processing = True
        self.message_input.disabled = True
        
        world = self.db.get_world(self.world_id)
        user_location = world.user_location if world else None
        
        selected_character = None
        spinner_text = self.character_spinner.text
        if spinner_text:
            if spinner_text.startswith('自动选择'):
                selected_character = None
            else:
                if ' (活跃度:' in spinner_text:
                    selected_character = spinner_text.split(' (活跃度:')[0]
                else:
                    selected_character = spinner_text
        
        self.listen_thread = ListenThread(
            self.dialogue_manager, self.world_id, self.session_id, user_location, selected_character
        )
        self.listen_thread.response_ready = self.handle_ai_response
        self.listen_thread.start()
    
    def open_script_settings(self, instance):
        if hasattr(self.manager, 'script_settings_screen'):
            self.manager.script_settings_screen.set_world(self.world_id)
            self.manager.current = 'script_settings'
    
    def open_location_change(self, instance):
        if hasattr(self.manager, 'location_change_screen'):
            self.manager.location_change_screen.set_world(self.world_id)
            self.manager.current = 'location_change'
    
    def open_user_health(self, instance):
        if hasattr(self.manager, 'user_health_screen'):
            self.manager.user_health_screen.set_world(self.world_id)
            self.manager.current = 'user_health'
    
    def open_call_manager(self, instance):
        if hasattr(self.manager, 'call_manager_screen'):
            self.manager.call_manager_screen.set_world(self.world_id)
            self.manager.current = 'call_manager'
    
    def update_call_button_state(self):
        if hasattr(self, 'call_btn') and self.world_id:
            has_pending = self.db.has_pending_call_requests(self.world_id)
            if has_pending:
                self.call_btn.background_color = COLORS['call_alert']
                self.call_btn.text = 'C!'
            else:
                self.call_btn.background_color = COLORS['call_orange']
                self.call_btn.text = 'C'
        
        if hasattr(self, 'menu_btn') and self.world_id:
            has_pending = self.db.has_pending_call_requests(self.world_id)
            if has_pending:
                self.menu_btn.background_color = COLORS['call_alert']
                self.menu_btn.text = '!'
            else:
                self.menu_btn.background_color = COLORS['primary']
                self.menu_btn.text = '菜单'
    
    def on_avatar_click(self, character_id):
        if hasattr(self.manager, 'health_screen'):
            self.manager.health_screen.set_character(character_id)
            self.manager.current = 'health'
    
    def load_view_locations(self):
        locations = self.db.get_locations(self.world_id)
        
        if locations:
            primary_locations = self.db.get_primary_locations(self.world_id)
            location_names = []
            
            for primary_loc in primary_locations:
                sub_locations = self.db.get_sub_locations(primary_loc.id)
                if sub_locations:
                    location_names.append(f"【{primary_loc.name}】")
                    for sub_loc in sub_locations:
                        location_names.append(f"  └ {sub_loc.name}")
                else:
                    location_names.append(f"【{primary_loc.name}】")
            
            self.view_spinner.values = location_names
            
            world = self.db.get_world(self.world_id)
            if world and world.user_location:
                self.view_spinner.text = world.user_location
                self.current_view_location = None
                self.is_viewing_other_location = False
        else:
            self.view_spinner.values = ['请先添加位置']
            self.view_spinner.text = '请先添加位置'
    
    def on_view_location_changed(self, spinner, location):
        if not location or location == '请先添加位置':
            return
        
        world = self.db.get_world(self.world_id)
        if not world:
            return
        
        clean_location = location.strip()
        if clean_location.startswith('└'):
            clean_location = clean_location[1:].strip()
        if clean_location.startswith('【') and clean_location.endswith('】'):
            clean_location = clean_location[1:-1]
        
        if clean_location == world.user_location:
            self.current_view_location = None
            self.is_viewing_other_location = False
        else:
            self.current_view_location = clean_location
            self.is_viewing_other_location = True
        
        self.update_speaker_list()
        self.set_location_background(clean_location)
        self.load_messages()
    
    def set_location_background(self, location_name):
        if not location_name:
            self.clear_background()
            return
        
        locations = self.db.get_locations(self.world_id)
        location = next((loc for loc in locations if loc.name == location_name), None)
        
        if not location:
            self.clear_background()
            return
        
        background_path = None
        
        if location.image_path and os.path.exists(location.image_path):
            background_path = location.image_path
        elif location.parent_location_id:
            parent_location = next((loc for loc in locations if loc.id == location.parent_location_id), None)
            if parent_location and parent_location.image_path and os.path.exists(parent_location.image_path):
                background_path = parent_location.image_path
        
        if background_path:
            self.env_background.source = background_path
        else:
            self.clear_background()
    
    def set_character_background(self, image_path):
        if image_path and os.path.exists(image_path):
            self.character_background.source = image_path
            self.character_background_container.opacity = 1
    
    def clear_background(self):
        self.env_background.source = ''
        self.character_background.source = ''
        self.character_background_container.opacity = 0
    
    def restart_from_beginning(self, instance):
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(16))
        
        title = Label(
            text='从头开始',
            font_name=FONT_NAME,
            font_size=dp(18),
            bold=True,
            color=COLORS['text'],
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(title)
        
        message = Label(
            text='确定要删除所有内容吗？\n\n这将删除：\n• 所有聊天记录\n• 世界记忆\n• 角色记忆\n\n此操作不可恢复！',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text_secondary'],
            halign='left',
            valign='top',
            size_hint_y=None,
            height=dp(160)
        )
        message.bind(size=message.setter('text_size'))
        content.add_widget(message)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(12))
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(14),
            background_normal='',
            background_color=COLORS['surface'],
            color=COLORS['text']
        )
        
        confirm_btn = Button(
            text='确定',
            font_name=FONT_NAME,
            font_size=dp(14),
            background_normal='',
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1)
        )
        
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(confirm_btn)
        content.add_widget(btn_row)
        
        popup = Popup(
            content=content,
            size_hint=(0.85, None),
            height=dp(320),
            auto_dismiss=False,
            background='',
            separator_color=(0, 0, 0, 0)
        )
        
        cancel_btn.bind(on_press=popup.dismiss)
        confirm_btn.bind(on_press=lambda x: self._perform_restart(popup))
        
        popup.open()
    
    def _perform_restart(self, popup):
        popup.dismiss()
        try:
            self.db.delete_all_memories(self.world_id)
            self.db.delete_all_chat_messages(self.session_id)
            
            self.load_messages()
            
            self._show_toast('已重置，可以重新开始对话')
        except Exception as e:
            self._show_toast(f'重置失败: {str(e)}')
    
    def _show_toast(self, message):
        toast = Label(
            text=message,
            font_name=FONT_NAME,
            font_size=dp(14),
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            padding=[dp(20), dp(12)],
            halign='center'
        )
        toast.bind(size=toast.setter('text_size'))
        toast.texture_update()
        toast.width = toast.texture_size[0] + dp(40)
        toast.height = toast.texture_size[1] + dp(24)
        
        with toast.canvas.before:
            Color(0.2, 0.2, 0.2, 0.9)
            toast._bg = RoundedRectangle(pos=toast.pos, size=toast.size, radius=[dp(8)])
        toast.bind(pos=lambda i, v: setattr(toast._bg, 'pos', v), 
                   size=lambda i, v: setattr(toast._bg, 'size', v))
        
        self.root_layout.add_widget(toast)
        
        from kivy.animation import Animation
        anim = Animation(opacity=0, duration=0.3) + Animation(opacity=0, duration=1.7)
        anim.bind(on_complete=lambda *args: self.root_layout.remove_widget(toast))
        anim.start(toast)
    
    def open_menu(self, instance):
        if hasattr(self.manager, 'chat_menu_screen'):
            self.manager.chat_menu_screen.set_world(self.world_id)
            self.manager.current = 'chat_menu'
    
    def go_back(self, instance):
        self.manager.current = 'world_list'


class ProcessingThread(Thread):
    def __init__(self, dialogue_manager, world_id, session_id, user_message, user_location=None):
        super().__init__()
        self.dialogue_manager = dialogue_manager
        self.world_id = world_id
        self.session_id = session_id
        self.user_message = user_message
        self.user_location = user_location
        self.response_ready = None
    
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            responses, timeline_events, _ = loop.run_until_complete(
                self.dialogue_manager.process_user_message(
                    self.world_id, self.session_id, self.user_message, location=self.user_location
                )
            )
            if self.response_ready:
                Clock.schedule_once(lambda dt: self.response_ready(responses, timeline_events), 0)
        except Exception as e:
            print(f"处理消息时发生错误: {e}")
            import traceback
            traceback.print_exc()
            if self.response_ready:
                Clock.schedule_once(lambda dt: self.response_ready([], []), 0)
        finally:
            loop.close()


class ListenThread(Thread):
    def __init__(self, dialogue_manager, world_id, session_id, user_location=None, selected_character=None):
        super().__init__()
        self.dialogue_manager = dialogue_manager
        self.world_id = world_id
        self.session_id = session_id
        self.user_location = user_location
        self.selected_character = selected_character
        self.response_ready = None
    
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            response = loop.run_until_complete(
                self.dialogue_manager.let_character_speak(
                    self.world_id, self.session_id, location=self.user_location, selected_character=self.selected_character
                )
            )
            if response and self.response_ready:
                responses = [response] if isinstance(response, dict) else response
                Clock.schedule_once(lambda dt: self.response_ready(responses, []), 0)
        except Exception as e:
            print(f"让角色说话时发生错误: {e}")
            import traceback
            traceback.print_exc()
            if self.response_ready:
                Clock.schedule_once(lambda dt: self.response_ready([], []), 0)
        finally:
            loop.close()


class ScriptSettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.is_processing = False
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_border = RoundedRectangle(pos=header.pos, size=header.size)
            Color(1, 1, 1, 0.95)
            self._header_bg = RoundedRectangle(
                pos=(header.pos[0] + dp(1), header.pos[1] + dp(1)),
                size=(header.size[0] - dp(2), header.size[1] - dp(2))
            )
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='< 返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(70),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='剧本设置',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(70)))
        
        self.root_layout.add_widget(header)
        
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(12), padding=[dp(16), dp(12), dp(16), dp(12)])
        content.bind(minimum_height=content.setter('height'))
        
        enable_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(12))
        enable_label = Label(
            text='启用剧本模式',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            halign='left',
            size_hint_x=0.7
        )
        enable_label.bind(size=enable_label.setter('text_size'))
        
        self.enable_btn = Button(
            text='关',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_x=0.3,
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        self.enable_btn.bind(on_press=self.toggle_script)
        enable_row.add_widget(enable_label)
        enable_row.add_widget(self.enable_btn)
        content.add_widget(enable_row)
        
        outline_label = Label(
            text='剧本大纲 (粗略描述):',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        outline_label.bind(size=outline_label.setter('text_size'))
        content.add_widget(outline_label)
        
        self.outline_input = TextInput(
            hint_text='描述剧本的粗略大纲，包括主要情节、关键事件、角色关系等...',
            font_name=FONT_NAME,
            font_size=dp(14),
            multiline=True,
            size_hint_y=None,
            height=dp(120),
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1)
        )
        content.add_widget(self.outline_input)
        
        generate_btn = Button(
            text='生成剧本 (API2扩写)',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        generate_btn.bind(on_press=self.generate_script)
        content.add_widget(generate_btn)
        
        self.progress_label = Label(
            text='当前进度: 未启用',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text_secondary'],
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        self.progress_label.bind(size=self.progress_label.setter('text_size'))
        content.add_widget(self.progress_label)
        
        chapter_label = Label(
            text='当前章节内容:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        chapter_label.bind(size=chapter_label.setter('text_size'))
        content.add_widget(chapter_label)
        
        self.chapter_display = TextInput(
            text='暂无章节内容',
            font_name=FONT_NAME,
            font_size=dp(13),
            multiline=True,
            readonly=True,
            size_hint_y=None,
            height=dp(180),
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1)
        )
        content.add_widget(self.chapter_display)
        
        nav_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(12))
        
        prev_btn = Button(
            text='上一章',
            font_name=FONT_NAME,
            font_size=dp(14),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        prev_btn.bind(on_press=self.prev_chapter)
        nav_row.add_widget(prev_btn)
        
        next_btn = Button(
            text='下一章',
            font_name=FONT_NAME,
            font_size=dp(14),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        next_btn.bind(on_press=self.next_chapter)
        nav_row.add_widget(next_btn)
        
        content.add_widget(nav_row)
        
        scroll.add_widget(content)
        self.root_layout.add_widget(scroll)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_border.pos = instance.pos
        self._header_border.size = instance.size
        self._header_bg.pos = (instance.pos[0] + dp(1), instance.pos[1] + dp(1))
        self._header_bg.size = (instance.size[0] - dp(2), instance.size[1] - dp(2))
    
    def set_world(self, world_id):
        self.world_id = world_id
        world = self.db.get_world(world_id)
        if world:
            self.title_label.text = f'剧本设置 - {world.name}'
            
            if world.script_outline:
                self.outline_input.text = world.script_outline
            
            if world.script_enabled:
                self.enable_btn.text = '开'
                self.enable_btn.background_color = COLORS['primary']
            else:
                self.enable_btn.text = '关'
                self.enable_btn.background_color = COLORS['text_hint']
            
            self.update_chapter_display()
    
    def update_chapter_display(self):
        world = self.db.get_world(self.world_id)
        if world and world.script_enabled and world.script_chapters:
            try:
                chapters = world.script_chapters
                if isinstance(chapters, str):
                    chapters = json.loads(chapters)
                current = world.current_chapter_index or 0
                total = len(chapters)
                
                if current < len(chapters):
                    chapter = chapters[current]
                    title = chapter.get('title', '未命名')
                    description = chapter.get('description', '无描述')
                    key_events = chapter.get('key_events', [])
                    estimated_rounds = chapter.get('estimated_rounds', 0)
                    
                    events_text = '\n'.join([f'  - {e}' for e in key_events]) if key_events else '  无'
                    
                    self.chapter_display.text = f'【{title}】\n\n{description}\n\n关键事件:\n{events_text}\n\n预计对话轮数: {estimated_rounds}'
                    self.progress_label.text = f'当前进度: 第{current + 1}章 / 共{total}章'
                else:
                    self.chapter_display.text = '章节索引超出范围'
                    self.progress_label.text = f'当前进度: 第{current + 1}章 / 共{total}章'
            except Exception as e:
                self.chapter_display.text = f'解析错误: {str(e)}'
                self.progress_label.text = '当前进度: 解析错误'
        else:
            self.chapter_display.text = '暂无章节内容\n\n请先输入剧本大纲并点击"生成剧本"'
            self.progress_label.text = '当前进度: 未启用'
    
    def toggle_script(self, instance):
        world = self.db.get_world(self.world_id)
        if world:
            new_enabled = not world.script_enabled
            self.db.update_world(self.world_id, script_enabled=new_enabled)
            
            if new_enabled:
                instance.text = '开'
                instance.background_color = COLORS['primary']
            else:
                instance.text = '关'
                instance.background_color = COLORS['text_hint']
            
            self.update_chapter_display()
    
    def generate_script(self, instance):
        if self.is_processing:
            return
        
        outline = self.outline_input.text.strip()
        if not outline:
            popup = create_message_popup('请输入剧本大纲')
            popup.open()
            return
        
        self.is_processing = True
        popup = create_message_popup('正在生成剧本...')
        popup.open()
        self._generating_popup = popup
        
        self.generate_thread = ScriptGenerateThread(self.db, self.world_id, outline)
        self.generate_thread.on_complete = self.on_generate_complete
        self.generate_thread.start()
    
    def on_generate_complete(self, success, message, chapters):
        if hasattr(self, '_generating_popup'):
            self._generating_popup.dismiss()
        
        self.is_processing = False
        
        if success:
            self.update_chapter_display()
            self.enable_btn.text = '开'
            self.enable_btn.background_color = COLORS['primary']
            popup = create_message_popup(message)
            popup.open()
        else:
            popup = create_message_popup(message)
            popup.open()
    
    def prev_chapter(self, instance):
        world = self.db.get_world(self.world_id)
        if not world or not world.script_enabled or not world.script_chapters:
            popup = create_message_popup('请先生成剧本')
            popup.open()
            return
        
        try:
            chapters = world.script_chapters
            if isinstance(chapters, str):
                chapters = json.loads(chapters)
            
            current = world.current_chapter_index or 0
            if current <= 0:
                popup = create_message_popup('已经是第一章')
                popup.open()
                return
            
            self.db.update_world(self.world_id, current_chapter_index=current - 1)
            self.update_chapter_display()
        except:
            popup = create_message_popup('章节解析错误')
            popup.open()
    
    def next_chapter(self, instance):
        world = self.db.get_world(self.world_id)
        if not world or not world.script_enabled or not world.script_chapters:
            popup = create_message_popup('请先生成剧本')
            popup.open()
            return
        
        try:
            chapters = world.script_chapters
            if isinstance(chapters, str):
                chapters = json.loads(chapters)
            
            current = world.current_chapter_index or 0
            if current + 1 >= len(chapters):
                popup = create_message_popup('已经是最后一章')
                popup.open()
                return
            
            self.db.update_world(self.world_id, current_chapter_index=current + 1)
            self.update_chapter_display()
        except:
            popup = create_message_popup('章节解析错误')
            popup.open()
    
    def go_back(self, instance):
        self.manager.current = 'chat'


class ScriptGenerateThread(Thread):
    def __init__(self, db, world_id, outline):
        super().__init__()
        self.db = db
        self.world_id = world_id
        self.outline = outline
        self.on_complete = None
    
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            api_config = self.db.get_api_config()
            if not api_config or not api_config.api2_key:
                if self.on_complete:
                    Clock.schedule_once(lambda dt: self.on_complete(False, '请先配置API2密钥', []), 0)
                return
            
            world = self.db.get_world(self.world_id)
            characters = self.db.get_characters_by_world(self.world_id)
            
            client = DeepSeekClient(api_key=api_config.api2_key)
            
            character_data = []
            for char in characters:
                character_data.append({
                    'name': char.name,
                    'description': char.description or "",
                    'background': char.background or ""
                })
            
            result = loop.run_until_complete(client.expand_script(
                script_outline=self.outline,
                world_context=world.background or "",
                characters=character_data,
                model=api_config.api2_model or "deepseek-chat"
            ))
            
            loop.run_until_complete(client.close())
            
            chapters = result.get('chapters', [])
            if chapters:
                chapters_json = json.dumps(chapters, ensure_ascii=False)
                self.db.update_world(
                    self.world_id,
                    script_outline=self.outline,
                    script_chapters=chapters_json,
                    current_chapter_index=0,
                    script_enabled=True
                )
                
                message = f'成功生成 {len(chapters)} 个篇章'
                if self.on_complete:
                    Clock.schedule_once(lambda dt: self.on_complete(True, message, chapters), 0)
            else:
                if self.on_complete:
                    Clock.schedule_once(lambda dt: self.on_complete(False, '剧本生成失败，未返回任何篇章', []), 0)
        
        except Exception as e:
            if self.on_complete:
                Clock.schedule_once(lambda dt: self.on_complete(False, f'生成剧本时发生错误: {str(e)}', []), 0)
        finally:
            loop.close()


class LocationChangeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_border = RoundedRectangle(pos=header.pos, size=header.size)
            Color(1, 1, 1, 0.95)
            self._header_bg = RoundedRectangle(
                pos=(header.pos[0] + dp(1), header.pos[1] + dp(1)),
                size=(header.size[0] - dp(2), header.size[1] - dp(2))
            )
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='< 返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(70),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='位置转换',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(70)))
        
        self.root_layout.add_widget(header)
        
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(12), padding=[dp(16), dp(12), dp(16), dp(12)])
        content.bind(minimum_height=content.setter('height'))
        
        char_label = Label(
            text='选择移动角色:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        char_label.bind(size=char_label.setter('text_size'))
        content.add_widget(char_label)
        
        self.char_spinner = ChineseSpinner(
            text='请选择角色',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            values=[],
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1),
            color=COLORS['text']
        )
        content.add_widget(self.char_spinner)
        
        primary_label = Label(
            text='选择一级位置:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        primary_label.bind(size=primary_label.setter('text_size'))
        content.add_widget(primary_label)
        
        self.primary_spinner = ChineseSpinner(
            text='请选择一级位置',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            values=[],
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1),
            color=COLORS['text']
        )
        self.primary_spinner.bind(text=self.on_primary_location_changed)
        content.add_widget(self.primary_spinner)
        
        secondary_label = Label(
            text='选择二级位置:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        secondary_label.bind(size=secondary_label.setter('text_size'))
        content.add_widget(secondary_label)
        
        self.secondary_spinner = ChineseSpinner(
            text='请选择二级位置',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            values=[],
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1),
            color=COLORS['text']
        )
        content.add_widget(self.secondary_spinner)
        
        transport_label = Label(
            text='选择交通工具:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        transport_label.bind(size=transport_label.setter('text_size'))
        content.add_widget(transport_label)
        
        self.transport_spinner = ChineseSpinner(
            text='请选择交通工具',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            values=[],
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1),
            color=COLORS['text']
        )
        content.add_widget(self.transport_spinner)
        
        self.info_label = Label(
            text='',
            font_name=FONT_NAME,
            font_size=dp(13),
            color=COLORS['text_secondary'],
            halign='left',
            size_hint_y=None,
            height=dp(50)
        )
        self.info_label.bind(size=self.info_label.setter('text_size'))
        content.add_widget(self.info_label)
        
        confirm_btn = Button(
            text='确认移动',
            font_name=FONT_NAME,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        confirm_btn.bind(on_press=self.confirm_move)
        content.add_widget(confirm_btn)
        
        scroll.add_widget(content)
        self.root_layout.add_widget(scroll)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_border.pos = instance.pos
        self._header_border.size = instance.size
        self._header_bg.pos = (instance.pos[0] + dp(1), instance.pos[1] + dp(1))
        self._header_bg.size = (instance.size[0] - dp(2), instance.size[1] - dp(2))
    
    def set_world(self, world_id):
        self.world_id = world_id
        self.load_data()
    
    def load_data(self):
        if not self.world_id:
            return
        
        world = self.db.get_world(self.world_id)
        characters = self.db.get_characters_by_world(self.world_id)
        primary_locations = self.db.get_primary_locations(self.world_id)
        transport_modes = self.db.get_transport_modes(self.world_id)
        
        char_values = [f"用户 (您) - {world.user_location or '未知'}"]
        self.char_data = {'user': None}
        for char in characters:
            char_values.append(f"{char.name} - {char.location or '未知'}")
            self.char_data[char.name] = char
        self.char_spinner.values = char_values
        
        self.primary_locations = {loc.name: loc for loc in primary_locations}
        self.primary_spinner.values = list(self.primary_locations.keys())
        
        self.transport_modes = {f"{t.name} (速度: {t.speed}m/s)": t for t in transport_modes}
        self.transport_spinner.values = list(self.transport_modes.keys())
        
        self.world = world
    
    def on_primary_location_changed(self, spinner, text):
        if not text or text == '请选择一级位置':
            self.secondary_spinner.values = []
            return
        
        primary_loc = self.primary_locations.get(text)
        if primary_loc:
            sub_locations = self.db.get_sub_locations(primary_loc.id)
            if sub_locations:
                self.secondary_spinner.values = [loc.name for loc in sub_locations]
            else:
                self.secondary_spinner.values = [text]
        else:
            self.secondary_spinner.values = [text]
    
    def confirm_move(self, instance):
        char_text = self.char_spinner.text
        primary_text = self.primary_spinner.text
        secondary_text = self.secondary_spinner.text
        transport_text = self.transport_spinner.text
        
        if char_text == '请选择角色':
            self.info_label.text = '请选择要移动的角色'
            return
        
        if primary_text == '请选择一级位置':
            self.info_label.text = '请选择目标位置'
            return
        
        if transport_text == '请选择交通工具':
            self.info_label.text = '请选择交通工具'
            return
        
        target_location = secondary_text if secondary_text and secondary_text != '请选择二级位置' else primary_text
        
        if '用户' in char_text:
            self.handle_user_location_change(target_location, transport_text)
        else:
            char_name = char_text.split(' - ')[0]
            char = self.char_data.get(char_name)
            if char:
                self.handle_character_location_change(char.id, target_location, transport_text)
    
    def handle_user_location_change(self, new_location, transport_text):
        world = self.db.get_world(self.world_id)
        current_location = world.user_location
        
        if current_location == new_location:
            self.info_label.text = '您已经在该位置了'
            return
        
        all_locations = self.db.get_locations(self.world_id)
        from_loc = next((loc for loc in all_locations if loc.name == current_location), None)
        to_loc = next((loc for loc in all_locations if loc.name == new_location), None)
        
        if not from_loc or not to_loc:
            self.info_label.text = '位置信息不完整'
            return
        
        dx = to_loc.x - from_loc.x
        dy = to_loc.y - from_loc.y
        distance_hm = (dx ** 2 + dy ** 2) ** 0.5
        distance_m = distance_hm * 100
        
        transport = self.transport_modes.get(transport_text)
        speed = transport.speed if transport else 1
        travel_time = int(distance_m / speed)
        if travel_time < 10:
            travel_time = 10
        
        departure_date = world.current_date
        departure_time = world.current_time
        arrival_date, arrival_time = self.calculate_arrival_time(departure_date, departure_time, travel_time)
        
        self.db.create_location_transfer(
            world_id=self.world_id,
            character_id=None,
            from_location=current_location,
            to_location=new_location,
            departure_date=departure_date,
            departure_time=departure_time,
            arrival_date=arrival_date,
            arrival_time=arrival_time
        )
        
        on_road_location = f"从{current_location}到{new_location}的路上"
        self.db.update_world(self.world_id, user_location=on_road_location)
        
        self.info_label.text = f'移动中...\n距离: {distance_m:.0f}米\n预计到达: {arrival_date} {arrival_time}'
        
        Clock.schedule_once(lambda dt: self._complete_move(new_location, arrival_date, arrival_time), 2)
    
    def handle_character_location_change(self, character_id, new_location, transport_text):
        character = self.db.get_character(character_id)
        if not character:
            self.info_label.text = '角色不存在'
            return
        
        current_location = character.location
        
        if current_location == new_location:
            self.info_label.text = f'{character.name}已经在该位置了'
            return
        
        all_locations = self.db.get_locations(self.world_id)
        from_loc = next((loc for loc in all_locations if loc.name == current_location), None)
        to_loc = next((loc for loc in all_locations if loc.name == new_location), None)
        
        if not from_loc or not to_loc:
            self.info_label.text = '位置信息不完整'
            return
        
        dx = to_loc.x - from_loc.x
        dy = to_loc.y - from_loc.y
        distance_hm = (dx ** 2 + dy ** 2) ** 0.5
        distance_m = distance_hm * 100
        
        transport = self.transport_modes.get(transport_text)
        speed = transport.speed if transport else 1
        travel_time = int(distance_m / speed)
        if travel_time < 10:
            travel_time = 10
        
        world = self.db.get_world(self.world_id)
        departure_date = world.current_date
        departure_time = world.current_time
        arrival_date, arrival_time = self.calculate_arrival_time(departure_date, departure_time, travel_time)
        
        self.db.create_location_transfer(
            world_id=self.world_id,
            character_id=character_id,
            from_location=current_location,
            to_location=new_location,
            departure_date=departure_date,
            departure_time=departure_time,
            arrival_date=arrival_date,
            arrival_time=arrival_time
        )
        
        on_road_location = f"从{current_location}到{new_location}的路上"
        self.db.update_character(character_id, location=on_road_location)
        
        self.info_label.text = f'{character.name}移动中...\n距离: {distance_m:.0f}米\n预计到达: {arrival_date} {arrival_time}'
        
        Clock.schedule_once(lambda dt: self._complete_character_move(character_id, new_location), 2)
    
    def _complete_move(self, new_location, arrival_date, arrival_time):
        self.db.update_world(self.world_id, user_location=new_location)
        self.info_label.text = f'已到达: {new_location}\n时间: {arrival_date} {arrival_time}'
        self.load_data()
    
    def _complete_character_move(self, character_id, new_location):
        self.db.update_character(character_id, location=new_location)
        character = self.db.get_character(character_id)
        self.info_label.text = f'{character.name}已到达: {new_location}'
        self.load_data()
    
    def calculate_arrival_time(self, date, time, travel_seconds):
        time_parts = time.split(':')
        hours = int(time_parts[0])
        minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
        
        total_minutes = hours * 60 + minutes + travel_seconds // 60
        new_hours = (total_minutes // 60) % 24
        new_minutes = total_minutes % 60
        
        arrival_time = f"{new_hours:02d}:{new_minutes:02d}"
        
        days_passed = total_minutes // (24 * 60)
        if days_passed > 0:
            date_parts = date.split('-')
            year = int(date_parts[0])
            month = int(date_parts[1])
            day = int(date_parts[2])
            day += days_passed
            arrival_date = f"{year}-{month:02d}-{day:02d}"
        else:
            arrival_date = date
        
        return arrival_date, arrival_time
    
    def go_back(self, instance):
        self.manager.current = 'chat'


class LocationListScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='位置管理',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.location_list = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(16), dp(8), dp(16), dp(8)]
        )
        self.location_list.bind(minimum_height=self.location_list.setter('height'))
        
        self.scroll_view.add_widget(self.location_list)
        self.root_layout.add_widget(self.scroll_view)
        
        transport_btn_container = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(16), dp(4), dp(16), dp(4)]
        )
        
        transport_btn = Button(
            text='🚗 交通工具管理',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        transport_btn.bind(on_press=self.open_transport_manage)
        transport_btn_container.add_widget(transport_btn)
        self.root_layout.add_widget(transport_btn_container)
        
        add_btn_container = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        with add_btn_container.canvas.before:
            Color(*COLORS['surface'])
            self._add_btn_bg = RoundedRectangle(pos=add_btn_container.pos, size=add_btn_container.size)
        add_btn_container.bind(pos=self._update_add_btn_bg, size=self._update_add_btn_bg)
        
        add_btn = Button(
            text='+ 添加位置',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        add_btn.bind(on_press=self.add_location)
        add_btn_container.add_widget(add_btn)
        self.root_layout.add_widget(add_btn_container)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_add_btn_bg(self, instance, value):
        self._add_btn_bg.pos = instance.pos
        self._add_btn_bg.size = instance.size
    
    def set_world(self, world_id):
        self.world_id = world_id
        self.load_locations()
    
    def load_locations(self):
        self.location_list.clear_widgets()
        
        if not self.world_id:
            return
        
        locations = self.db.get_primary_locations(self.world_id)
        
        if not locations:
            empty_label = Label(
                text='暂无位置\n点击下方按钮创建',
                font_size=dp(14),
                font_name=FONT_NAME,
                color=COLORS['text_hint'],
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(200)
            )
            empty_label.bind(size=empty_label.setter('text_size'))
            self.location_list.add_widget(empty_label)
        else:
            for location in locations:
                location_card = LocationCard(location, on_edit=self.edit_location, on_delete=self.delete_location)
                self.location_list.add_widget(location_card)
    
    def on_enter(self):
        self.load_locations()
    
    def add_location(self, instance):
        if hasattr(self.manager, 'location_edit_screen'):
            self.manager.location_edit_screen.set_location(self.world_id, None)
            self.manager.current = 'location_edit'
    
    def edit_location(self, location):
        if hasattr(self.manager, 'location_edit_screen'):
            self.manager.location_edit_screen.set_location(self.world_id, location.id)
            self.manager.current = 'location_edit'
    
    def delete_location(self, location):
        popup = create_confirm_popup(
            f'确定要删除"{location.name}"吗？\n此操作不可恢复',
            lambda p: self._do_delete_location(location.id, p),
            confirm_text='删除',
            is_danger=True
        )
        popup.open()
    
    def _do_delete_location(self, location_id, popup):
        self.db.delete_location(location_id)
        popup.dismiss()
        self.load_locations()
    
    def open_transport_manage(self, instance):
        if hasattr(self.manager, 'transport_screen'):
            self.manager.transport_screen.set_world(self.world_id)
            self.manager.current = 'transport'
    
    def go_back(self, instance):
        self.manager.current = 'world_edit'


class LocationCard(BoxLayout):
    def __init__(self, location, on_edit=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.location = location
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(60)
        self.padding = [dp(16), dp(12)]
        
        self._long_press_triggered = False
        self._long_press_event = None
        
        with self.canvas.before:
            Color(*COLORS['surface'])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        inner = FloatLayout()
        
        name_label = Label(
            text=location.name,
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            valign='middle',
            pos_hint={'x': 0, 'center_y': 0.5},
            size_hint_x=0.7
        )
        name_label.bind(size=name_label.setter('text_size'))
        inner.add_widget(name_label)
        
        edit_label = Label(
            text='编辑 >',
            font_size=dp(12),
            font_name=FONT_NAME,
            color=COLORS['primary'],
            halign='right',
            valign='middle',
            pos_hint={'right': 1, 'center_y': 0.5},
            size_hint_x=0.3
        )
        edit_label.bind(size=edit_label.setter('text_size'))
        inner.add_widget(edit_label)
        
        self.add_widget(inner)
    
    def _update_bg(self, instance, value):
        self._bg.pos = instance.pos
        self._bg.size = instance.size
    
    def _trigger_long_press(self, dt):
        self._long_press_triggered = True
        if self.on_delete:
            self.on_delete(self.location)
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._long_press_triggered = False
            self._long_press_event = Clock.schedule_once(self._trigger_long_press, 0.5)
            return True
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if self._long_press_event:
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        
        if self.collide_point(*touch.pos) and not self._long_press_triggered:
            if self.on_edit:
                self.on_edit(self.location)
            return True
        return super().on_touch_up(touch)
    
    def on_touch_move(self, touch):
        if self._long_press_event and not self.collide_point(*touch.pos):
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        return super().on_touch_move(touch)


class TransportScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.selected_transport_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='交通工具管理',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.transport_list = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(16), dp(8), dp(16), dp(8)]
        )
        self.transport_list.bind(minimum_height=self.transport_list.setter('height'))
        
        self.scroll_view.add_widget(self.transport_list)
        self.root_layout.add_widget(self.scroll_view)
        
        btn_container = BoxLayout(
            size_hint_y=None,
            height=dp(120),
            padding=[dp(16), dp(8), dp(16), dp(12)],
            spacing=dp(8),
            orientation='vertical'
        )
        with btn_container.canvas.before:
            Color(*COLORS['surface'])
            self._btn_bg = RoundedRectangle(pos=btn_container.pos, size=btn_container.size)
        btn_container.bind(pos=self._update_btn_bg, size=self._update_btn_bg)
        
        add_btn = Button(
            text='+ 添加交通工具',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        add_btn.bind(on_press=self.add_transport)
        btn_container.add_widget(add_btn)
        
        edit_delete_row = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(8)
        )
        
        edit_btn = Button(
            text='编辑',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        edit_btn.bind(on_press=self.edit_transport)
        edit_delete_row.add_widget(edit_btn)
        
        delete_btn = Button(
            text='删除',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1)
        )
        delete_btn.bind(on_press=self.delete_transport)
        edit_delete_row.add_widget(delete_btn)
        
        btn_container.add_widget(edit_delete_row)
        self.root_layout.add_widget(btn_container)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_btn_bg(self, instance, value):
        self._btn_bg.pos = instance.pos
        self._btn_bg.size = instance.size
    
    def set_world(self, world_id):
        self.world_id = world_id
        self.selected_transport_id = None
        self.load_transports()
    
    def load_transports(self):
        self.transport_list.clear_widgets()
        self.selected_transport_id = None
        
        if not self.world_id:
            return
        
        transports = self.db.get_transport_modes(self.world_id)
        
        if not transports:
            empty_label = Label(
                text='暂无交通工具\n点击下方按钮创建',
                font_size=dp(14),
                font_name=FONT_NAME,
                color=COLORS['text_hint'],
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(200)
            )
            empty_label.bind(size=empty_label.setter('text_size'))
            self.transport_list.add_widget(empty_label)
        else:
            for transport in transports:
                card = TransportCard(transport, on_select=self.select_transport)
                self.transport_list.add_widget(card)
    
    def select_transport(self, transport_id):
        self.selected_transport_id = transport_id
        for child in self.transport_list.children:
            if isinstance(child, TransportCard):
                child.set_selected(child.transport.id == transport_id)
    
    def add_transport(self, instance):
        popup = TransportEditPopup(self.db, self.world_id, on_save=self.load_transports)
        popup.open()
    
    def edit_transport(self, instance):
        if not self.selected_transport_id:
            popup = create_message_popup('请先选择一个交通工具')
            popup.open()
            return
        
        popup = TransportEditPopup(self.db, self.world_id, transport_id=self.selected_transport_id, on_save=self.load_transports)
        popup.open()
    
    def delete_transport(self, instance):
        if not self.selected_transport_id:
            popup = create_message_popup('请先选择一个交通工具')
            popup.open()
            return
        
        popup = create_confirm_popup(
            '确定要删除这个交通工具吗？',
            lambda p: self._do_delete(p),
            confirm_text='删除',
            is_danger=True
        )
        popup.open()
    
    def _do_delete(self, popup):
        self.db.delete_transport_mode(self.selected_transport_id)
        popup.dismiss()
        self.selected_transport_id = None
        self.load_transports()
    
    def go_back(self, instance):
        self.manager.current = 'location_list'


class TransportCard(BoxLayout):
    def __init__(self, transport, on_select=None, **kwargs):
        super().__init__(**kwargs)
        self.transport = transport
        self.on_select = on_select
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(60)
        self.padding = [dp(16), dp(12)]
        
        with self.canvas.before:
            Color(*COLORS['surface'])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        inner = FloatLayout()
        
        name_label = Label(
            text=transport.name,
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            valign='middle',
            pos_hint={'x': 0, 'center_y': 0.5},
            size_hint_x=0.6
        )
        name_label.bind(size=name_label.setter('text_size'))
        inner.add_widget(name_label)
        
        speed_label = Label(
            text=f'{transport.speed} m/s',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            halign='right',
            valign='middle',
            pos_hint={'right': 1, 'center_y': 0.5},
            size_hint_x=0.35
        )
        speed_label.bind(size=speed_label.setter('text_size'))
        inner.add_widget(speed_label)
        
        self.add_widget(inner)
    
    def _update_bg(self, instance, value):
        self._bg.pos = instance.pos
        self._bg.size = instance.size
    
    def set_selected(self, selected):
        with self.canvas.before:
            self.canvas.before.clear()
            if selected:
                Color(*COLORS['primary_light'])
            else:
                Color(*COLORS['surface'])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.on_select:
                self.on_select(self.transport.id)
            return True
        return super().on_touch_down(touch)


class TransportEditPopup(Popup):
    def __init__(self, db, world_id, transport_id=None, on_save=None, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.world_id = world_id
        self.transport_id = transport_id
        self.on_save = on_save
        
        self.title = '编辑交通工具' if transport_id else '添加交通工具'
        self.size_hint = (0.9, 0.6)
        self.background = ''
        self.separator_color = COLORS['primary']
        
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        name_label = Label(
            text='交通工具名称:',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            size_hint_y=None,
            height=dp(24)
        )
        name_label.bind(size=name_label.setter('text_size'))
        content.add_widget(name_label)
        
        self.name_input = TextInput(
            hint_text='如：步行、开车、地铁',
            font_name=FONT_NAME,
            font_size=dp(14),
            multiline=False,
            size_hint_y=None,
            height=dp(44),
            background_normal='',
            background_active='',
            background_color=(0.95, 0.95, 0.95, 1),
            foreground_color=COLORS['text'],
            padding=[dp(12), dp(14), dp(12), dp(14)]
        )
        content.add_widget(self.name_input)
        
        speed_label = Label(
            text='速度 (米/秒):',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            size_hint_y=None,
            height=dp(24)
        )
        speed_label.bind(size=speed_label.setter('text_size'))
        content.add_widget(speed_label)
        
        self.speed_input = TextInput(
            hint_text='如：步行1.4、开车13.9',
            font_name=FONT_NAME,
            font_size=dp(14),
            multiline=False,
            input_filter='float',
            size_hint_y=None,
            height=dp(44),
            background_normal='',
            background_active='',
            background_color=(0.95, 0.95, 0.95, 1),
            foreground_color=COLORS['text'],
            padding=[dp(12), dp(14), dp(12), dp(14)]
        )
        self.speed_input.text = '1.0'
        content.add_widget(self.speed_input)
        
        info_label = Label(
            text='参考: 步行1.4m/s | 骑车5m/s | 开车13.9m/s',
            font_size=dp(11),
            font_name=FONT_NAME,
            color=COLORS['text_hint'],
            halign='center',
            size_hint_y=None,
            height=dp(24)
        )
        info_label.bind(size=info_label.setter('text_size'))
        content.add_widget(info_label)
        
        content.add_widget(BoxLayout())
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(12))
        
        save_btn = Button(
            text='保存',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        save_btn.bind(on_press=self.save)
        btn_row.add_widget(save_btn)
        
        cancel_btn = Button(
            text='取消',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_press=self.dismiss)
        btn_row.add_widget(cancel_btn)
        
        content.add_widget(btn_row)
        
        self.content = content
        
        if transport_id:
            self.load_data()
    
    def load_data(self):
        transport = self.db.get_transport_mode(self.transport_id)
        if transport:
            self.name_input.text = transport.name
            self.speed_input.text = str(transport.speed)
    
    def save(self, instance):
        name = self.name_input.text.strip()
        speed_text = self.speed_input.text.strip()
        
        if not name:
            popup = create_message_popup('请输入交通工具名称')
            popup.open()
            return
        
        try:
            speed = float(speed_text)
            if speed <= 0:
                raise ValueError()
        except ValueError:
            popup = create_message_popup('请输入有效的速度值')
            popup.open()
            return
        
        if self.transport_id:
            self.db.update_transport_mode(self.transport_id, name=name, speed=speed)
        else:
            self.db.create_transport_mode(self.world_id, name, speed)
        
        self.dismiss()
        if self.on_save:
            self.on_save()


class MapSelectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.map_image_path = None
        self.selected_coord = None
        self.on_coord_selected = None
        self._touch_start_pos = None
        self._marker_screen_pos = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='取消',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='选择位置坐标',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        confirm_btn = Button(
            text='确定',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        confirm_btn.bind(on_press=self.confirm_selection)
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(confirm_btn)
        self.root_layout.add_widget(header)
        
        self.map_container = FloatLayout()
        
        self.map_image = Image(
            source='',
            fit_mode='fill',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        
        self.map_container.add_widget(self.map_image)
        
        self._coord_marker = Label(
            text='+',
            font_name=FONT_NAME,
            font_size=dp(48),
            color=(1, 0, 0, 1),
            size_hint=(None, None),
            size=(dp(48), dp(48)),
            pos=(0, 0)
        )
        
        self._coord_text = Label(
            text='(0, 0)',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=(1, 0, 0, 1),
            size_hint=(None, None),
            size=(dp(100), dp(24)),
            pos=(0, 0)
        )
        
        self.map_container.add_widget(self._coord_marker)
        self.map_container.add_widget(self._coord_text)
        self.root_layout.add_widget(self.map_container)
        
        self.coord_display = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            padding=[dp(16), dp(8)]
        )
        with self.coord_display.canvas.before:
            Color(*COLORS['surface'])
            self._coord_bg = RoundedRectangle(pos=self.coord_display.pos, size=self.coord_display.size)
        self.coord_display.bind(pos=self._update_coord_bg, size=self._update_coord_bg)
        
        self.coord_label = Label(
            text='滑动屏幕移动标记点',
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['text']
        )
        self.coord_display.add_widget(self.coord_label)
        self.root_layout.add_widget(self.coord_display)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_coord_bg(self, instance, value):
        self._coord_bg.pos = instance.pos
        self._coord_bg.size = instance.size
    
    def set_map(self, world_id, current_x=0, current_y=0, on_coord_selected=None):
        self.world_id = world_id
        self.on_coord_selected = on_coord_selected
        self.selected_coord = (current_x, current_y)
        
        world = self.db.get_world(world_id)
        if world and world.map_image and os.path.exists(world.map_image):
            self.map_image_path = world.map_image
            self.map_image.source = self.map_image_path
        else:
            self.map_image_path = None
            self.map_image.source = ''
            self.coord_label.text = '请先上传世界地图'
    
    def on_enter(self):
        Clock.schedule_once(self._init_marker_position, 0.1)
    
    def _init_marker_position(self, dt):
        if not self.map_image_path:
            return
        
        container_size = self.map_container.size
        img_size = self.map_image.size
        
        if self.selected_coord and self.selected_coord != (0, 0):
            marker_x = (self.selected_coord[0] / img_size[0]) * container_size[0]
            marker_y = container_size[1] - (self.selected_coord[1] / img_size[1]) * container_size[1]
        else:
            marker_x = container_size[0] / 2
            marker_y = container_size[1] / 2
        
        self._marker_screen_pos = [marker_x, marker_y]
        self._update_marker_display()
    
    def _update_marker_display(self):
        if not self._marker_screen_pos:
            return
        
        container_size = self.map_container.size
        img_size = self.map_image.size
        
        self._marker_screen_pos[0] = max(0, min(container_size[0], self._marker_screen_pos[0]))
        self._marker_screen_pos[1] = max(0, min(container_size[1], self._marker_screen_pos[1]))
        
        self._coord_marker.pos = (
            self._marker_screen_pos[0] - dp(24),
            self._marker_screen_pos[1] - dp(24)
        )
        
        self._coord_text.pos = (
            self._marker_screen_pos[0] + dp(20),
            self._marker_screen_pos[1] + dp(10)
        )
        
        coord_x = int((self._marker_screen_pos[0] / container_size[0]) * img_size[0])
        coord_y = int(img_size[1] - (self._marker_screen_pos[1] / container_size[1]) * img_size[1])
        
        self.selected_coord = (coord_x, coord_y)
        self.coord_label.text = f'坐标: X={coord_x}百米, Y={coord_y}百米 (1单位=100米)'
        self._coord_text.text = f'({coord_x}, {coord_y})'
    
    def on_touch_down(self, touch):
        if self.map_container.collide_point(*touch.pos) and self.map_image_path:
            self._touch_start_pos = (touch.x, touch.y)
            return True
        return super().on_touch_down(touch)
    
    def on_touch_move(self, touch):
        if self._touch_start_pos and self.map_image_path:
            dx = touch.x - self._touch_start_pos[0]
            dy = touch.y - self._touch_start_pos[1]
            
            if self._marker_screen_pos:
                self._marker_screen_pos[0] += dx
                self._marker_screen_pos[1] += dy
                self._update_marker_display()
            
            self._touch_start_pos = (touch.x, touch.y)
            return True
        return super().on_touch_move(touch)
    
    def on_touch_up(self, touch):
        self._touch_start_pos = None
        return super().on_touch_up(touch)
    
    def confirm_selection(self, instance):
        if self.selected_coord and self.on_coord_selected:
            self.on_coord_selected(self.selected_coord[0], self.selected_coord[1])
        self.go_back(None)
    
    def go_back(self, instance):
        self.manager.current = 'location_edit'


class LocationEditScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.location_id = None
        self.map_image_path = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='编辑位置',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(16),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        name_label = Label(
            text='位置名称',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        name_label.bind(size=name_label.setter('text_size'))
        self.content_layout.add_widget(name_label)
        
        self.name_input = AutoExpandTextInput(
            hint_text='输入位置名称',
            initial_height=dp(50)
        )
        self.content_layout.add_widget(self.name_input)
        
        coord_label = Label(
            text='坐标设置 (单位: 百米，1单位=100米)',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        coord_label.bind(size=coord_label.setter('text_size'))
        self.content_layout.add_widget(coord_label)
        
        coord_container = BoxLayout(
            size_hint_y=None,
            height=dp(130),
            orientation='vertical'
        )
        with coord_container.canvas.before:
            Color(*COLORS['surface_light'])
            self._coord_bg = RoundedRectangle(pos=coord_container.pos, size=coord_container.size, radius=[dp(12)])
        coord_container.bind(pos=self._update_coord_bg, size=self._update_coord_bg)
        
        coord_inner = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        
        coord_row = BoxLayout(size_hint_y=None, height=dp(30))
        self.x_label = Label(
            text='X: 0 百米',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left'
        )
        self.x_label.bind(size=self.x_label.setter('text_size'))
        self.y_label = Label(
            text='Y: 0 百米',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left'
        )
        self.y_label.bind(size=self.y_label.setter('text_size'))
        coord_row.add_widget(self.x_label)
        coord_row.add_widget(self.y_label)
        coord_inner.add_widget(coord_row)
        
        input_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        
        x_input_label = Label(
            text='X:',
            font_size=dp(12),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_x=None,
            width=dp(24)
        )
        self.x_input = TextInput(
            hint_text='0',
            font_name=FONT_NAME,
            font_size=dp(13),
            multiline=False,
            input_filter='int',
            size_hint_x=0.4,
            background_normal='',
            background_active='',
            background_color=(1, 1, 1, 1),
            foreground_color=COLORS['text'],
            padding=[dp(8), dp(10), dp(8), dp(10)]
        )
        
        y_input_label = Label(
            text='Y:',
            font_size=dp(12),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_x=None,
            width=dp(24)
        )
        self.y_input = TextInput(
            hint_text='0',
            font_name=FONT_NAME,
            font_size=dp(13),
            multiline=False,
            input_filter='int',
            size_hint_x=0.4,
            background_normal='',
            background_active='',
            background_color=(1, 1, 1, 1),
            foreground_color=COLORS['text'],
            padding=[dp(8), dp(10), dp(8), dp(10)]
        )
        
        input_row.add_widget(x_input_label)
        input_row.add_widget(self.x_input)
        input_row.add_widget(y_input_label)
        input_row.add_widget(self.y_input)
        coord_inner.add_widget(input_row)
        
        select_coord_btn = Button(
            text='在地图上选择坐标',
            font_size=dp(12),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary_light'],
            color=COLORS['text'],
            size_hint_y=None,
            height=dp(36)
        )
        select_coord_btn.bind(on_press=self.select_coordinate_on_map)
        coord_inner.add_widget(select_coord_btn)
        
        coord_container.add_widget(coord_inner)
        self.content_layout.add_widget(coord_container)
        
        sub_label = Label(
            text='二级位置',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        sub_label.bind(size=sub_label.setter('text_size'))
        self.content_layout.add_widget(sub_label)
        
        self.sublocation_list = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8)
        )
        self.sublocation_list.bind(minimum_height=self.sublocation_list.setter('height'))
        self.content_layout.add_widget(self.sublocation_list)
        
        add_sub_btn = Button(
            text='+ 添加二级位置',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['surface_light'],
            color=COLORS['primary'],
            size_hint_y=None,
            height=dp(44)
        )
        add_sub_btn.bind(on_press=self.add_sublocation)
        self.content_layout.add_widget(add_sub_btn)
        
        self.content_layout.add_widget(BoxLayout())
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        save_container = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        with save_container.canvas.before:
            Color(*COLORS['surface'])
            self._save_bg = RoundedRectangle(pos=save_container.pos, size=save_container.size)
        save_container.bind(pos=self._update_save_bg, size=self._update_save_bg)
        
        save_btn = Button(
            text='保存',
            font_size=dp(16),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        save_btn.bind(on_press=self.save_location)
        save_container.add_widget(save_btn)
        self.root_layout.add_widget(save_container)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_coord_bg(self, instance, value):
        self._coord_bg.pos = instance.pos
        self._coord_bg.size = instance.size
    
    def _update_save_bg(self, instance, value):
        self._save_bg.pos = instance.pos
        self._save_bg.size = instance.size
    
    def set_location(self, world_id, location_id):
        self.world_id = world_id
        self.location_id = location_id
        self.x = 0
        self.y = 0
        
        world = self.db.get_world(world_id)
        if world and world.map_image:
            self.map_image_path = world.map_image
        else:
            self.map_image_path = None
        
        if location_id:
            location = self.db.get_location(location_id)
            if location:
                self.title_label.text = location.name
                self.name_input.text = location.name or ''
                self.x = location.x or 0
                self.y = location.y or 0
                self.x_label.text = f'X: {self.x} 百米'
                self.y_label.text = f'Y: {self.y} 百米'
                self.x_input.text = str(self.x)
                self.y_input.text = str(self.y)
                self.load_sublocations()
        else:
            self.title_label.text = '新位置'
            self.name_input.text = ''
            self.x_label.text = 'X: 0 百米'
            self.y_label.text = 'Y: 0 百米'
            self.x_input.text = ''
            self.y_input.text = ''
            self.sublocation_list.clear_widgets()
    
    def load_sublocations(self):
        self.sublocation_list.clear_widgets()
        
        if not self.location_id:
            return
        
        sublocations = self.db.get_sub_locations(self.location_id)
        
        for sub in sublocations:
            sub_card = SubLocationCard(
                sub, 
                on_image_change=self.change_sublocation_image,
                on_name_change=self.change_sublocation_name,
                on_delete=self.delete_sublocation
            )
            self.sublocation_list.add_widget(sub_card)
    
    def select_coordinate_on_map(self, instance):
        if hasattr(self.manager, 'map_select_screen'):
            self.manager.map_select_screen.set_map(
                self.world_id,
                self.x,
                self.y,
                on_coord_selected=self.on_coord_selected
            )
            self.manager.current = 'map_select'
    
    def on_coord_selected(self, x, y):
        self.x = x
        self.y = y
        self.x_label.text = f'X: {self.x} 百米'
        self.y_label.text = f'Y: {self.y} 百米'
        self.x_input.text = str(self.x)
        self.y_input.text = str(self.y)
    
    def add_sublocation(self, instance):
        popup = create_input_popup(
            '输入二级位置名称',
            self._create_sublocation,
            confirm_text='创建',
            title_text='创建二级位置'
        )
        popup.open()
    
    def _create_sublocation(self, name, popup):
        name = name.strip()
        if name and self.location_id:
            self.db.create_location(self.world_id, name, parent_location_id=self.location_id)
            self.load_sublocations()
        popup.dismiss()
    
    def change_sublocation_image(self, sublocation):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title='选择图片',
            filetypes=[('图片文件', '*.png *.jpg *.jpeg *.gif *.bmp')]
        )
        root.destroy()
        
        if file_path:
            self.db.update_location(sublocation.id, image_path=file_path)
            self.load_sublocations()
    
    def change_sublocation_name(self, sublocation):
        popup = create_input_popup(
            '输入新名称',
            lambda name, p: self._update_sublocation_name(sublocation.id, name, p),
            initial_value=sublocation.name,
            confirm_text='保存'
        )
        popup.open()
    
    def _update_sublocation_name(self, sub_id, name, popup):
        if name.strip():
            self.db.update_location(sub_id, name=name.strip())
            self.load_sublocations()
        popup.dismiss()
    
    def delete_sublocation(self, sublocation):
        popup = create_confirm_popup(
            f'确定要删除"{sublocation.name}"吗？',
            lambda p: self._do_delete_sublocation(sublocation.id, p),
            confirm_text='删除',
            is_danger=True
        )
        popup.open()
    
    def _do_delete_sublocation(self, sub_id, popup):
        self.db.delete_location(sub_id)
        popup.dismiss()
        self.load_sublocations()
    
    def save_location(self, instance):
        name = self.name_input.text.strip()
        if not name:
            popup = create_message_popup('请输入位置名称')
            popup.open()
            return
        
        x_text = self.x_input.text.strip()
        y_text = self.y_input.text.strip()
        
        try:
            self.x = int(x_text) if x_text else 0
            self.y = int(y_text) if y_text else 0
        except ValueError:
            popup = create_message_popup('坐标必须是整数')
            popup.open()
            return
        
        if self.location_id:
            self.db.update_location(self.location_id, name=name, x=self.x, y=self.y)
        else:
            location = self.db.create_location(self.world_id, name, x=self.x, y=self.y)
            self.location_id = location.id
            self.title_label.text = name
        
        popup = create_message_popup('保存成功')
        popup.open()
    
    def go_back(self, instance):
        if hasattr(self.manager, 'location_list_screen'):
            self.manager.location_list_screen.load_locations()
        self.manager.current = 'location_list'


class SubLocationCard(BoxLayout):
    def __init__(self, sublocation, on_image_change=None, on_name_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.sublocation = sublocation
        self.on_image_change = on_image_change
        self.on_name_change = on_name_change
        self.on_delete = on_delete
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(70)
        spacing=dp(8)
        
        self._long_press_triggered = False
        self._long_press_event = None
        
        self.image_btn = BoxLayout(
            size_hint_x=None,
            width=dp(60),
            orientation='vertical'
        )
        with self.image_btn.canvas.before:
            Color(*COLORS['surface_light'])
            self._img_bg = RoundedRectangle(pos=self.image_btn.pos, size=self.image_btn.size, radius=[dp(8)])
        self.image_btn.bind(pos=self._update_img_bg, size=self._update_img_bg)
        
        if sublocation.image_path and os.path.exists(sublocation.image_path):
            from kivy.uix.image import Image
            img = Image(source=sublocation.image_path, fit_mode='cover')
            self.image_btn.add_widget(img)
        else:
            img_label = Label(
                text='无图',
                font_size=dp(10),
                font_name=FONT_NAME,
                color=COLORS['text_hint']
            )
            self.image_btn.add_widget(img_label)
        
        self.add_widget(self.image_btn)
        
        name_container = BoxLayout(orientation='vertical')
        name_label = Label(
            text=sublocation.name,
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            valign='middle'
        )
        name_label.bind(size=name_label.setter('text_size'))
        name_container.add_widget(name_label)
        self.add_widget(name_container)
        
        with self.canvas.before:
            Color(*COLORS['surface'])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._update_bg, size=self._update_bg)
    
    def _update_bg(self, instance, value):
        self._bg.pos = instance.pos
        self._bg.size = instance.size
    
    def _update_img_bg(self, instance, value):
        self._img_bg.pos = instance.pos
        self._img_bg.size = instance.size
    
    def _trigger_long_press(self, dt):
        self._long_press_triggered = True
        if self.on_delete:
            self.on_delete(self.sublocation)
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.image_btn.collide_point(*touch.pos):
                if self.on_image_change:
                    self.on_image_change(self.sublocation)
                return True
            
            self._long_press_triggered = False
            self._long_press_event = Clock.schedule_once(self._trigger_long_press, 0.5)
            return True
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if self._long_press_event:
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        
        if self.collide_point(*touch.pos) and not self._long_press_triggered:
            if not self.image_btn.collide_point(*touch.pos):
                if self.on_name_change:
                    self.on_name_change(self.sublocation)
                return True
        return super().on_touch_up(touch)
    
    def on_touch_move(self, touch):
        if self._long_press_event and not self.collide_point(*touch.pos):
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        return super().on_touch_move(touch)


class CharacterListScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='角色管理',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.character_list = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(16), dp(8), dp(16), dp(8)]
        )
        self.character_list.bind(minimum_height=self.character_list.setter('height'))
        
        self.scroll_view.add_widget(self.character_list)
        self.root_layout.add_widget(self.scroll_view)
        
        add_btn_container = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        with add_btn_container.canvas.before:
            Color(*COLORS['surface'])
            self._add_btn_bg = RoundedRectangle(pos=add_btn_container.pos, size=add_btn_container.size)
        add_btn_container.bind(pos=self._update_add_btn_bg, size=self._update_add_btn_bg)
        
        add_btn = Button(
            text='+ 添加角色',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        add_btn.bind(on_press=self.add_character)
        add_btn_container.add_widget(add_btn)
        self.root_layout.add_widget(add_btn_container)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_add_btn_bg(self, instance, value):
        self._add_btn_bg.pos = instance.pos
        self._add_btn_bg.size = instance.size
    
    def set_world(self, world_id):
        self.world_id = world_id
        self.load_characters()
    
    def on_enter(self):
        self.load_characters()
    
    def load_characters(self):
        self.character_list.clear_widgets()
        
        user_settings_btn = Button(
            text='⚙ 用户设置',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['surface_light'],
            color=COLORS['primary'],
            size_hint_y=None,
            height=dp(46)
        )
        user_settings_btn.bind(on_press=self.open_user_settings)
        self.character_list.add_widget(user_settings_btn)
        
        if not self.world_id:
            return
        
        characters = self.db.get_characters_by_world(self.world_id)
        
        if not characters:
            empty_label = Label(
                text='暂无角色\n点击下方按钮创建',
                font_size=dp(14),
                font_name=FONT_NAME,
                color=COLORS['text_hint'],
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(200)
            )
            empty_label.bind(size=empty_label.setter('text_size'))
            self.character_list.add_widget(empty_label)
        else:
            for character in characters:
                card = CharacterCard(character, on_edit=self.edit_character, on_delete=self.delete_character)
                self.character_list.add_widget(card)
    
    def open_user_settings(self, instance):
        if hasattr(self.manager, 'user_settings_screen'):
            self.manager.user_settings_screen.set_world(self.world_id)
            self.manager.current = 'user_settings'
    
    def add_character(self, instance):
        if hasattr(self.manager, 'character_edit_screen'):
            self.manager.character_edit_screen.set_character(self.world_id, None)
            self.manager.current = 'character_edit'
    
    def edit_character(self, character):
        if hasattr(self.manager, 'character_edit_screen'):
            self.manager.character_edit_screen.set_character(self.world_id, character.id)
            self.manager.current = 'character_edit'
    
    def delete_character(self, character):
        popup = create_confirm_popup(
            f'确定要删除"{character.name}"吗？\n此操作不可恢复',
            lambda p: self._do_delete_character(character.id, p),
            confirm_text='删除',
            is_danger=True
        )
        popup.open()
    
    def _do_delete_character(self, character_id, popup):
        self.db.delete_character(character_id)
        popup.dismiss()
        self.load_characters()
    
    def go_back(self, instance):
        self.manager.current = 'world_edit'


class CharacterCard(BoxLayout):
    def __init__(self, character, on_edit=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.character = character
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(70)
        self.padding = [dp(12), dp(8)]
        self.spacing = dp(12)
        
        self._long_press_triggered = False
        self._long_press_event = None
        
        with self.canvas.before:
            Color(*COLORS['surface'])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        if character.avatar_path and os.path.exists(character.avatar_path):
            avatar = Image(
                source=character.avatar_path,
                size_hint_x=None,
                width=dp(54)
            )
        else:
            avatar_container = BoxLayout(size_hint_x=None, width=dp(54))
            with avatar_container.canvas.before:
                Color(*COLORS['primary_light'])
                self._avatar_bg = RoundedRectangle(pos=avatar_container.pos, size=avatar_container.size, radius=[dp(27)])
            avatar_container.bind(pos=self._update_avatar_bg, size=self._update_avatar_bg)
            
            avatar_label = Label(
                text=character.name[0] if character.name else '?',
                font_size=dp(24),
                font_name=FONT_NAME,
                color=COLORS['text']
            )
            avatar_container.add_widget(avatar_label)
            avatar = avatar_container
        
        self.add_widget(avatar)
        
        info_layout = BoxLayout(orientation='vertical', spacing=dp(4))
        
        name_label = Label(
            text=character.name,
            font_size=dp(16),
            font_name=FONT_NAME,
            color=COLORS['text'],
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(28)
        )
        name_label.bind(size=name_label.setter('text_size'))
        info_layout.add_widget(name_label)
        
        gender_text = '男' if character.gender == 'male' else '女' if character.gender == 'female' else '其他'
        gender_label = Label(
            text=f'性别: {gender_text}',
            font_size=dp(12),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(20)
        )
        gender_label.bind(size=gender_label.setter('text_size'))
        info_layout.add_widget(gender_label)
        
        self.add_widget(info_layout)
        self.add_widget(BoxLayout(size_hint_x=None, width=dp(10)))
    
    def _update_bg(self, instance, value):
        self._bg.pos = instance.pos
        self._bg.size = instance.size
    
    def _update_avatar_bg(self, instance, value):
        self._avatar_bg.pos = instance.pos
        self._avatar_bg.size = instance.size
    
    def _trigger_long_press(self, dt):
        self._long_press_triggered = True
        if self.on_delete:
            self.on_delete(self.character)
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._long_press_triggered = False
            self._long_press_event = Clock.schedule_once(self._trigger_long_press, 0.5)
            return True
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if self._long_press_event:
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        
        if self.collide_point(*touch.pos) and not self._long_press_triggered:
            if self.on_edit:
                self.on_edit(self.character)
            return True
        return super().on_touch_up(touch)
    
    def on_touch_move(self, touch):
        if self._long_press_event and not self.collide_point(*touch.pos):
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        return super().on_touch_move(touch)


class HealthScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.character_id = None
        self.character = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='健康状态',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        self.health_items = {}
        self._build_health_ui()
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _build_health_ui(self):
        body_parts = [
            ('mouth', '口腔'),
            ('anus', '肛门'),
            ('buttocks', '臀部'),
            ('penis', '阴茎'),
            ('testicles', '睾丸'),
            ('left_breast', '左乳'),
            ('right_breast', '右乳'),
            ('vagina', '阴道')
        ]
        
        for part_key, part_name in body_parts:
            item = self._create_health_item(part_name)
            self.health_items[part_key] = item
            self.content_layout.add_widget(item)
    
    def _create_health_item(self, part_name):
        container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(80),
            padding=[dp(12), dp(8), dp(12), dp(8)]
        )
        with container.canvas.before:
            Color(*COLORS['surface_light'])
            self._bg = RoundedRectangle(pos=container.pos, size=container.size, radius=[dp(8)])
        container.bind(pos=self._update_item_bg, size=self._update_item_bg)
        
        name_label = Label(
            text=part_name,
            font_name=FONT_NAME,
            font_size=dp(16),
            bold=True,
            color=COLORS['text'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        name_label.bind(size=name_label.setter('text_size'))
        
        status_label = Label(
            text='状态正常',
            font_name=FONT_NAME,
            font_size=dp(13),
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(40),
            halign='left',
            valign='top'
        )
        status_label.bind(size=status_label.setter('text_size'))
        
        container.add_widget(name_label)
        container.add_widget(status_label)
        
        container.status_label = status_label
        container.bg = self._bg
        
        return container
    
    def _update_item_bg(self, instance, value):
        instance.bg.pos = instance.pos
        instance.bg.size = instance.size
    
    def set_character(self, character_id):
        self.character_id = character_id
        self.character = self.db.get_character(character_id)
        
        if self.character:
            self.title_label.text = f'{self.character.name} - 健康状态'
            self._update_health_display()
    
    def _update_health_display(self):
        if not self.character:
            return
        
        body_parts = [
            ('mouth', 'health_mouth', 'health_mouth_color'),
            ('anus', 'health_anus', 'health_anus_color'),
            ('buttocks', 'health_buttocks', 'health_buttocks_color'),
            ('penis', 'health_penis', 'health_penis_color'),
            ('testicles', 'health_testicles', 'health_testicles_color'),
            ('left_breast', 'health_left_breast', 'health_left_breast_color'),
            ('right_breast', 'health_right_breast', 'health_right_breast_color'),
            ('vagina', 'health_vagina', 'health_vagina_color')
        ]
        
        for part_key, health_attr, color_attr in body_parts:
            if part_key in self.health_items:
                item = self.health_items[part_key]
                health_text = getattr(self.character, health_attr, '状态正常') or '状态正常'
                color_hex = getattr(self.character, color_attr, '#28a745') or '#28a745'
                
                item.status_label.text = health_text
                
                try:
                    r = int(color_hex[1:3], 16) / 255
                    g = int(color_hex[3:5], 16) / 255
                    b = int(color_hex[5:7], 16) / 255
                    item.status_label.color = (r, g, b, 1)
                except:
                    item.status_label.color = COLORS['text_secondary']
    
    def go_back(self, instance):
        self.manager.current = 'chat'


class UserHealthScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.world = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='用户健康状态',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        self.health_items = {}
        self._build_health_ui()
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _build_health_ui(self):
        body_parts = [
            ('mouth', '口腔'),
            ('anus', '肛门'),
            ('buttocks', '臀部'),
            ('penis', '阴茎'),
            ('testicles', '睾丸'),
            ('left_breast', '左乳'),
            ('right_breast', '右乳'),
            ('vagina', '阴道')
        ]
        
        for part_key, part_name in body_parts:
            item = self._create_health_item(part_name)
            self.health_items[part_key] = item
            self.content_layout.add_widget(item)
    
    def _create_health_item(self, part_name):
        container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(80),
            padding=[dp(12), dp(8), dp(12), dp(8)]
        )
        with container.canvas.before:
            Color(*COLORS['surface_light'])
            self._bg = RoundedRectangle(pos=container.pos, size=container.size, radius=[dp(8)])
        container.bind(pos=self._update_item_bg, size=self._update_item_bg)
        
        name_label = Label(
            text=part_name,
            font_name=FONT_NAME,
            font_size=dp(16),
            bold=True,
            color=COLORS['text'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        name_label.bind(size=name_label.setter('text_size'))
        
        status_label = Label(
            text='状态正常',
            font_name=FONT_NAME,
            font_size=dp(13),
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(40),
            halign='left',
            valign='top'
        )
        status_label.bind(size=status_label.setter('text_size'))
        
        container.add_widget(name_label)
        container.add_widget(status_label)
        
        container.status_label = status_label
        container.bg = self._bg
        
        return container
    
    def _update_item_bg(self, instance, value):
        instance.bg.pos = instance.pos
        instance.bg.size = instance.size
    
    def set_world(self, world_id):
        self.world_id = world_id
        self.world = self.db.get_world(world_id)
        
        if self.world:
            self.title_label.text = '用户健康状态'
            self._update_health_display()
    
    def _update_health_display(self):
        if not self.world:
            return
        
        body_parts = [
            ('mouth', 'user_health_mouth', 'user_health_mouth_color'),
            ('anus', 'user_health_anus', 'user_health_anus_color'),
            ('buttocks', 'user_health_buttocks', 'user_health_buttocks_color'),
            ('penis', 'user_health_penis', 'user_health_penis_color'),
            ('testicles', 'user_health_testicles', 'user_health_testicles_color'),
            ('left_breast', 'user_health_left_breast', 'user_health_left_breast_color'),
            ('right_breast', 'user_health_right_breast', 'user_health_right_breast_color'),
            ('vagina', 'user_health_vagina', 'user_health_vagina_color')
        ]
        
        for part_key, health_attr, color_attr in body_parts:
            if part_key in self.health_items:
                item = self.health_items[part_key]
                health_text = getattr(self.world, health_attr, '状态正常') or '状态正常'
                color_hex = getattr(self.world, color_attr, '#28a745') or '#28a745'
                
                item.status_label.text = health_text
                
                try:
                    r = int(color_hex[1:3], 16) / 255
                    g = int(color_hex[3:5], 16) / 255
                    b = int(color_hex[5:7], 16) / 255
                    item.status_label.color = (r, g, b, 1)
                except:
                    item.status_label.color = COLORS['text_secondary']
    
    def go_back(self, instance):
        self.manager.current = 'chat'


class ChatMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(16), dp(8), dp(16), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回聊天',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(80),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='功能菜单',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(80)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(16),
            padding=[dp(20), dp(20), dp(20), dp(20)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        self._build_menu_items()
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _build_menu_items(self):
        self.content_layout.clear_widgets()
        
        menu_items = [
            {
                'text': '重置对话',
                'icon': '重置',
                'color': COLORS['accent'],
                'callback': self.restart_from_beginning
            },
            {
                'text': '剧本设置',
                'icon': '剧本',
                'color': COLORS['primary'],
                'callback': self.open_script_settings
            },
            {
                'text': '位置管理',
                'icon': '位置',
                'color': (0.8, 0.4, 0.2, 1),
                'callback': self.open_location_change
            },
            {
                'text': '用户状态',
                'icon': '状态',
                'color': (0.2, 0.6, 0.8, 1),
                'callback': self.open_user_health
            },
            {
                'text': '通话管理',
                'icon': '通话',
                'color': COLORS['call_orange'],
                'callback': self.open_call_manager
            },
        ]
        
        for item in menu_items:
            btn = self._build_menu_button(item)
            self.content_layout.add_widget(btn)
        
        self.content_layout.add_widget(BoxLayout())
    
    def _build_menu_button(self, item):
        container = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(70),
            spacing=dp(12)
        )
        with container.canvas.before:
            Color(*COLORS['surface'])
            container._bg = RoundedRectangle(pos=container.pos, size=container.size, radius=[dp(12)])
        container.bind(pos=self._update_btn_bg, size=self._update_btn_bg)
        
        icon_container = BoxLayout(
            size_hint_x=None,
            width=dp(60),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        
        icon_btn = Button(
            text=item['icon'],
            font_size=dp(16),
            font_name=FONT_NAME,
            background_normal='',
            background_color=item['color'],
            color=(1, 1, 1, 1)
        )
        icon_container.add_widget(icon_btn)
        container.add_widget(icon_container)
        
        text_container = BoxLayout(
            orientation='vertical',
            padding=[dp(4), dp(8), dp(4), dp(8)]
        )
        
        text_label = Label(
            text=item['text'],
            font_size=dp(18),
            font_name=FONT_NAME,
            color=COLORS['text'],
            bold=True,
            halign='left',
            valign='middle'
        )
        text_label.bind(size=text_label.setter('text_size'))
        text_container.add_widget(text_label)
        container.add_widget(text_container)
        
        container.bind(on_touch_down=lambda instance, touch, cb=item['callback']: self._on_btn_touch(instance, touch, cb))
        
        return container
    
    def _update_btn_bg(self, instance, value):
        if hasattr(instance, '_bg'):
            instance._bg.pos = instance.pos
            instance._bg.size = instance.size
    
    def _on_btn_touch(self, instance, touch, callback):
        if instance.collide_point(*touch.pos):
            callback()
            return True
        return False
    
    def set_world(self, world_id):
        self.world_id = world_id
    
    def restart_from_beginning(self):
        if self.world_id:
            sessions = self.db.get_chat_sessions_by_world(self.world_id)
            for session in sessions:
                self.db.delete_chat_session(session.id)
            
            self.db.clear_memories(self.world_id, from_segment=1)
            
            self.db.create_chat_session(self.world_id)
            
            if hasattr(self.manager, 'chat_screen'):
                self.manager.chat_screen.session_id = None
                self.manager.chat_screen.load_messages()
            
            popup = create_message_popup('已重置对话')
            popup.open()
            self.go_back(None)
    
    def open_script_settings(self):
        if hasattr(self.manager, 'script_settings_screen'):
            self.manager.script_settings_screen.set_world(self.world_id)
            self.manager.current = 'script_settings'
    
    def open_location_change(self):
        if hasattr(self.manager, 'location_change_screen'):
            self.manager.location_change_screen.set_world(self.world_id)
            self.manager.current = 'location_change'
    
    def open_user_health(self):
        if hasattr(self.manager, 'user_health_screen'):
            self.manager.user_health_screen.set_world(self.world_id)
            self.manager.current = 'user_health'
    
    def open_call_manager(self):
        if hasattr(self.manager, 'call_manager_screen'):
            self.manager.call_manager_screen.set_world(self.world_id)
            self.manager.current = 'call_manager'
    
    def go_back(self, instance):
        self.manager.current = 'chat'


class CharacterMemoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.character_id = None
        self.character_name = ''
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='角色记忆',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        add_btn = Button(
            text='+',
            font_size=dp(20),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(50),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        add_btn.bind(on_press=self.show_add_memory_options)
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(add_btn)
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def set_character(self, world_id, character_id):
        self.world_id = world_id
        self.character_id = character_id
        
        character = self.db.get_character(character_id)
        if character:
            self.character_name = character.name
            self.title_label.text = f'{character.name}的记忆'
        
        self.load_memories()
    
    def load_memories(self):
        self.content_layout.clear_widgets()
        
        short_term_label = Label(
            text='短期记忆',
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['primary'],
            bold=True,
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        short_term_label.bind(size=short_term_label.setter('text_size'))
        self.content_layout.add_widget(short_term_label)
        
        short_term_memories = self.db.get_short_term_memories(self.world_id, self.character_id, limit=20)
        
        if short_term_memories:
            for mem in short_term_memories:
                card = self._build_memory_card(mem, is_short_term=True)
                self.content_layout.add_widget(card)
        else:
            empty_label = Label(
                text='暂无短期记忆',
                font_name=FONT_NAME,
                font_size=dp(14),
                color=COLORS['text_hint'],
                size_hint_y=None,
                height=dp(40)
            )
            self.content_layout.add_widget(empty_label)
        
        long_term_label = Label(
            text='长期记忆',
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['accent'],
            bold=True,
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        long_term_label.bind(size=long_term_label.setter('text_size'))
        self.content_layout.add_widget(long_term_label)
        
        long_term_memories = self.db.get_long_term_memories(self.world_id, self.character_id, limit=20)
        
        if long_term_memories:
            for mem in long_term_memories:
                card = self._build_memory_card(mem, is_short_term=False)
                self.content_layout.add_widget(card)
        else:
            empty_label = Label(
                text='暂无长期记忆',
                font_name=FONT_NAME,
                font_size=dp(14),
                color=COLORS['text_hint'],
                size_hint_y=None,
                height=dp(40)
            )
            self.content_layout.add_widget(empty_label)
        
        self.content_layout.add_widget(BoxLayout())
    
    def _build_memory_card(self, memory, is_short_term=True):
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(100),
            padding=[dp(12), dp(8), dp(12), dp(8)]
        )
        with card.canvas.before:
            Color(*COLORS['surface_light'])
            card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(8)])
        card.bind(pos=self._update_card_bg, size=self._update_card_bg)
        
        content_row = BoxLayout(size_hint_y=None, height=dp(50))
        
        content_label = Label(
            text=memory.content[:100] + ('...' if len(memory.content) > 100 else ''),
            font_name=FONT_NAME,
            font_size=dp(13),
            color=COLORS['text'],
            halign='left',
            valign='top',
            text_size=(None, None)
        )
        content_label.bind(size=content_label.setter('text_size'))
        content_row.add_widget(content_label)
        card.add_widget(content_row)
        
        info_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        
        importance_label = Label(
            text=f'重要性: {memory.importance}',
            font_name=FONT_NAME,
            font_size=dp(11),
            color=COLORS['text_secondary'],
            halign='left',
            size_hint_x=0.4
        )
        importance_label.bind(size=importance_label.setter('text_size'))
        info_row.add_widget(importance_label)
        
        time_label = Label(
            text=memory.created_at[:16] if memory.created_at else '',
            font_name=FONT_NAME,
            font_size=dp(11),
            color=COLORS['text_hint'],
            halign='right',
            size_hint_x=0.6
        )
        time_label.bind(size=time_label.setter('text_size'))
        info_row.add_widget(time_label)
        
        card.add_widget(info_row)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        
        edit_btn = Button(
            text='编辑',
            font_name=FONT_NAME,
            font_size=dp(12),
            background_normal='',
            background_color=COLORS['primary_light'],
            color=(1, 1, 1, 1)
        )
        edit_btn.bind(on_press=lambda x, m=memory, s=is_short_term: self.edit_memory(m, s))
        btn_row.add_widget(edit_btn)
        
        delete_btn = Button(
            text='删除',
            font_name=FONT_NAME,
            font_size=dp(12),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        delete_btn.bind(on_press=lambda x, m=memory, s=is_short_term: self.delete_memory(m, s))
        btn_row.add_widget(delete_btn)
        
        card.add_widget(btn_row)
        
        return card
    
    def _update_card_bg(self, instance, value):
        if hasattr(instance, '_bg'):
            instance._bg.pos = instance.pos
            instance._bg.size = instance.size
    
    def show_add_memory_options(self, instance):
        popup = Popup(title='添加记忆', size_hint=(0.8, 0.4))
        
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        short_btn = Button(
            text='添加短期记忆',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        short_btn.bind(on_press=lambda x: self._add_memory_popup(True, popup))
        content.add_widget(short_btn)
        
        long_btn = Button(
            text='添加长期记忆',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        long_btn.bind(on_press=lambda x: self._add_memory_popup(False, popup))
        content.add_widget(long_btn)
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(14),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_press=popup.dismiss)
        content.add_widget(cancel_btn)
        
        popup.content = content
        popup.open()
    
    def _add_memory_popup(self, is_short_term, parent_popup=None):
        if parent_popup:
            parent_popup.dismiss()
        
        title = '添加短期记忆' if is_short_term else '添加长期记忆'
        popup = Popup(title=title, size_hint=(0.9, 0.7))
        
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        content_input = AutoExpandTextInput(
            hint_text='输入记忆内容',
            initial_height=dp(100)
        )
        content.add_widget(content_input)
        
        importance_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        importance_label = Label(
            text='重要性:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            size_hint_x=None,
            width=dp(60)
        )
        importance_row.add_widget(importance_label)
        
        importance_input = TextInput(
            text='5',
            input_filter='int',
            multiline=False,
            font_name=FONT_NAME,
            font_size=dp(14)
        )
        importance_row.add_widget(importance_input)
        content.add_widget(importance_row)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        
        save_btn = Button(
            text='保存',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        btn_row.add_widget(save_btn)
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(cancel_btn)
        
        content.add_widget(btn_row)
        
        def save_memory(instance):
            text = content_input.text.strip()
            if not text:
                return
            
            try:
                importance = int(importance_input.text)
            except:
                importance = 5
            
            if is_short_term:
                self.db.create_short_term_memory(
                    world_id=self.world_id,
                    character_id=self.character_id,
                    content=text,
                    importance=importance
                )
            else:
                self.db.create_long_term_memory(
                    world_id=self.world_id,
                    character_id=self.character_id,
                    content=text,
                    importance=importance
                )
            
            popup.dismiss()
            self.load_memories()
        
        save_btn.bind(on_press=save_memory)
        
        popup.content = content
        popup.open()
    
    def edit_memory(self, memory, is_short_term):
        title = '编辑短期记忆' if is_short_term else '编辑长期记忆'
        popup = Popup(title=title, size_hint=(0.9, 0.7))
        
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        content_input = AutoExpandTextInput(
            hint_text='输入记忆内容',
            initial_height=dp(100)
        )
        content_input.text = memory.content
        content.add_widget(content_input)
        
        importance_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        importance_label = Label(
            text='重要性:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            size_hint_x=None,
            width=dp(60)
        )
        importance_row.add_widget(importance_label)
        
        importance_input = TextInput(
            text=str(memory.importance),
            input_filter='int',
            multiline=False,
            font_name=FONT_NAME,
            font_size=dp(14)
        )
        importance_row.add_widget(importance_input)
        content.add_widget(importance_row)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        
        save_btn = Button(
            text='保存',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        btn_row.add_widget(save_btn)
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(cancel_btn)
        
        content.add_widget(btn_row)
        
        def save_memory(instance):
            text = content_input.text.strip()
            if not text:
                return
            
            try:
                importance = int(importance_input.text)
            except:
                importance = 5
            
            if is_short_term:
                self.db.update_short_term_memory(memory.id, content=text, importance=importance)
            else:
                self.db.update_long_term_memory(memory.id, content=text, importance=importance)
            
            popup.dismiss()
            self.load_memories()
        
        save_btn.bind(on_press=save_memory)
        
        popup.content = content
        popup.open()
    
    def delete_memory(self, memory, is_short_term):
        popup = Popup(title='确认删除', size_hint=(0.8, 0.3))
        
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        msg_label = Label(
            text='确定要删除这条记忆吗？',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text']
        )
        content.add_widget(msg_label)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        
        delete_btn = Button(
            text='删除',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        btn_row.add_widget(delete_btn)
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(cancel_btn)
        
        content.add_widget(btn_row)
        
        def confirm_delete(instance):
            if is_short_term:
                self.db.delete_short_term_memory(memory.id)
            else:
                self.db.delete_long_term_memory(memory.id)
            
            popup.dismiss()
            self.load_memories()
        
        delete_btn.bind(on_press=confirm_delete)
        
        popup.content = content
        popup.open()
    
    def go_back(self, instance):
        self.manager.current = 'character_edit'


class WorldMemoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='世界记忆',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        add_btn = Button(
            text='+',
            font_size=dp(20),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(50),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        add_btn.bind(on_press=self.show_add_memory_options)
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(add_btn)
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def set_world(self, world_id):
        self.world_id = world_id
        
        world = self.db.get_world(world_id)
        if world:
            self.title_label.text = f'{world.name}的世界记忆'
        
        self.load_memories()
    
    def load_memories(self):
        self.content_layout.clear_widgets()
        
        short_term_label = Label(
            text='短期记忆（全局）',
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['primary'],
            bold=True,
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        short_term_label.bind(size=short_term_label.setter('text_size'))
        self.content_layout.add_widget(short_term_label)
        
        short_term_memories = self.db.get_short_term_memories(self.world_id, character_id=None, limit=20)
        
        if short_term_memories:
            for mem in short_term_memories:
                card = self._build_memory_card(mem, is_short_term=True)
                self.content_layout.add_widget(card)
        else:
            empty_label = Label(
                text='暂无全局短期记忆',
                font_name=FONT_NAME,
                font_size=dp(14),
                color=COLORS['text_hint'],
                size_hint_y=None,
                height=dp(40)
            )
            self.content_layout.add_widget(empty_label)
        
        long_term_label = Label(
            text='长期记忆（全局）',
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['accent'],
            bold=True,
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        long_term_label.bind(size=long_term_label.setter('text_size'))
        self.content_layout.add_widget(long_term_label)
        
        long_term_memories = self.db.get_long_term_memories(self.world_id, character_id=None, limit=20)
        
        if long_term_memories:
            for mem in long_term_memories:
                card = self._build_memory_card(mem, is_short_term=False)
                self.content_layout.add_widget(card)
        else:
            empty_label = Label(
                text='暂无全局长期记忆',
                font_name=FONT_NAME,
                font_size=dp(14),
                color=COLORS['text_hint'],
                size_hint_y=None,
                height=dp(40)
            )
            self.content_layout.add_widget(empty_label)
        
        self.content_layout.add_widget(BoxLayout())
    
    def _build_memory_card(self, memory, is_short_term=True):
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(100),
            padding=[dp(12), dp(8), dp(12), dp(8)]
        )
        with card.canvas.before:
            Color(*COLORS['surface_light'])
            card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(8)])
        card.bind(pos=self._update_card_bg, size=self._update_card_bg)
        
        content_row = BoxLayout(size_hint_y=None, height=dp(50))
        
        content_label = Label(
            text=memory.content[:100] + ('...' if len(memory.content) > 100 else ''),
            font_name=FONT_NAME,
            font_size=dp(13),
            color=COLORS['text'],
            halign='left',
            valign='top',
            text_size=(None, None)
        )
        content_label.bind(size=content_label.setter('text_size'))
        content_row.add_widget(content_label)
        card.add_widget(content_row)
        
        info_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        
        importance_label = Label(
            text=f'重要性: {memory.importance}',
            font_name=FONT_NAME,
            font_size=dp(11),
            color=COLORS['text_secondary'],
            halign='left',
            size_hint_x=0.4
        )
        importance_label.bind(size=importance_label.setter('text_size'))
        info_row.add_widget(importance_label)
        
        time_label = Label(
            text=memory.created_at[:16] if memory.created_at else '',
            font_name=FONT_NAME,
            font_size=dp(11),
            color=COLORS['text_hint'],
            halign='right',
            size_hint_x=0.6
        )
        time_label.bind(size=time_label.setter('text_size'))
        info_row.add_widget(time_label)
        
        card.add_widget(info_row)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        
        edit_btn = Button(
            text='编辑',
            font_name=FONT_NAME,
            font_size=dp(12),
            background_normal='',
            background_color=COLORS['primary_light'],
            color=(1, 1, 1, 1)
        )
        edit_btn.bind(on_press=lambda x, m=memory, s=is_short_term: self.edit_memory(m, s))
        btn_row.add_widget(edit_btn)
        
        delete_btn = Button(
            text='删除',
            font_name=FONT_NAME,
            font_size=dp(12),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        delete_btn.bind(on_press=lambda x, m=memory, s=is_short_term: self.delete_memory(m, s))
        btn_row.add_widget(delete_btn)
        
        card.add_widget(btn_row)
        
        return card
    
    def _update_card_bg(self, instance, value):
        if hasattr(instance, '_bg'):
            instance._bg.pos = instance.pos
            instance._bg.size = instance.size
    
    def show_add_memory_options(self, instance):
        popup = Popup(title='添加记忆', size_hint=(0.8, 0.4))
        
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        short_btn = Button(
            text='添加短期记忆',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        short_btn.bind(on_press=lambda x: self._add_memory_popup(True, popup))
        content.add_widget(short_btn)
        
        long_btn = Button(
            text='添加长期记忆',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        long_btn.bind(on_press=lambda x: self._add_memory_popup(False, popup))
        content.add_widget(long_btn)
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(14),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_press=popup.dismiss)
        content.add_widget(cancel_btn)
        
        popup.content = content
        popup.open()
    
    def _add_memory_popup(self, is_short_term, parent_popup=None):
        if parent_popup:
            parent_popup.dismiss()
        
        title = '添加短期记忆' if is_short_term else '添加长期记忆'
        popup = Popup(title=title, size_hint=(0.9, 0.7))
        
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        content_input = AutoExpandTextInput(
            hint_text='输入记忆内容',
            initial_height=dp(100)
        )
        content.add_widget(content_input)
        
        importance_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        importance_label = Label(
            text='重要性:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            size_hint_x=None,
            width=dp(60)
        )
        importance_row.add_widget(importance_label)
        
        importance_input = TextInput(
            text='5',
            input_filter='int',
            multiline=False,
            font_name=FONT_NAME,
            font_size=dp(14)
        )
        importance_row.add_widget(importance_input)
        content.add_widget(importance_row)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        
        save_btn = Button(
            text='保存',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        btn_row.add_widget(save_btn)
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(cancel_btn)
        
        content.add_widget(btn_row)
        
        def save_memory(instance):
            text = content_input.text.strip()
            if not text:
                return
            
            try:
                importance = int(importance_input.text)
            except:
                importance = 5
            
            if is_short_term:
                self.db.create_short_term_memory(
                    world_id=self.world_id,
                    character_id=None,
                    content=text,
                    importance=importance
                )
            else:
                self.db.create_long_term_memory(
                    world_id=self.world_id,
                    character_id=None,
                    content=text,
                    importance=importance
                )
            
            popup.dismiss()
            self.load_memories()
        
        save_btn.bind(on_press=save_memory)
        
        popup.content = content
        popup.open()
    
    def edit_memory(self, memory, is_short_term):
        title = '编辑短期记忆' if is_short_term else '编辑长期记忆'
        popup = Popup(title=title, size_hint=(0.9, 0.7))
        
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        content_input = AutoExpandTextInput(
            hint_text='输入记忆内容',
            initial_height=dp(100)
        )
        content_input.text = memory.content
        content.add_widget(content_input)
        
        importance_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        importance_label = Label(
            text='重要性:',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            size_hint_x=None,
            width=dp(60)
        )
        importance_row.add_widget(importance_label)
        
        importance_input = TextInput(
            text=str(memory.importance),
            input_filter='int',
            multiline=False,
            font_name=FONT_NAME,
            font_size=dp(14)
        )
        importance_row.add_widget(importance_input)
        content.add_widget(importance_row)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        
        save_btn = Button(
            text='保存',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1)
        )
        btn_row.add_widget(save_btn)
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(cancel_btn)
        
        content.add_widget(btn_row)
        
        def save_memory(instance):
            text = content_input.text.strip()
            if not text:
                return
            
            try:
                importance = int(importance_input.text)
            except:
                importance = 5
            
            if is_short_term:
                self.db.update_short_term_memory(memory.id, content=text, importance=importance)
            else:
                self.db.update_long_term_memory(memory.id, content=text, importance=importance)
            
            popup.dismiss()
            self.load_memories()
        
        save_btn.bind(on_press=save_memory)
        
        popup.content = content
        popup.open()
    
    def delete_memory(self, memory, is_short_term):
        popup = Popup(title='确认删除', size_hint=(0.8, 0.3))
        
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        
        msg_label = Label(
            text='确定要删除这条记忆吗？',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text']
        )
        content.add_widget(msg_label)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        
        delete_btn = Button(
            text='删除',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        btn_row.add_widget(delete_btn)
        
        cancel_btn = Button(
            text='取消',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_press=popup.dismiss)
        btn_row.add_widget(cancel_btn)
        
        content.add_widget(btn_row)
        
        def confirm_delete(instance):
            if is_short_term:
                self.db.delete_short_term_memory(memory.id)
            else:
                self.db.delete_long_term_memory(memory.id)
            
            popup.dismiss()
            self.load_memories()
        
        delete_btn.bind(on_press=confirm_delete)
        
        popup.content = content
        popup.open()
    
    def go_back(self, instance):
        self.manager.current = 'world_edit'


class CallManagerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='通话管理',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def set_world(self, world_id):
        self.world_id = world_id
        self.load_data()
    
    def load_data(self):
        self.content_layout.clear_widgets()
        
        if not self.world_id:
            return
        
        world = self.db.get_world(self.world_id)
        active_calls = self.db.get_active_calls_by_world(self.world_id)
        pending_requests = self.db.get_pending_call_requests(self.world_id)
        
        info_label = Label(
            text='管理角色通话状态\n通话中的角色会临时来到您的位置参与对话',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text_secondary'],
            halign='center',
            size_hint_y=None,
            height=dp(60)
        )
        info_label.bind(size=info_label.setter('text_size'))
        self.content_layout.add_widget(info_label)
        
        if pending_requests:
            requests_label = Label(
                text='来电请求',
                font_name=FONT_NAME,
                font_size=dp(16),
                color=COLORS['call_alert'],
                bold=True,
                halign='left',
                size_hint_y=None,
                height=dp(30)
            )
            requests_label.bind(size=requests_label.setter('text_size'))
            self.content_layout.add_widget(requests_label)
            
            for request in pending_requests:
                request_card = self._build_call_request_card(request)
                self.content_layout.add_widget(request_card)
        
        if active_calls:
            active_label = Label(
                text='当前通话中',
                font_name=FONT_NAME,
                font_size=dp(16),
                color=COLORS['call_orange'],
                bold=True,
                halign='left',
                size_hint_y=None,
                height=dp(30)
            )
            active_label.bind(size=active_label.setter('text_size'))
            self.content_layout.add_widget(active_label)
            
            for call in active_calls:
                call_card = self._build_active_call_card(call)
                self.content_layout.add_widget(call_card)
        
        start_label = Label(
            text='开始新通话',
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['primary'],
            bold=True,
            halign='left',
            size_hint_y=None,
            height=dp(30)
        )
        start_label.bind(size=start_label.setter('text_size'))
        self.content_layout.add_widget(start_label)
        
        all_characters = self.db.get_characters_by_world(self.world_id)
        call_character_ids = {call.character_id for call in active_calls}
        request_character_ids = {req.character_id for req in pending_requests}
        
        user_location = world.user_location if world else None
        
        for char in all_characters:
            if char.id not in call_character_ids and char.id not in request_character_ids:
                if char.location != user_location:
                    char_card = self._build_character_card(char)
                    self.content_layout.add_widget(char_card)
        
        self.content_layout.add_widget(BoxLayout())
    
    def _build_call_request_card(self, request):
        card = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(70),
            spacing=dp(12)
        )
        with card.canvas.before:
            Color(*COLORS['surface_light'])
            card._card_bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])
        card.bind(pos=self._update_card_bg, size=self._update_card_bg)
        
        info_layout = BoxLayout(orientation='vertical', spacing=dp(4))
        
        name_label = Label(
            text=f'来电: {request.character_name}',
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['call_alert'],
            bold=True,
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(24)
        )
        name_label.bind(size=name_label.setter('text_size'))
        info_layout.add_widget(name_label)
        
        time_label = Label(
            text=f'请求时间: {request.request_date} {request.request_time}',
            font_name=FONT_NAME,
            font_size=dp(12),
            color=COLORS['text_secondary'],
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(20)
        )
        time_label.bind(size=time_label.setter('text_size'))
        info_layout.add_widget(time_label)
        
        card.add_widget(info_layout)
        
        btn_layout = BoxLayout(size_hint_x=None, width=dp(100), spacing=dp(4))
        
        accept_btn = Button(
            text='接听',
            font_name=FONT_NAME,
            font_size=dp(12),
            size_hint_x=None,
            width=dp(48),
            background_normal='',
            background_color=COLORS['call_orange'],
            color=(1, 1, 1, 1)
        )
        accept_btn.bind(on_press=lambda x, r=request: self.accept_call_request(r))
        btn_layout.add_widget(accept_btn)
        
        dismiss_btn = Button(
            text='忽略',
            font_name=FONT_NAME,
            font_size=dp(12),
            size_hint_x=None,
            width=dp(48),
            background_normal='',
            background_color=COLORS['text_hint'],
            color=(1, 1, 1, 1)
        )
        dismiss_btn.bind(on_press=lambda x, r=request: self.dismiss_call_request(r))
        btn_layout.add_widget(dismiss_btn)
        
        card.add_widget(btn_layout)
        
        return card
    
    def _build_active_call_card(self, call):
        card = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(70),
            spacing=dp(12)
        )
        with card.canvas.before:
            Color(*COLORS['surface_light'])
            card._card_bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])
        card.bind(pos=self._update_card_bg, size=self._update_card_bg)
        
        info_layout = BoxLayout(orientation='vertical', spacing=dp(4))
        
        name_label = Label(
            text=f'📞 {call.character_name}',
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['call_orange'],
            bold=True,
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(24)
        )
        name_label.bind(size=name_label.setter('text_size'))
        info_layout.add_widget(name_label)
        
        location_label = Label(
            text=f'原位置: {call.original_location}',
            font_name=FONT_NAME,
            font_size=dp(12),
            color=COLORS['text_secondary'],
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(20)
        )
        location_label.bind(size=location_label.setter('text_size'))
        info_layout.add_widget(location_label)
        
        time_label = Label(
            text=f'通话开始: {call.call_start_date} {call.call_start_time}',
            font_name=FONT_NAME,
            font_size=dp(12),
            color=COLORS['text_hint'],
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(20)
        )
        time_label.bind(size=time_label.setter('text_size'))
        info_layout.add_widget(time_label)
        
        card.add_widget(info_layout)
        
        end_btn = Button(
            text='结束通话',
            font_name=FONT_NAME,
            font_size=dp(12),
            size_hint_x=None,
            width=dp(80),
            background_normal='',
            background_color=COLORS['accent'],
            color=(1, 1, 1, 1)
        )
        end_btn.bind(on_press=lambda x, c=call: self.end_call(c))
        card.add_widget(end_btn)
        
        return card
    
    def _build_character_card(self, character):
        card = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(60),
            spacing=dp(12)
        )
        with card.canvas.before:
            Color(*COLORS['surface_light'])
            card._card_bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])
        card.bind(pos=self._update_card_bg, size=self._update_card_bg)
        
        info_layout = BoxLayout(orientation='vertical', spacing=dp(4))
        
        name_label = Label(
            text=character.name,
            font_name=FONT_NAME,
            font_size=dp(16),
            color=COLORS['text'],
            bold=True,
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(24)
        )
        name_label.bind(size=name_label.setter('text_size'))
        info_layout.add_widget(name_label)
        
        location_label = Label(
            text=f'位置: {character.location or "未知"}',
            font_name=FONT_NAME,
            font_size=dp(12),
            color=COLORS['text_secondary'],
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(20)
        )
        location_label.bind(size=location_label.setter('text_size'))
        info_layout.add_widget(location_label)
        
        card.add_widget(info_layout)
        
        call_btn = Button(
            text='📞 通话',
            font_name=FONT_NAME,
            font_size=dp(12),
            size_hint_x=None,
            width=dp(80),
            background_normal='',
            background_color=COLORS['call_orange'],
            color=(1, 1, 1, 1)
        )
        call_btn.bind(on_press=lambda x, c=character: self.start_call(c))
        card.add_widget(call_btn)
        
        return card
    
    def _update_card_bg(self, instance, value):
        if hasattr(instance, '_card_bg'):
            instance._card_bg.pos = instance.pos
            instance._card_bg.size = instance.size
    
    def start_call(self, character):
        world = self.db.get_world(self.world_id)
        if not world:
            return
        
        original_location = character.location or '未知'
        
        self.db.create_active_call(
            world_id=self.world_id,
            character_id=character.id,
            character_name=character.name,
            original_location=original_location,
            call_start_date=world.current_date,
            call_start_time=world.current_time
        )
        
        self.db.update_character(character.id, location=world.user_location)
        
        self.load_data()
        
        if hasattr(self.manager, 'chat_screen'):
            self.manager.chat_screen.update_speaker_list()
    
    def accept_call_request(self, request):
        character = self.db.get_character(request.character_id)
        if not character:
            self.db.dismiss_call_request(request.id)
            self.load_data()
            return
        
        world = self.db.get_world(self.world_id)
        if not world:
            return
        
        original_location = character.location or '未知'
        
        self.db.create_active_call(
            world_id=self.world_id,
            character_id=character.id,
            character_name=character.name,
            original_location=original_location,
            call_start_date=world.current_date,
            call_start_time=world.current_time
        )
        
        self.db.update_character(character.id, location=world.user_location)
        self.db.mark_call_request_as_handled(request.id)
        
        self.load_data()
        
        if hasattr(self.manager, 'chat_screen'):
            self.manager.chat_screen.update_speaker_list()
            self.manager.chat_screen.update_call_button_state()
    
    def dismiss_call_request(self, request):
        self.db.dismiss_call_request(request.id)
        self.load_data()
        
        if hasattr(self.manager, 'chat_screen'):
            self.manager.chat_screen.update_call_button_state()
    
    def end_call(self, call):
        character = self.db.get_character(call.character_id)
        if character:
            self.db.update_character(call.character_id, location=call.original_location)
            
            self._consolidate_call_memories(call.character_id)
        
        self.db.end_active_call(call.id)
        
        self.load_data()
        
        if hasattr(self.manager, 'chat_screen'):
            self.manager.chat_screen.update_speaker_list()
            self.manager.chat_screen.update_call_button_state()
    
    def _consolidate_call_memories(self, character_id):
        try:
            short_term_memories = self.db.get_short_term_memories(self.world_id, character_id, limit=10)
            
            if short_term_memories:
                world = self.db.get_world(self.world_id)
                content = f"通话期间的记忆汇总: 共{len(short_term_memories)}条短期记忆"
                importance = max(m.importance for m in short_term_memories) if short_term_memories else 1
                
                source_ids = ','.join(str(m.id) for m in short_term_memories)
                self.db.create_long_term_memory(
                    world_id=self.world_id,
                    content=content,
                    importance=importance,
                    character_id=character_id,
                    source_short_term_ids=source_ids
                )
                
                for mem in short_term_memories:
                    self.db.delete_short_term_memory(mem.id)
                
                print(f"已为角色{character_id}汇总{len(short_term_memories)}条通话记忆")
        except Exception as e:
            print(f"汇总通话记忆失败: {e}")
    
    def go_back(self, instance):
        self.manager.current = 'chat'


class UserSettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        title_label = Label(
            text='用户设置',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(16),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        user_name_label = Label(
            text='用户名称',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        user_name_label.bind(size=user_name_label.setter('text_size'))
        self.content_layout.add_widget(user_name_label)
        
        self.user_name_input = AutoExpandTextInput(
            hint_text='输入用户名称',
            initial_height=dp(50)
        )
        self.content_layout.add_widget(self.user_name_input)
        
        location_row = BoxLayout(
            size_hint_y=None,
            height=dp(36),
            spacing=dp(8)
        )
        
        location_label_container = BoxLayout(
            size_hint_x=None,
            width=dp(70)
        )
        location_label = Label(
            text='用户地点:',
            font_name=FONT_NAME,
            font_size=dp(13),
            color=COLORS['text_secondary'],
            halign='left',
            valign='middle'
        )
        location_label.bind(size=location_label.setter('text_size'))
        location_label_container.add_widget(location_label)
        
        self.user_location_spinner = ChineseSpinner(
            text='未设置',
            font_name=FONT_NAME,
            font_size=dp(13),
            size_hint_x=1,
            height=dp(36),
            values=['未设置'],
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1),
            color=COLORS['text']
        )
        
        location_row.add_widget(location_label_container)
        location_row.add_widget(self.user_location_spinner)
        self.content_layout.add_widget(location_row)
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        save_container = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        with save_container.canvas.before:
            Color(*COLORS['surface'])
            self._save_bg = RoundedRectangle(pos=save_container.pos, size=save_container.size)
        save_container.bind(pos=self._update_save_bg, size=self._update_save_bg)
        
        save_btn = Button(
            text='保存',
            font_size=dp(16),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        save_btn.bind(on_press=self.save_settings)
        save_container.add_widget(save_btn)
        self.root_layout.add_widget(save_container)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_save_bg(self, instance, value):
        self._save_bg.pos = instance.pos
        self._save_bg.size = instance.size
    
    def set_world(self, world_id):
        self.world_id = world_id
        
        primary_locations = self.db.get_primary_locations(world_id)
        location_values = ['未设置']
        
        if primary_locations:
            for primary_loc in primary_locations:
                sub_locations = self.db.get_sub_locations(primary_loc.id)
                if sub_locations:
                    location_values.append(f"【{primary_loc.name}】")
                    for sub_loc in sub_locations:
                        location_values.append(f"  └ {sub_loc.name}")
                else:
                    location_values.append(f"【{primary_loc.name}】")
        
        self.user_location_spinner.values = location_values
        
        world = self.db.get_world(world_id)
        if world:
            if world.user_name:
                self.user_name_input.text = world.user_name
            else:
                self.user_name_input.text = ''
            
            if world.user_location:
                self.user_location_spinner.text = world.user_location
            else:
                self.user_location_spinner.text = '未设置'
    
    def save_settings(self, instance):
        user_name = self.user_name_input.text.strip()
        user_location = self.user_location_spinner.text
        
        if user_location and user_location != '未设置':
            clean_location = user_location.strip()
            if clean_location.startswith('└'):
                clean_location = clean_location[1:].strip()
            if clean_location.startswith('【') and clean_location.endswith('】'):
                clean_location = clean_location[1:-1]
            user_location = clean_location
        else:
            user_location = None
        
        self.db.update_world(self.world_id, user_name=user_name, user_location=user_location)
        
        popup = create_message_popup('保存成功')
        popup.open()
    
    def go_back(self, instance):
        self.manager.current = 'character_list'


class CharacterEditScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.character_id = None
        self.avatar_path = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='编辑角色',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(16),
            padding=[dp(16), dp(16), dp(16), dp(16)]
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        name_label = Label(
            text='角色姓名',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        name_label.bind(size=name_label.setter('text_size'))
        self.content_layout.add_widget(name_label)
        
        self.name_input = AutoExpandTextInput(
            hint_text='输入角色姓名',
            initial_height=dp(50)
        )
        self.content_layout.add_widget(self.name_input)
        
        gender_label = Label(
            text='性别',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        gender_label.bind(size=gender_label.setter('text_size'))
        self.content_layout.add_widget(gender_label)
        
        gender_container = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(12)
        )
        
        self.male_btn = Button(
            text='男',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['text_hint']
        )
        self.male_btn.bind(on_press=lambda x: self.set_gender('male'))
        
        self.female_btn = Button(
            text='女',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['primary']
        )
        self.female_btn.bind(on_press=lambda x: self.set_gender('female'))
        
        self.other_btn = Button(
            text='其他',
            font_name=FONT_NAME,
            font_size=dp(16),
            background_normal='',
            background_color=COLORS['text_hint']
        )
        self.other_btn.bind(on_press=lambda x: self.set_gender('other'))
        
        gender_container.add_widget(self.male_btn)
        gender_container.add_widget(self.female_btn)
        gender_container.add_widget(self.other_btn)
        self.content_layout.add_widget(gender_container)
        
        self.gender = 'female'
        
        avatar_label = Label(
            text='头像',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        avatar_label.bind(size=avatar_label.setter('text_size'))
        self.content_layout.add_widget(avatar_label)
        
        self.avatar_container = BoxLayout(
            size_hint_y=None,
            height=dp(120),
            padding=[dp(0), dp(8), dp(0), dp(8)]
        )
        with self.avatar_container.canvas.before:
            Color(*COLORS['surface_light'])
            self._avatar_bg = RoundedRectangle(pos=self.avatar_container.pos, size=self.avatar_container.size, radius=[dp(12)])
        self.avatar_container.bind(pos=self._update_avatar_bg, size=self._update_avatar_bg)
        
        self.avatar_display = BoxLayout()
        self.avatar_container.add_widget(self.avatar_display)
        self.content_layout.add_widget(self.avatar_container)
        
        self.avatar_container.bind(on_touch_down=self.on_avatar_touch)
        
        desc_label = Label(
            text='角色介绍',
            font_size=dp(14),
            font_name=FONT_NAME,
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle'
        )
        desc_label.bind(size=desc_label.setter('text_size'))
        self.content_layout.add_widget(desc_label)
        
        self.desc_input = AutoExpandTextInput(
            hint_text='输入角色介绍',
            initial_height=dp(100)
        )
        self.content_layout.add_widget(self.desc_input)
        
        bg_btn = Button(
            text='选择背景图',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['surface_light'],
            color=COLORS['primary'],
            size_hint_y=None,
            height=dp(50)
        )
        bg_btn.bind(on_press=self.open_background_select)
        self.content_layout.add_widget(bg_btn)
        
        location_row = BoxLayout(
            size_hint_y=None,
            height=dp(36),
            spacing=dp(8)
        )
        
        location_label_container = BoxLayout(
            size_hint_x=None,
            width=dp(70)
        )
        location_label = Label(
            text='角色地点:',
            font_name=FONT_NAME,
            font_size=dp(13),
            color=COLORS['text_secondary'],
            halign='left',
            valign='middle'
        )
        location_label.bind(size=location_label.setter('text_size'))
        location_label_container.add_widget(location_label)
        
        self.location_spinner = ChineseSpinner(
            text='未设置',
            font_name=FONT_NAME,
            font_size=dp(13),
            size_hint_x=1,
            height=dp(36),
            values=['未设置'],
            background_normal='',
            background_color=(0.95, 0.95, 0.95, 1),
            color=COLORS['text']
        )
        
        location_row.add_widget(location_label_container)
        location_row.add_widget(self.location_spinner)
        self.content_layout.add_widget(location_row)
        
        self.memory_btn_container = BoxLayout(
            size_hint_y=None,
            height=dp(50)
        )
        self.content_layout.add_widget(self.memory_btn_container)
        
        self.scroll_view.add_widget(self.content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        save_container = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        with save_container.canvas.before:
            Color(*COLORS['surface'])
            self._save_bg = RoundedRectangle(pos=save_container.pos, size=save_container.size)
        save_container.bind(pos=self._update_save_bg, size=self._update_save_bg)
        
        save_btn = Button(
            text='保存',
            font_size=dp(16),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        save_btn.bind(on_press=self.save_character)
        save_container.add_widget(save_btn)
        self.root_layout.add_widget(save_container)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_avatar_bg(self, instance, value):
        self._avatar_bg.pos = instance.pos
        self._avatar_bg.size = instance.size
    
    def _update_save_bg(self, instance, value):
        self._save_bg.pos = instance.pos
        self._save_bg.size = instance.size
    
    def set_character(self, world_id, character_id):
        self.world_id = world_id
        self.character_id = character_id
        self.avatar_path = None
        
        primary_locations = self.db.get_primary_locations(world_id)
        location_values = ['未设置']
        
        if primary_locations:
            for primary_loc in primary_locations:
                sub_locations = self.db.get_sub_locations(primary_loc.id)
                if sub_locations:
                    location_values.append(f"【{primary_loc.name}】")
                    for sub_loc in sub_locations:
                        location_values.append(f"  └ {sub_loc.name}")
                else:
                    location_values.append(f"【{primary_loc.name}】")
        
        self.location_spinner.values = location_values
        
        if character_id:
            character = self.db.get_character(character_id)
            if character:
                self.title_label.text = character.name
                self.name_input.text = character.name or ''
                self.desc_input.text = character.description or ''
                self.gender = character.gender or 'female'
                self.set_gender(self.gender)
                
                if character.location:
                    self.location_spinner.text = character.location
                else:
                    self.location_spinner.text = '未设置'
                
                if character.avatar_path and os.path.exists(character.avatar_path):
                    self.avatar_path = character.avatar_path
                
                self.memory_btn_container.clear_widgets()
                memory_btn = Button(
                    text='查看记忆',
                    font_size=dp(14),
                    font_name=FONT_NAME,
                    background_normal='',
                    background_color=COLORS['surface_light'],
                    color=COLORS['primary']
                )
                memory_btn.bind(on_press=self.open_memory_screen)
                self.memory_btn_container.add_widget(memory_btn)
        else:
            self.title_label.text = '新角色'
            self.name_input.text = ''
            self.desc_input.text = ''
            self.gender = 'female'
            self.set_gender('female')
            self.avatar_path = None
            self.location_spinner.text = '未设置'
            self.memory_btn_container.clear_widgets()
        
        self.update_avatar_display()
    
    def set_gender(self, gender):
        self.gender = gender
        self.male_btn.background_color = COLORS['primary'] if gender == 'male' else COLORS['text_hint']
        self.female_btn.background_color = COLORS['primary'] if gender == 'female' else COLORS['text_hint']
        self.other_btn.background_color = COLORS['primary'] if gender == 'other' else COLORS['text_hint']
    
    def update_avatar_display(self):
        self.avatar_display.clear_widgets()
        
        if self.avatar_path and os.path.exists(self.avatar_path):
            avatar_img = Image(
                source=self.avatar_path,
                size_hint=(None, None),
                size=(dp(100), dp(100))
            )
            self.avatar_display.add_widget(avatar_img)
        else:
            placeholder = Label(
                text='点击上传头像',
                font_name=FONT_NAME,
                font_size=dp(14),
                color=COLORS['text_hint']
            )
            self.avatar_display.add_widget(placeholder)
    
    def on_avatar_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.upload_avatar()
            return True
        return False
    
    def upload_avatar(self):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title='选择头像图片',
            filetypes=[('图片文件', '*.png *.jpg *.jpeg *.gif *.bmp')]
        )
        root.destroy()
        
        if file_path:
            if hasattr(self.manager, 'avatar_crop_screen'):
                self.manager.avatar_crop_screen.set_image(
                    file_path,
                    on_crop_complete=self.on_avatar_cropped
                )
                self.manager.current = 'avatar_crop'
    
    def on_avatar_cropped(self, cropped_path):
        self.avatar_path = cropped_path
        self.update_avatar_display()
    
    def open_memory_screen(self, instance):
        if hasattr(self.manager, 'character_memory_screen') and self.character_id:
            self.manager.character_memory_screen.set_character(self.world_id, self.character_id)
            self.manager.current = 'character_memory'
    
    def open_background_select(self, instance):
        if hasattr(self.manager, 'character_background_screen'):
            self.manager.character_background_screen.set_character(
                self.world_id,
                self.character_id
            )
            self.manager.current = 'character_background'
    
    def save_character(self, instance):
        name = self.name_input.text.strip()
        if not name:
            popup = create_message_popup('请输入角色姓名')
            popup.open()
            return
        
        description = self.desc_input.text.strip()
        location = self.location_spinner.text
        
        if location and location != '未设置':
            clean_location = location.strip()
            if clean_location.startswith('└'):
                clean_location = clean_location[1:].strip()
            if clean_location.startswith('【') and clean_location.endswith('】'):
                clean_location = clean_location[1:-1]
            location = clean_location
        else:
            location = None
        
        if self.character_id:
            self.db.update_character(
                self.character_id,
                name=name,
                description=description,
                gender=self.gender,
                avatar_path=self.avatar_path,
                location=location
            )
        else:
            character = self.db.create_character(
                self.world_id,
                name=name,
                description=description,
                gender=self.gender,
                avatar_path=self.avatar_path,
                location=location
            )
            self.character_id = character.id
            self.title_label.text = name
        
        popup = create_message_popup('保存成功')
        popup.open()
    
    def go_back(self, instance):
        if hasattr(self.manager, 'character_list_screen'):
            self.manager.character_list_screen.load_characters()
        self.manager.current = 'character_list'


class AvatarCropScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_path = None
        self.on_crop_complete = None
        self._touch_start_pos = None
        self._crop_size = 200
        self._crop_center = [200, 200]
        self._touches = {}
        self._initial_distance = None
        self._initial_crop_size = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='取消',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='裁剪头像',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        confirm_btn = Button(
            text='确定',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        confirm_btn.bind(on_press=self.confirm_crop)
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(confirm_btn)
        self.root_layout.add_widget(header)
        
        self.crop_container = FloatLayout()
        
        self.image_display = Image(
            source='',
            size_hint=(None, None),
            pos=(0, 0),
            allow_stretch=True
        )
        self.crop_container.add_widget(self.image_display)
        
        self.crop_mask = Image(
            source='',
            size_hint=(1, 1),
            pos=(0, 0),
            allow_stretch=True
        )
        self.crop_container.add_widget(self.crop_mask)
        
        self.crop_frame = Widget()
        self.crop_container.add_widget(self.crop_frame)
        
        self.root_layout.add_widget(self.crop_container)
        
        hint_label = Label(
            text='拖动图片调整位置，双指缩放调整裁剪框大小',
            font_name=FONT_NAME,
            font_size=dp(12),
            color=COLORS['text_hint'],
            size_hint_y=None,
            height=dp(40)
        )
        self.root_layout.add_widget(hint_label)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def set_image(self, image_path, on_crop_complete=None):
        self.image_path = image_path
        self.on_crop_complete = on_crop_complete
        self._touches = {}
        
        if image_path and os.path.exists(image_path):
            self.image_display.source = image_path
            Clock.schedule_once(self._init_crop_frame, 0.1)
    
    def _init_crop_frame(self, dt):
        if not self.image_path:
            return
        
        container_size = self.crop_container.size
        container_center_x = container_size[0] / 2
        container_center_y = container_size[1] / 2
        
        self._crop_size = min(container_size[0], container_size[1]) * 0.6
        self._crop_center = [container_center_x, container_center_y]
        
        try:
            from PIL import Image as PILImage
            with PILImage.open(self.image_path) as img:
                img_width, img_height = img.size
        except:
            img_width, img_height = container_size[0], container_size[1]
        
        scale_x = container_size[0] / img_width
        scale_y = container_size[1] / img_height
        scale = min(scale_x, scale_y)
        
        display_width = img_width * scale
        display_height = img_height * scale
        
        self.image_display.size = (display_width, display_height)
        self.image_display.pos = (
            (container_size[0] - display_width) / 2,
            (container_size[1] - display_height) / 2
        )
        
        self._update_mask_image()
        self._draw_crop_frame()
    
    def _update_mask_image(self):
        container_size = self.crop_container.size
        size = self._crop_size
        cx, cy = self._crop_center
        
        try:
            from PIL import Image as PILImage, ImageDraw
            
            mask = PILImage.new('RGBA', (int(container_size[0]), int(container_size[1])), (0, 0, 0, 128))
            draw = ImageDraw.Draw(mask)
            
            pil_cx = int(cx)
            pil_cy = int(container_size[1] - cy)
            
            draw.ellipse(
                (int(pil_cx - size/2), int(pil_cy - size/2), int(pil_cx + size/2), int(pil_cy + size/2)),
                fill=(0, 0, 0, 0)
            )
            
            mask_path = os.path.join(os.path.dirname(self.image_path), 'crop_mask.png')
            mask.save(mask_path)
            self.crop_mask.source = mask_path
            self.crop_mask.reload()
        except Exception as e:
            print(f"Mask error: {e}")
    
    def _draw_crop_frame(self):
        self.crop_frame.canvas.clear()
        
        size = self._crop_size
        cx, cy = self._crop_center
        
        with self.crop_frame.canvas:
            Color(1, 1, 1, 1)
            Line(circle=(cx, cy, size/2), width=dp(2))
    
    def on_touch_down(self, touch):
        if self.crop_container.collide_point(*touch.pos):
            self._touches[touch.id] = (touch.x, touch.y)
            
            if len(self._touches) == 2:
                points = list(self._touches.values())
                dx = points[0][0] - points[1][0]
                dy = points[0][1] - points[1][1]
                self._initial_distance = (dx * dx + dy * dy) ** 0.5
                self._initial_crop_size = self._crop_size
            else:
                self._touch_start_pos = (touch.x, touch.y)
            
            return True
        return super().on_touch_down(touch)
    
    def on_touch_move(self, touch):
        if touch.id in self._touches:
            self._touches[touch.id] = (touch.x, touch.y)
            
            if len(self._touches) == 2 and self._initial_distance:
                points = list(self._touches.values())
                dx = points[0][0] - points[1][0]
                dy = points[0][1] - points[1][1]
                current_distance = (dx * dx + dy * dy) ** 0.5
                
                if self._initial_distance > 0:
                    scale = current_distance / self._initial_distance
                    new_size = self._initial_crop_size * scale
                    
                    min_size = dp(80)
                    max_size = min(self.crop_container.size[0], self.crop_container.size[1]) * 0.9
                    self._crop_size = max(min_size, min(max_size, new_size))
                    
                    self._update_mask_image()
                    self._draw_crop_frame()
            elif self._touch_start_pos:
                dx = touch.x - self._touch_start_pos[0]
                dy = touch.y - self._touch_start_pos[1]
                
                self._crop_center[0] += dx
                self._crop_center[1] += dy
                
                self._touch_start_pos = (touch.x, touch.y)
                self._update_mask_image()
                self._draw_crop_frame()
            
            return True
        return super().on_touch_move(touch)
    
    def on_touch_up(self, touch):
        if touch.id in self._touches:
            del self._touches[touch.id]
        
        if len(self._touches) < 2:
            self._initial_distance = None
            self._initial_crop_size = None
        
        self._touch_start_pos = None
        return super().on_touch_up(touch)
    
    def confirm_crop(self, instance):
        if not self.image_path:
            self.go_back(None)
            return
        
        try:
            from PIL import Image as PILImage
            
            with PILImage.open(self.image_path) as img:
                img_width, img_height = img.size
                
                container_size = self.crop_container.size
                crop_size = self._crop_size
                center_x, center_y = self._crop_center
                
                print(f"Debug: img_width={img_width}, img_height={img_height}")
                print(f"Debug: container_size={container_size}")
                print(f"Debug: crop_center=({center_x}, {center_y}), crop_size={crop_size}")
                print(f"Debug: image_display.pos={self.image_display.pos}, image_display.size={self.image_display.size}")
                
                crop_left = center_x - crop_size / 2
                crop_top = center_y - crop_size / 2
                crop_right = center_x + crop_size / 2
                crop_bottom = center_y + crop_size / 2
                
                print(f"Debug: crop box in container=({crop_left}, {crop_top}, {crop_right}, {crop_bottom})")
                
                img_pos_x = self.image_display.pos[0]
                img_pos_y = self.image_display.pos[1]
                img_display_width = self.image_display.size[0]
                img_display_height = self.image_display.size[1]
                
                left = int((crop_left - img_pos_x) * img_width / img_display_width)
                top = int((container_size[1] - crop_bottom - img_pos_y) * img_height / img_display_height)
                right = int((crop_right - img_pos_x) * img_width / img_display_width)
                bottom = int((container_size[1] - crop_top - img_pos_y) * img_height / img_display_height)
                
                left = max(0, left)
                top = max(0, top)
                right = min(img_width, right)
                bottom = min(img_height, bottom)
                
                print(f"Debug: crop box in image=({left}, {top}, {right}, {bottom})")
                
                cropped = img.crop((left, top, right, bottom))
                
                output_size = 200
                cropped = cropped.resize((output_size, output_size), PILImage.LANCZOS)
                
                output_path = os.path.join(os.path.dirname(self.image_path), f'avatar_cropped_{os.path.basename(self.image_path)}')
                cropped.save(output_path)
                
                if self.on_crop_complete:
                    self.on_crop_complete(output_path)
        
        except Exception as e:
            print(f"Crop error: {e}")
        
        self.go_back(None)
    
    def go_back(self, instance):
        self.manager.current = 'character_edit'


class BackgroundImageCard(BoxLayout):
    def __init__(self, bg_image, on_delete=None, on_tags_update=None, on_image_update=None, **kwargs):
        super().__init__(**kwargs)
        self.bg_image = bg_image
        self.on_delete = on_delete
        self.on_tags_update = on_tags_update
        self.on_image_update = on_image_update
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(80)
        self.spacing = dp(12)
        self.padding = [dp(12), dp(8), dp(12), dp(8)]
        
        self._long_press_triggered = False
        self._long_press_event = None
        self._touch_on_image = False
        
        with self.canvas.before:
            Color(*COLORS['surface'])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        self.img_container = BoxLayout(size_hint_x=None, width=dp(64))
        with self.img_container.canvas.before:
            Color(*COLORS['primary_light'])
            self._img_bg = RoundedRectangle(pos=self.img_container.pos, size=self.img_container.size, radius=[dp(4)])
        self.img_container.bind(pos=self._update_img_bg, size=self._update_img_bg)
        
        if bg_image.image_path and os.path.exists(bg_image.image_path):
            self.img_display = Image(
                source=bg_image.image_path,
                size_hint=(None, None),
                size=(dp(64), dp(64))
            )
        else:
            self.img_display = Label(
                text='无图',
                font_name=FONT_NAME,
                font_size=dp(12),
                color=COLORS['text_hint']
            )
        
        self.img_container.add_widget(self.img_display)
        self.add_widget(self.img_container)
        
        info_layout = BoxLayout(orientation='vertical', spacing=dp(4))
        
        self.tags_label = Label(
            text=bg_image.tags or '点击添加标签',
            font_name=FONT_NAME,
            font_size=dp(14),
            color=COLORS['text'],
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(32)
        )
        self.tags_label.bind(size=self.tags_label.setter('text_size'))
        
        info_layout.add_widget(BoxLayout())
        info_layout.add_widget(self.tags_label)
        info_layout.add_widget(BoxLayout())
        self.add_widget(info_layout)
    
    def _update_bg(self, instance, value):
        self._bg.pos = instance.pos
        self._bg.size = instance.size
    
    def _update_img_bg(self, instance, value):
        self._img_bg.pos = instance.pos
        self._img_bg.size = instance.size
    
    def _update_image_display(self):
        self.img_container.clear_widgets()
        if self.bg_image.image_path and os.path.exists(self.bg_image.image_path):
            self.img_display = Image(
                source=self.bg_image.image_path,
                size_hint=(None, None),
                size=(dp(64), dp(64))
            )
        else:
            self.img_display = Label(
                text='无图',
                font_name=FONT_NAME,
                font_size=dp(12),
                color=COLORS['text_hint']
            )
        self.img_container.add_widget(self.img_display)
    
    def _trigger_long_press(self, dt):
        self._long_press_triggered = True
        if self.on_delete:
            self.on_delete(self.bg_image)
    
    def _is_touch_on_image(self, touch):
        return self.img_container.collide_point(*touch.pos)
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._long_press_triggered = False
            self._touch_on_image = self._is_touch_on_image(touch)
            self._long_press_event = Clock.schedule_once(self._trigger_long_press, 0.5)
            return True
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if self._long_press_event:
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        
        if self.collide_point(*touch.pos) and not self._long_press_triggered:
            if self._touch_on_image:
                self._change_image()
            else:
                self._edit_tags()
            return True
        return super().on_touch_up(touch)
    
    def on_touch_move(self, touch):
        if self._long_press_event and not self.collide_point(*touch.pos):
            Clock.unschedule(self._long_press_event)
            self._long_press_event = None
        return super().on_touch_move(touch)
    
    def _edit_tags(self):
        current_tags = self.bg_image.tags or ''
        
        popup = create_input_popup(
            '编辑标签',
            lambda p, text: self._save_tags(text, p),
            current_tags
        )
        popup.open()
    
    def _save_tags(self, tags_text, popup):
        if self.on_tags_update:
            self.on_tags_update(self.bg_image, tags_text)
        self.tags_label.text = tags_text or '点击添加标签'
        popup.dismiss()
    
    def _change_image(self):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title='选择背景图片',
            filetypes=[('图片文件', '*.png *.jpg *.jpeg *.gif *.bmp')]
        )
        root.destroy()
        
        if file_path and self.on_image_update:
            self.on_image_update(self.bg_image, file_path)


class CharacterBackgroundScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.world_id = None
        self.character_id = None
        self.build_ui()
    
    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        with header.canvas.before:
            Color(*COLORS['surface'])
            self._header_bg = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)
        
        back_btn = Button(
            text='返回',
            font_size=dp(14),
            font_name=FONT_NAME,
            size_hint_x=None,
            width=dp(60),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(
            text='背景图选择',
            font_size=dp(18),
            font_name=FONT_NAME,
            bold=True,
            color=COLORS['text']
        )
        
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(BoxLayout(size_hint_x=None, width=dp(60)))
        self.root_layout.add_widget(header)
        
        self.scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.bg_list = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(16), dp(8), dp(16), dp(8)]
        )
        self.bg_list.bind(minimum_height=self.bg_list.setter('height'))
        
        self.scroll_view.add_widget(self.bg_list)
        self.root_layout.add_widget(self.scroll_view)
        
        add_btn_container = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        with add_btn_container.canvas.before:
            Color(*COLORS['surface'])
            self._add_btn_bg = RoundedRectangle(pos=add_btn_container.pos, size=add_btn_container.size)
        add_btn_container.bind(pos=self._update_add_btn_bg, size=self._update_add_btn_bg)
        
        add_btn = Button(
            text='+ 添加背景图',
            font_size=dp(14),
            font_name=FONT_NAME,
            background_normal='',
            background_color=COLORS['primary'],
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46)
        )
        add_btn.bind(on_press=self.add_background)
        add_btn_container.add_widget(add_btn)
        self.root_layout.add_widget(add_btn_container)
        
        self.add_widget(self.root_layout)
    
    def _update_header_bg(self, instance, value):
        self._header_bg.pos = instance.pos
        self._header_bg.size = instance.size
    
    def _update_add_btn_bg(self, instance, value):
        self._add_btn_bg.pos = instance.pos
        self._add_btn_bg.size = instance.size
    
    def set_character(self, world_id, character_id):
        self.world_id = world_id
        self.character_id = character_id
        self.load_backgrounds()
    
    def load_backgrounds(self):
        self.bg_list.clear_widgets()
        
        if not self.character_id:
            return
        
        backgrounds = self.db.get_background_images(self.character_id)
        
        if not backgrounds:
            empty_label = Label(
                text='暂无背景图\n点击下方按钮添加',
                font_size=dp(14),
                font_name=FONT_NAME,
                color=COLORS['text_hint'],
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(200)
            )
            empty_label.bind(size=empty_label.setter('text_size'))
            self.bg_list.add_widget(empty_label)
        else:
            for bg in backgrounds:
                bg_card = BackgroundImageCard(
                    bg,
                    on_delete=self.delete_background,
                    on_tags_update=self.update_tags,
                    on_image_update=self.update_image
                )
                self.bg_list.add_widget(bg_card)
    
    def on_enter(self):
        self.load_backgrounds()
    
    def add_background(self, instance):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title='选择背景图片',
            filetypes=[('图片文件', '*.png *.jpg *.jpeg *.gif *.bmp')]
        )
        root.destroy()
        
        if file_path and self.world_id and self.character_id:
            self.db.save_background_image(
                self.world_id,
                self.character_id,
                file_path
            )
            self.load_backgrounds()
    
    def update_tags(self, bg_image, tags):
        self.db.update_background_image(bg_image.id, tags=tags)
    
    def update_image(self, bg_image, new_path):
        self.db.update_background_image(bg_image.id, image_path=new_path)
        bg_image.image_path = new_path
        self.load_backgrounds()
    
    def delete_background(self, bg_image):
        popup = create_confirm_popup(
            '确定要删除这张背景图吗？\n此操作不可恢复',
            lambda p: self._do_delete_background(bg_image.id, p),
            confirm_text='删除',
            is_danger=True
        )
        popup.open()
    
    def _do_delete_background(self, bg_id, popup):
        self.db.delete_background_image(bg_id)
        popup.dismiss()
        self.load_backgrounds()
    
    def go_back(self, instance):
        self.manager.current = 'character_edit'


class MobileApp(App):
    def build(self):
        self.title = '旮旯GAME'
        
        sm = ScreenManager()
        
        world_list_screen = WorldListScreen(name='world_list')
        world_edit_screen = WorldEditScreen(name='world_edit')
        api_settings_screen = ApiSettingsScreen(name='api_settings')
        chat_screen = ChatScreen(name='chat')
        script_settings_screen = ScriptSettingsScreen(name='script_settings')
        location_change_screen = LocationChangeScreen(name='location_change')
        location_list_screen = LocationListScreen(name='location_list')
        location_edit_screen = LocationEditScreen(name='location_edit')
        map_select_screen = MapSelectScreen(name='map_select')
        transport_screen = TransportScreen(name='transport')
        character_list_screen = CharacterListScreen(name='character_list')
        character_edit_screen = CharacterEditScreen(name='character_edit')
        user_settings_screen = UserSettingsScreen(name='user_settings')
        avatar_crop_screen = AvatarCropScreen(name='avatar_crop')
        character_background_screen = CharacterBackgroundScreen(name='character_background')
        health_screen = HealthScreen(name='health')
        user_health_screen = UserHealthScreen(name='user_health')
        call_manager_screen = CallManagerScreen(name='call_manager')
        character_memory_screen = CharacterMemoryScreen(name='character_memory')
        world_memory_screen = WorldMemoryScreen(name='world_memory')
        chat_menu_screen = ChatMenuScreen(name='chat_menu')
        
        sm.add_widget(world_list_screen)
        sm.add_widget(world_edit_screen)
        sm.add_widget(api_settings_screen)
        sm.add_widget(chat_screen)
        sm.add_widget(script_settings_screen)
        sm.add_widget(location_change_screen)
        sm.add_widget(location_list_screen)
        sm.add_widget(location_edit_screen)
        sm.add_widget(map_select_screen)
        sm.add_widget(transport_screen)
        sm.add_widget(character_list_screen)
        sm.add_widget(character_edit_screen)
        sm.add_widget(user_settings_screen)
        sm.add_widget(avatar_crop_screen)
        sm.add_widget(character_background_screen)
        sm.add_widget(health_screen)
        sm.add_widget(user_health_screen)
        sm.add_widget(call_manager_screen)
        sm.add_widget(character_memory_screen)
        sm.add_widget(world_memory_screen)
        sm.add_widget(chat_menu_screen)
        
        sm.health_screen = health_screen
        sm.user_health_screen = user_health_screen
        sm.call_manager_screen = call_manager_screen
        sm.character_memory_screen = character_memory_screen
        sm.world_memory_screen = world_memory_screen
        sm.chat_menu_screen = chat_menu_screen
        
        sm.world_list_screen = world_list_screen
        sm.world_edit_screen = world_edit_screen
        sm.api_settings_screen = api_settings_screen
        sm.chat_screen = chat_screen
        sm.script_settings_screen = script_settings_screen
        sm.location_change_screen = location_change_screen
        sm.location_list_screen = location_list_screen
        sm.location_edit_screen = location_edit_screen
        sm.map_select_screen = map_select_screen
        sm.transport_screen = transport_screen
        sm.character_list_screen = character_list_screen
        sm.character_edit_screen = character_edit_screen
        sm.user_settings_screen = user_settings_screen
        sm.avatar_crop_screen = avatar_crop_screen
        sm.character_background_screen = character_background_screen
        
        return sm


if __name__ == '__main__':
    MobileApp().run()
