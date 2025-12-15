# developer/game_templates/Multiplayer/client.py
import socket
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox
import time
import sys

class MultiplayerGUIClientTemplate:
    def __init__(self, host='localhost', port=6000):
        """
        Initialize multiplayer GUI game client
        """
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.running = True
        
        # Player info
        self.player_id = None
        self.player_name = ""
        self.player_ready = False
        
        # Game state
        self.game_state = {}
        self.scores = {}
        self.players = {}
        self.current_round = 0
        self.max_rounds = 1
        self.game_started = False
        
        # UI
        self.root = tk.Tk()
        self.setup_ui()
    
    def get_game_name(self):
        """
        Override to return game name for window title
        """
        return "Multiplayer Game Template"
    
    def setup_ui(self):
        """
        Setup the main UI
        """
        self.root.title(self.get_game_name())
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        
        # Top status bar
        self.create_status_bar()
        
        # Main game area
        self.create_game_area()
        
        # Right sidebar
        self.create_sidebar()
        
        # Bottom chat/control area
        self.create_chat_area()
    
    def create_status_bar(self):
        """
        Create top status bar
        """
        status_frame = ttk.Frame(self.root, relief=tk.RAISED, borderwidth=1)
        status_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=(0, 5))
        
        # Connection status
        self.status_label = ttk.Label(status_frame, text="Connecting...", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Round info
        self.round_label = ttk.Label(status_frame, text="Round: 0/0", font=("Arial", 10))
        self.round_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Game phase
        self.phase_label = ttk.Label(status_frame, text="Lobby", font=("Arial", 10, "bold"))
        self.phase_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Ready status
        self.ready_status_label = ttk.Label(status_frame, text="Not Ready", font=("Arial", 10))
        self.ready_status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Spacer
        ttk.Frame(status_frame, width=20).pack(side=tk.LEFT)
        
        # Name entry
        name_frame = ttk.Frame(status_frame)
        name_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.name_entry = ttk.Entry(name_frame, width=15)
        self.name_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.name_entry.insert(0, "Player")
        
        self.set_name_btn = ttk.Button(name_frame, text="Set Name", 
                                      command=self.set_name, state=tk.DISABLED)
        self.set_name_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.ready_btn = ttk.Button(name_frame, text="Ready", 
                                   command=self.toggle_ready, state=tk.DISABLED)
        self.ready_btn.pack(side=tk.LEFT)
    
    def create_game_area(self):
        """
        Create main game area - override for game-specific UI
        """
        game_frame = ttk.LabelFrame(self.root, text="Game Area", padding="10")
        game_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 5), pady=(0, 5))
        game_frame.grid_rowconfigure(0, weight=1)
        game_frame.grid_columnconfigure(0, weight=1)
        
        # Placeholder - override in subclass
        placeholder = ttk.Label(game_frame, text="Game content will appear here", 
                               font=("Arial", 14))
        placeholder.pack(expand=True)
    
    def create_sidebar(self):
        """
        Create right sidebar with players and scores
        """
        sidebar_frame = ttk.Frame(self.root, width=300)
        sidebar_frame.grid(row=1, column=1, sticky=(tk.N, tk.S, tk.E), padx=(0, 5), pady=(0, 5))
        sidebar_frame.grid_propagate(False)
        
        # Players list
        players_frame = ttk.LabelFrame(sidebar_frame, text="Players", padding="10", width=280)
        players_frame.pack(fill=tk.X, pady=(0, 10))
        players_frame.pack_propagate(False)
        
        # Players listbox with scrollbar
        players_container = ttk.Frame(players_frame)
        players_container.pack(fill=tk.BOTH, expand=True)
        
        self.players_listbox = tk.Listbox(players_container, height=10, font=("Arial", 10))
        players_scrollbar = ttk.Scrollbar(players_container)
        
        self.players_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        players_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.players_listbox.config(yscrollcommand=players_scrollbar.set)
        players_scrollbar.config(command=self.players_listbox.yview)
        
        # Ready count
        self.ready_count_label = ttk.Label(players_frame, text="Ready: 0/0", font=("Arial", 10))
        self.ready_count_label.pack(pady=(5, 0))
        
        # Scores
        scores_frame = ttk.LabelFrame(sidebar_frame, text="Scores", padding="10", width=280)
        scores_frame.pack(fill=tk.BOTH, expand=True)
        scores_frame.pack_propagate(False)
        
        scores_container = ttk.Frame(scores_frame)
        scores_container.pack(fill=tk.BOTH, expand=True)
        
        self.scores_text = tk.Text(scores_container, height=15, state=tk.DISABLED, 
                                  font=("Arial", 10))
        scores_scrollbar = ttk.Scrollbar(scores_container)
        
        self.scores_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scores_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.scores_text.config(yscrollcommand=scores_scrollbar.set)
        scores_scrollbar.config(command=self.scores_text.yview)
    
    def create_chat_area(self):
        """
        Create bottom chat area
        """
        chat_frame = ttk.LabelFrame(self.root, text="Chat", padding="5")
        chat_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.S), 
                       padx=5, pady=(0, 5))
        
        # Chat display
        chat_display_frame = ttk.Frame(chat_frame)
        chat_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.chat_text = tk.Text(chat_display_frame, height=8, state=tk.DISABLED, 
                                font=("Arial", 10))
        chat_scrollbar = ttk.Scrollbar(chat_display_frame)
        
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.chat_text.config(yscrollcommand=chat_scrollbar.set)
        chat_scrollbar.config(command=self.chat_text.yview)
        
        # Chat input
        chat_input_frame = ttk.Frame(chat_frame)
        chat_input_frame.pack(fill=tk.X)
        
        self.chat_entry = ttk.Entry(chat_input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", self.send_chat_message)
        
        self.chat_button = ttk.Button(chat_input_frame, text="Send", 
                                     command=self.send_chat_message)
        self.chat_button.pack(side=tk.RIGHT)
    
    def connect(self):
        """
        Connect to game server
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            # Start receive thread
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
        if not self.connected or not self.socket:
            return False
        
        try:
            message = json.dumps(data) + '\n'
            self.socket.sendall(message.encode())
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def receive_messages(self):
        """
        Receive messages from server
        """
        buffer = ''
        while self.running and self.connected:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        self.handle_server_message(line)
            except Exception as e:
                if self.running:
                    print(f"Error receiving message: {e}")
                break
        
        if self.running:
            self.root.after(0, self.handle_disconnect)
    
    def handle_server_message(self, message_str):
        """
        Handle incoming server message
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
        
        if msg_type == 'error':
            self.handle_error_message(message)
            
        elif msg_type == 'welcome':
            self.handle_welcome_message(message)
            
        elif msg_type == 'player_joined':
            self.handle_player_joined(message)
            
        elif msg_type == 'player_ready':
            self.handle_player_ready(message)
            
        elif msg_type == 'player_left':
            self.handle_player_left(message)
            
        elif msg_type == 'game_start':
            self.handle_game_start(message)
            
        elif msg_type == 'round_start':
            self.handle_round_start(message)
            
        elif msg_type == 'game_update':
            self.handle_game_update(message)
            
        elif msg_type == 'round_result':
            self.handle_round_result(message)
            
        elif msg_type == 'game_end':
            self.handle_game_end(message)
            
        elif msg_type == 'chat':
            self.handle_chat(message)
            
        else:
            self.handle_custom_message(message)
    
    def handle_error_message(self, message):
        """
        Handle error messages
        """
        error_msg = message.get('message', 'An error occurred')
        messagebox.showerror("Error", error_msg)
    
    def handle_welcome_message(self, message):
        """
        Handle welcome message
        """
        self.player_id = message.get('player_id')
        self.game_state = message.get('game_state', {})
        self.players = self.game_state.get('players', {})
        
        self.status_label.config(text=f"Connected as Player {self.player_id + 1}")
        self.set_name_btn.config(state=tk.NORMAL)
        
        self.update_players_list()
        self.update_scores_display()
    
    def handle_player_joined(self, message):
        """
        Handle player joined message
        """
        player_id = message.get('player_id')
        player_name = message.get('name', f'Player {player_id + 1}')
        
        self.players[player_id] = {
            'id': player_id,
            'name': player_name,
            'ready': False,
            'connected': True
        }
        
        self.update_players_list()
        self.update_ready_count(message.get('ready_count', 0), 
                               message.get('total_players', 0))
    
    def handle_player_ready(self, message):
        """
        Handle player ready message
        """
        player_id = message.get('player_id')
        ready_count = message.get('ready_count', 0)
        total_players = message.get('total_players', 0)
        
        if player_id in self.players:
            self.players[player_id]['ready'] = True
        
        self.update_players_list()
        self.update_ready_count(ready_count, total_players)
    
    def handle_player_left(self, message):
        """
        Handle player left message
        """
        player_id = message.get('player_id')
        
        if player_id in self.players:
            self.players[player_id]['connected'] = False
        
        self.update_players_list()
        self.update_ready_count(message.get('ready_count', 0), 
                               message.get('total_players', 0))
        
        if message.get('message'):
            messagebox.showinfo("Player Left", message['message'])
    
    def handle_game_start(self, message):
        """
        Handle game start message
        """
        self.game_started = True
        self.game_state = message.get('game_state', {})
        self.max_rounds = message.get('total_rounds', 1)
        self.current_round = message.get('current_round', 1)
        
        self.phase_label.config(text="Playing")
        self.set_name_btn.config(state=tk.DISABLED)
        self.ready_btn.config(state=tk.DISABLED)
        
        self.on_game_start()
    
    def handle_round_start(self, message):
        """
        Handle round start message
        """
        self.current_round = message.get('round', 1)
        self.max_rounds = message.get('total_rounds', 1)
        self.game_state = message.get('game_state', {})
        
        self.round_label.config(text=f"Round: {self.current_round}/{self.max_rounds}")
        
        self.on_round_start()
    
    def handle_game_update(self, message):
        """
        Handle game update message
        """
        player_id = message.get('player_id')
        action_type = message.get('action_type')
        data = message.get('data', {})
        result = message.get('result', {})
        
        self.game_state = message.get('game_state', {})
        
        self.on_game_update(player_id, action_type, data, result)
    
    def handle_round_result(self, message):
        """
        Handle round result message
        """
        round_num = message.get('round')
        results = message.get('results', {})
        self.game_state = message.get('game_state', {})
        
        self.scores = self.game_state.get('scores', {})
        self.update_scores_display()
        
        self.on_round_result(round_num, results)
    
    def handle_game_end(self, message):
        """
        Handle game end message
        """
        results = message.get('results', {})
        self.game_state = message.get('game_state', {})
        
        self.scores = self.game_state.get('scores', {})
        self.update_scores_display()
        
        self.on_game_end(results)
        
        # Reset for new game
        self.game_started = False
        self.player_ready = False
        self.ready_btn.config(text="Ready", state=tk.NORMAL)
        self.phase_label.config(text="Lobby")
    
    def handle_chat(self, message):
        """
        Handle chat message
        """
        player_id = message.get('player_id')
        player_name = message.get('player_name', f'Player {player_id + 1}')
        text = message.get('text', '')
        timestamp = message.get('timestamp', time.strftime("%H:%M:%S"))
        
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"[{timestamp}] {player_name}: {text}\n")
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)
    
    def handle_custom_message(self, message):
        """
        Override to handle custom message types
        """
        pass
    
    def handle_disconnect(self):
        """
        Handle server disconnection
        """
        if self.running:
            messagebox.showwarning("Disconnected", "Lost connection to server")
            self.root.quit()
    
    # UI Update Methods
    def update_players_list(self):
        """
        Update players list display
        """
        self.players_listbox.delete(0, tk.END)
        
        for player_id, player_info in sorted(self.players.items()):
            status = ""
            if player_info.get('connected'):
                if player_info.get('ready'):
                    status = " ✅"
                else:
                    status = " ⏳"
            else:
                status = " ❌"
            
            display_text = f"{player_info.get('name', f'Player {player_id + 1}')}{status}"
            self.players_listbox.insert(tk.END, display_text)
    
    def update_ready_count(self, ready_count, total_players):
        """
        Update ready count display
        """
        self.ready_count_label.config(text=f"Ready: {ready_count}/{total_players}")
    
    def update_scores_display(self):
        """
        Update scores display
        """
        self.scores_text.config(state=tk.NORMAL)
        self.scores_text.delete(1.0, tk.END)
        
        self.scores_text.insert(tk.END, "Current Scores:\n")
        self.scores_text.insert(tk.END, "=" * 20 + "\n")
        
        for player_id, score in sorted(self.scores.items()):
            player_name = self.players.get(player_id, {}).get('name', f'Player {player_id + 1}')
            if player_id == self.player_id:
                self.scores_text.insert(tk.END, f"👉 {player_name}: {score}\n")
            else:
                self.scores_text.insert(tk.END, f"  {player_name}: {score}\n")
        
        self.scores_text.config(state=tk.DISABLED)
    
    # Player Actions
    def set_name(self):
        """
        Set player name
        """
        name = self.name_entry.get().strip()
        if name:
            self.player_name = name
            if self.send_message({
                'type': 'set_name',
                'name': name
            }):
                self.set_name_btn.config(state=tk.DISABLED)
                self.ready_btn.config(state=tk.NORMAL)
                self.status_label.config(text=f"Name set: {name}")
    
    def toggle_ready(self):
        """
        Toggle ready status
        """
        if not self.player_ready:
            if self.send_message({'type': 'ready'}):
                self.player_ready = True
                self.ready_btn.config(text="Waiting...", state=tk.DISABLED)
                self.ready_status_label.config(text="Ready ✅")
        else:
            # In this implementation, ready is one-way
            pass
    
    def send_chat_message(self, event=None):
        """
        Send chat message
        """
        text = self.chat_entry.get().strip()
        if text:
            if self.send_message({
                'type': 'chat',
                'text': text,
                'timestamp': time.strftime("%H:%M:%S")
            }):
                self.chat_entry.delete(0, tk.END)
    
    def send_game_action(self, action_type, data):
        """
        Send game action to server
        """
        if self.game_started:
            return self.send_message({
                'type': 'game_action',
                'action_type': action_type,
                'data': data
            })
        return False
    
    # Game-specific methods to override
    def on_game_start(self):
        """
        Override for game-specific initialization when game starts
        """
        pass
    
    def on_round_start(self):
        """
        Override for round start handling
        """
        pass
    
    def on_game_update(self, player_id, action_type, data, result):
        """
        Override to handle game updates
        """
        pass
    
    def on_round_result(self, round_num, results):
        """
        Override to handle round results
        """
        pass
    
    def on_game_end(self, results):
        """
        Override to handle game end
        """
        pass
    
    def on_closing(self):
        """
        Handle window closing
        """
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
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
    client = MultiplayerGUIClientTemplate(host, port)
    client.run()