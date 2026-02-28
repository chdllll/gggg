from kivy import Config
Config.set('graphics', 'orientation', 'portrait')
Config.set('graphics', 'resizable', False)
Config.set('kivy', 'keyboard_mode', 'system')

import os
import sys

if hasattr(sys, '_MEIPASS'):
    resource_path = os.path.join(sys._MEIPASS, 'data')
    if os.path.exists(resource_path):
        os.environ['KIVY_NO_ARGS'] = '1'

from mobile_main import MobileApp

if __name__ == '__main__':
    app = MobileApp()
    app.run()
