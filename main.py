from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivy.clock import Clock
import socket
import threading

# Configuration: Update to your server's local or web public IP address
SERVER_IP = "127.0.0.1" 
SERVER_PORT = 55555

class MenuScreen(MDScreen):
    """The landing interface screen handling login and code entry verification."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', padding=30, spacing=20, size_hint_y=None, pos_hint={"center_y": 0.5})
        
        self.nick_input = MDTextField(hint_text="Choose Username", icon_right="account")
        self.code_input = MDTextField(hint_text="5-Digit Invite Code (For Join)", icon_right="key")
        
        btn_create = MDRaisedButton(text="Create New Room", pos_hint={"center_x": 0.5}, on_release=self.create_room)
        btn_join = MDRaisedButton(text="Join Existing Room", pos_hint={"center_x": 0.5}, on_release=self.join_room)
        
        self.status_lbl = MDLabel(text="", halign="center", theme_text_color="Error")
        
        layout.add_widget(self.nick_input)
        layout.add_widget(self.code_input)
        layout.add_widget(btn_create)
        layout.add_widget(btn_join)
        layout.add_widget(self.status_lbl)
        self.add_widget(layout)

    def verify_inputs(self):
        return bool(self.nick_input.text.strip())

    def create_room(self, instance):
        if self.verify_inputs():
            self.manager.app_config_connect(self.nick_input.text.strip(), "CREATE", "")
        else:
            self.status_lbl.text = "Username missing!"

    def join_room(self, instance):
        code = self.code_input.text.strip().upper()
        if self.verify_inputs() and code:
            self.manager.app_config_connect(self.nick_input.text.strip(), "JOIN", code)
        else:
            self.status_lbl.text = "Fill all credentials!"

class ActiveChatScreen(MDScreen):
    """The secondary chat feed window displaying scrolling message boxes."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        main_layout = MDBoxLayout(orientation='vertical', padding=15, spacing=10)
        
        self.title_lbl = MDLabel(text="Room: Connecting...", size_hint_y=None, height="30dp", bold=True, halign="center")
        
        self.scroll = MDScrollView()
        self.chat_feed = MDBoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        self.chat_feed.bind(minimum_height=self.chat_feed.setter('height'))
        self.scroll.add_widget(self.chat_feed)
        
        input_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height="50dp", spacing=10)
        self.msg_field = MDTextField(hint_text="Write a message...", size_hint_x=0.85)
        send_btn = MDIconButton(icon="send", size_hint_x=0.15, on_release=self.send_text_payload)
        input_row.add_widget(self.msg_field)
        input_row.add_widget(send_btn)
        
        main_layout.add_widget(self.title_lbl)
        main_layout.add_widget(self.scroll)
        main_layout.add_widget(input_row)
        self.add_widget(main_layout)

    def update_title(self, code_text):
        self.title_lbl.text = f"Room Code Invite ID: {code_text}"

    def send_text_payload(self, instance):
        text = self.msg_field.text.strip()
        if text:
            self.manager.send_socket_data(text)
            # Instantly mirror sender text locally on UI screen thread
            self.add_message_bubble(f"You: {text}")
            self.msg_field.text = ""

    def add_message_bubble(self, text):
        lbl = MDLabel(text=text, size_hint_y=None, height="35dp", theme_text_color="Secondary")
        self.chat_feed.add_widget(lbl)

class ChatAppManager(MDScreenManager):
    """The system coordinator handling socket state changes safely across background loops."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client_socket = None
        self.menu = MenuScreen(name="menu")
        self.chat = ActiveChatScreen(name="chat")
        self.add_widget(self.menu)
        self.add_widget(self.chat)

    def app_config_connect(self, nick, action, target_room):
        threading.Thread(target=self.network_handshake, args=(nick, action, target_room), daemon=True).start()

    def network_handshake(self, nick, action, target_room):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
            
            payload = f"{nick}|{action}|{target_room}"
            self.client_socket.send(payload.encode('utf-8'))
            
            response = self.client_socket.recv(1024).decode('utf-8')
            status, code = response.split('|')
            
            if status in ["CREATED", "JOINED"]:
                # Switch main layout view frame safely via target UI scheduling clock
                Clock.schedule_once(lambda dt: self.switch_to_chat(code))
                threading.Thread(target=self.receive_loop, daemon=True).start()
            else:
                Clock.schedule_once(lambda dt: self.update_menu_error(code))
        except:
            Clock.schedule_once(lambda dt: self.update_menu_error("Server offline! Check IP."))

    def switch_to_chat(self, code):
        self.chat.update_title(code)
        self.current = "chat"

    def update_menu_error(self, text):
        self.menu.status_lbl.text = text

    def receive_loop(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    Clock.schedule_once(lambda dt, msg=message: self.chat.add_message_bubble(msg))
                else:
                    break
            except:
                break

    def send_socket_data(self, text):
        try:
            self.client_socket.send(text.encode('utf-8'))
        except:
            pass

class MobileChatApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.theme_style = "Dark" # Modern sleek black layout background style
        return ChatAppManager()

if __name__ == "__main__":
    MobileChatApp().run()
