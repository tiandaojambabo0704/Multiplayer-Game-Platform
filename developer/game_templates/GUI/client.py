# developer/game_templates/GUI/client.py
import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox
import sys
import time

class GUIGameClientTemplate:
    def __init__(self, host='localhost', port=6000):
        """
        Initialize GUI game client
        """
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        
        self.player_num = None
        self.player_info = None
        self.game_state = None
        self.current_turn = None
        self.game_over = False
        
        self.root = tk.Tk()
        self.setup_ui()
    
    def get_game_name(self):
        """
        Override to return game name for window title
        """
        return "GUI Game Template"
    
    def setup_ui(self):
        """
        Override to setup game-specific UI
        """
        self.root.title(self.get_game_name())
        self.root.geometry("500x400")
        
        # Connection status
        self.status_label = tk.Label(self.root, text="Connecting...", font=("Arial", 12))
        self.status_label.pack(pady=10)
        
        # Game info
        self.info_label = tk.Label(self.root, text="", font=("Arial", 10))
        self.info_label.pack(pady=5)
        
        # Game board/area
        self.game_frame = tk.Frame(self.root)
        self.game_frame.pack(pady=20)
        
        self.create_game_widgets()
        
        # Chat/status area
        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.chat_text = tk.Text(self.chat_frame, height=6, width=40, state=tk.DISABLED)
        self.chat_text.pack(side=tk.LEFT, padx=5)
        
        self.chat_scroll = tk.Scrollbar(self.chat_frame)
        self.chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_text.config(yscrollcommand=self.chat_scroll.set)
        self.chat_scroll.config(command=self.chat_text.yview)
        
        # Chat input
        self.chat_input_frame = tk.Frame(self.root)
        self.chat_input_frame.pack(pady=5)
        
        self.chat_entry = tk.Entry(self.chat_input_frame, width=40)
        self.chat_entry.pack(side=tk.LEFT, padx=5)
        self.chat_entry.bind("<Return>", self.send_chat_message)
        
        self.chat_button = tk.Button(self.chat_input_frame, text="Send", command=self.send_chat_message)
        self.chat_button.pack(side=tk.LEFT)
    
    def create_game_widgets(self):
        """
        Override to create game-specific widgets
        """
        # Example: Create a placeholder label
        placeholder = tk.Label(self.game_frame, text="Game Area", font=("Arial", 14))
        placeholder.pack()
    
    def connect(self):
        """
        Connect to game server
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
        except Exception as e:
            messagebox.showerror("Connection Error", f"Cannot connect to server: {e}")
            return False
    
    def send_message(self, data):
        """
        Send JSON message to server
        """
        if not self.connected:
            return False
        
        try:
            message = json.dumps(data) + '\n'
            self.socket.sendall(message.encode())
            return True
        except:
            return False
    
    def receive_messages(self):
        """
        Receive messages from server
        """
        buffer = ''
        while self.connected:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        self.handle_server_message(line)
            except:
                break
        
        if not self.game_over:
            self.root.after(0, self.show_disconnection_message)
    
    def handle_server_message(self, message_str):
        """
        Handle messages from server
        """
        try:
            message = json.loads(message_str)
            self.root.after(0, lambda: self.process_message(message))
        except json.JSONDecodeError:
            print(f"Invalid message: {message_str}")
    
    def process_message(self, message):
        """
        Process message from server
        """
        msg_type = message.get('type')
        
        if msg_type == 'init':
            self.handle_init_message(message)
        elif msg_type == 'start':
            self.handle_start_message(message)
        elif msg_type == 'turn':
            self.handle_turn_message(message)
        elif msg_type == 'move':
            self.handle_move_message(message)
        elif msg_type == 'chat':
            self.handle_chat_message(message)
        elif msg_type == 'end':
            self.handle_end_message(message)
        elif msg_type == 'error':
            self.handle_error_message(message)
        elif msg_type == 'update':
            self.handle_update_message(message)
    
    def handle_init_message(self, message):
        """
        Handle initialization message
        """
        self.player_num = message.get('player')
        self.player_info = message.get('player_info', {})
        self.game_state = message.get('game_state', {})
        
        self.status_label.config(text=f"Connected as Player {self.player_num + 1}")
        self.update_game_display()
    
    def handle_start_message(self, message):
        """
        Handle game start message
        """
        self.game_state = message.get('game_state', {})
        self.info_label.config(text=f"Game started!")
        self.update_game_display()
    
    def handle_turn_message(self, message):
        """
        Handle turn change message
        """
        self.current_turn = message.get('player')
        if self.current_turn == self.player_num:
            self.info_label.config(text="Your turn!", fg='green')
            self.enable_player_input(True)
        else:
            self.info_label.config(text="Waiting for opponent...", fg='red')
            self.enable_player_input(False)
    
    def handle_move_message(self, message):
        """
        Override to handle move messages
        """
        move_data = message.get('move_data', {})
        self.game_state = message.get('game_state', {})
        self.update_game_display()
    
    def handle_chat_message(self, message):
        """
        Handle chat messages
        """
        player = message.get('player')
        text = message.get('message', '')
        timestamp = message.get('timestamp', time.strftime("%H:%M:%S"))
        
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"[{timestamp}] Player {player + 1}: {text}\n")
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)
    
    def handle_end_message(self, message):
        """
        Handle game end message
        """
        self.game_over = True
        result = message.get('result', {})
        self.show_game_result(result)
    
    def handle_error_message(self, message):
        """
        Handle error messages
        """
        error_msg = message.get('message', 'An error occurred')
        messagebox.showwarning("Error", error_msg)
    
    def handle_update_message(self, message):
        """
        Handle update messages
        """
        self.game_state = message.get('game_state', {})
        self.update_game_display()
    
    def update_game_display(self):
        """
        Override to update game display based on game state
        """
        # Update UI based on current game state
        pass
    
    def enable_player_input(self, enabled):
        """
        Override to enable/disable player input controls
        """
        pass
    
    def player_action(self, action_data):
        """
        Send player action to server
        """
        self.send_message({
            'type': 'action',
            **action_data
        })
    
    def player_move(self, move_data):
        """
        Send player move to server
        """
        self.send_message({
            'type': 'move',
            **move_data
        })
    
    def send_chat_message(self, event=None):
        """
        Send chat message
        """
        text = self.chat_entry.get().strip()
        if text:
            self.send_message({
                'type': 'chat',
                'text': text,
                'timestamp': time.strftime("%H:%M:%S")
            })
            self.chat_entry.delete(0, tk.END)
    
    def show_game_result(self, result):
        """
        Override to show game result
        """
        messagebox.showinfo("Game Over", f"Game finished: {result}")
        self.root.quit()
    
    def show_disconnection_message(self):
        """
        Show disconnection message
        """
        if not self.game_over:
            messagebox.showerror("Disconnected", "Lost connection to server")
            self.root.quit()
    
    def run(self):
        """
        Run the client
        """
        if self.connect():
            self.root.mainloop()
        
        # Cleanup
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

if __name__ == '__main__':
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    client = GUIGameClientTemplate(host, port)
    client.run()