# developer/games/card_battle/client.py
import socket
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox
import sys

class CardBattleClient:
    def __init__(self, host='localhost', port=6002):
        self.host = host
        self.port = port
        self.socket = None
        self.player_id = None
        self.player_name = ""
        self.cards = []
        self.remaining_cards = [] 
        self.scores = {}
        self.players = {}
        self.current_round = 0
        self.selected_this_round = False 
        self.played_cards = []  
        self.receive_thread = None
        self.running = True
        
        # GUI
        self.root = tk.Tk()
        self.root.title("Card Battle Game - Secret Selection")
        self.root.geometry("1000x700") 
        
        self.setup_ui()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)  
        main_frame.grid_columnconfigure(0, weight=1)  
        main_frame.grid_columnconfigure(1, weight=0) 
        
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        status_frame = ttk.Frame(top_frame)
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.status_label = ttk.Label(status_frame, text="Connecting to server...", font=("Arial", 12))
        self.status_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.round_label = ttk.Label(status_frame, text="Round: 0/7", font=("Arial", 12, "bold"))
        self.round_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.play_status = ttk.Label(status_frame, text="Waiting for players...", font=("Arial", 10))
        self.play_status.pack(side=tk.LEFT)
        
        control_frame = ttk.Frame(top_frame)
        control_frame.pack(side=tk.RIGHT)
        
        name_frame = ttk.Frame(control_frame)
        name_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(name_frame, text="Your Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.name_entry = ttk.Entry(name_frame, width=15)
        self.name_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.name_entry.insert(0, "Player")
        
        self.set_name_btn = ttk.Button(name_frame, text="Set Name", command=self.set_name, state=tk.DISABLED)
        self.set_name_btn.pack(side=tk.LEFT)
        
        self.ready_btn = ttk.Button(control_frame, text="Ready", command=self.toggle_ready, state=tk.DISABLED)
        self.ready_btn.pack(side=tk.LEFT)
        
        left_frame = ttk.LabelFrame(main_frame, text="Game Info", padding="10")
        left_frame.grid(row=1, column=1, sticky=(tk.N, tk.S), padx=(10, 0))
        
        info_frame = ttk.LabelFrame(left_frame, text="Players Info", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.ready_label = ttk.Label(info_frame, text="Ready: 0/0", font=("Arial", 10))
        self.ready_label.pack(pady=5)
        
        players_subframe = ttk.Frame(info_frame)
        players_subframe.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(players_subframe, text="Online Players:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        self.players_listbox = tk.Listbox(players_subframe, width=20, height=8)
        self.players_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        result_frame = ttk.LabelFrame(left_frame, text="Round Results", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        result_canvas = tk.Canvas(result_frame, highlightthickness=0)
        result_scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=result_canvas.yview)
        
        result_text_container = ttk.Frame(result_canvas)
        result_text_container.bind(
            "<Configure>",
            lambda e: result_canvas.configure(scrollregion=result_canvas.bbox("all"))
        )
        
        result_canvas.create_window((0, 0), window=result_text_container, anchor="nw")
        result_canvas.configure(yscrollcommand=result_scrollbar.set)
        
        result_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def _on_mousewheel_result(event):
            result_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        result_canvas.bind_all("<MouseWheel>", _on_mousewheel_result)
        
        self.result_text = tk.Text(result_text_container, width=50, height=30, state=tk.DISABLED, font=("Arial", 9))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        game_frame = ttk.Frame(main_frame)
        game_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        selection_frame = ttk.LabelFrame(game_frame, text="Your Selection", padding="10")
        selection_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.selection_label = ttk.Label(selection_frame, text="Not selected yet", font=("Arial", 11))
        self.selection_label.pack()
        
        hand_frame = ttk.LabelFrame(game_frame, text="Select Your Card", padding="10")
        hand_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.card_container = ttk.Frame(hand_frame)
        self.card_container.pack(fill=tk.BOTH, expand=True)
        
        self.card_buttons = []
        
        score_frame = ttk.LabelFrame(game_frame, text="Current Scores", padding="10")
        score_frame.pack(fill=tk.X)
        
        self.score_text = tk.Text(score_frame, height=5, state=tk.DISABLED, font=("Arial", 10))
        self.score_text.pack(fill=tk.BOTH, expand=True)
    
    def create_card_buttons(self):
        for btn in self.card_buttons:
            btn.destroy()
        self.card_buttons.clear()
        
        for widget in self.card_container.winfo_children():
            widget.destroy()
        
        num_cards = len(self.cards)
        cards_per_row = 5 if num_cards <= 10 else 6  
        
        for i, card in enumerate(self.cards):
            is_played = card in self.played_cards
            btn_state = tk.NORMAL if not is_played and not self.selected_this_round else tk.DISABLED
            
            btn = tk.Button(
                self.card_container, 
                text=str(card), 
                font=("Arial", 12),
                width=6,  
                height=2,  
                relief=tk.RAISED,
                bg="lightblue" if not is_played else "lightgray",
                fg="black" if not is_played else "gray",
                state=btn_state,
                command=lambda c=card: self.select_card(c) if not is_played else None
            )
            
            if is_played:
                btn.config(relief=tk.SUNKEN, bg="lightgray")
            
            row = i // cards_per_row
            col = i % cards_per_row
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="nsew") 
            
            self.card_container.grid_rowconfigure(row, weight=1)
            self.card_container.grid_columnconfigure(col, weight=1)
            
            self.card_buttons.append(btn)
        
        self.card_container.update_idletasks()
    
    def update_card_buttons_state(self):
        for btn in self.card_buttons:
            card = int(btn['text'])
            is_played = card in self.played_cards
            
            if is_played:
                btn.config(state=tk.DISABLED, relief=tk.SUNKEN, bg="lightgray", fg="gray")
            elif self.selected_this_round or self.current_round == 0:
                btn.config(state=tk.DISABLED, bg="lightblue", fg="black")
            else:
                btn.config(state=tk.NORMAL, relief=tk.RAISED, bg="lightblue", fg="black")
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            self.status_label.config(text="Connected! Set your name.")
            self.set_name_btn.config(state=tk.NORMAL)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Cannot connect to server: {e}")
            return False
    
    def send_message(self, data):
        try:
            message = json.dumps(data) + '\n'
            self.socket.sendall(message.encode())
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def receive_messages(self):
        buffer = ''
        while self.running:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        try:
                            message = json.loads(line)
                            self.root.after(0, self.handle_message, message)
                        except json.JSONDecodeError:
                            print(f"Invalid JSON received: {line}")
            except Exception as e:
                if self.running:
                    print(f"Error receiving message: {e}")
                break
        
        if self.running:
            self.root.after(0, self.handle_disconnect)
    
    def handle_message(self, message):
        msg_type = message['type']
        
        if msg_type == 'error':
            messagebox.showerror("Error", message['message'])
            
        elif msg_type == 'welcome':
            self.player_id = message['player_id']
            self.status_label.config(text=f"Connected as Player {self.player_id + 1}")
            
        elif msg_type == 'player_joined':
            player_id = message['player_id']
            name = message['name']
            self.players[player_id] = name
            self.update_players_list()
            
        elif msg_type == 'player_ready':
            ready_count = message['ready_count']
            total = message['total_players']
            player_id = message['player_id']
            player_name = self.players.get(player_id, f'Player {player_id + 1}')
            self.ready_label.config(text=f"Ready: {ready_count}/{total}")
            
        elif msg_type == 'player_left':
            player_id = message['player_id']
            if player_id in self.players:
                del self.players[player_id]
            self.update_players_list()
            ready_count = message.get('ready_count', 0)
            total = len(self.players)
            self.ready_label.config(text=f"Ready: {ready_count}/{total}")
            
        elif msg_type == 'game_start':
            self.player_id = message['player_id']
            self.cards = message['cards']
            self.remaining_cards = self.cards.copy()  
            self.played_cards = [] 
            self.create_card_buttons()
            total_players = message['total_players']
            self.status_label.config(text=f"You are {self.player_name}")
            self.ready_btn.config(state=tk.DISABLED)
            self.set_name_btn.config(state=tk.DISABLED)
            
        elif msg_type == 'round_start':
            self.current_round = message['round']
            self.selected_this_round = False
            self.selection_label.config(text="Not selected yet")
            self.round_label.config(text=f"Round: {self.current_round}/7")
            self.play_status.config(text=f"Round {self.current_round}: Select a card")
            
            self.update_card_buttons_state()
            
        elif msg_type == 'card_selected':
            card = message['card']
            remaining = message['remaining']
            total = message['total_players']
            
            self.selection_label.config(text=f"✅ You selected card {card}")
            status_text = f"You selected card {card}. Waiting: {remaining}/{total} players"
            self.play_status.config(text=status_text)
            
            self.played_cards.append(card)
            self.selected_this_round = True
            
            self.update_card_buttons_state()
            
        elif msg_type == 'player_ready_in_round':
            player_id = message['player_id']
            remaining = message['remaining']
            total = message['total_players']
            player_name = self.players.get(player_id, f'Player {player_id + 1}')
            
            status_text = f"{player_name} is ready. Waiting: {remaining}/{total} players"
            self.play_status.config(text=status_text)
            
        elif msg_type == 'round_result':
            result = message['result']
            
            scores_int = {}
            for pid_str, score in result['scores'].items():
                try:
                    pid = int(pid_str)  
                    scores_int[pid] = score
                except (ValueError, TypeError):
                    scores_int[pid_str] = score
            
            self.update_scores(scores_int)
            
            self.show_round_result(result)
            
        elif msg_type == 'game_end':
            final_scores = message['final_scores']
            champions = message['champions']
            
            self.show_final_results(final_scores, champions)
            
            self.reset_game()
    
    def handle_disconnect(self):
        if self.running:
            messagebox.showwarning("Disconnected", "Lost connection to server")
            self.root.quit()
    
    def set_name(self):
        name = self.name_entry.get().strip()
        if name:
            self.player_name = name
            if self.send_message({
                'type': 'set_name',
                'name': name
            }):
                self.set_name_btn.config(state=tk.DISABLED)
                self.ready_btn.config(state=tk.NORMAL)
                self.status_label.config(text=f"Name set to: {name}")
    
    def toggle_ready(self):
        if self.send_message({'type': 'ready'}):
            self.ready_btn.config(text="Waiting...", state=tk.DISABLED)
    
    def select_card(self, card):
        if card in self.played_cards:
            messagebox.showwarning("Invalid Move", f"Card {card} has already been played!")
            return
            
        if self.selected_this_round or not self.cards or self.current_round == 0:
            return
            
        if self.send_message({
            'type': 'select_card',
            'card': card,
            'round': self.current_round
        }):
            self.selected_this_round = True
            self.played_cards.append(card)
            self.update_card_buttons_state()
            self.selection_label.config(text=f"✅ You selected card {card}")
            
            self.play_status.config(text=f"You selected card {card}. Waiting for others...")
    
    def update_players_list(self):
        self.players_listbox.delete(0, tk.END)
        for pid, name in sorted(self.players.items()):
            try:
                pid_int = int(pid)
                display_name = f"{name} (Player {pid_int + 1})" if name else f"Player {pid_int + 1}"
            except (ValueError, TypeError):
                display_name = f"{name} (Player {int(pid) + 1})" if name else f"Player {int(pid) + 1}"
            self.players_listbox.insert(tk.END, display_name)
    
    def update_scores(self, scores):
        self.scores = scores
        self.score_text.config(state=tk.NORMAL)
        self.score_text.delete(1.0, tk.END)
        
        self.score_text.insert(tk.END, "Current Scores:\n")
        self.score_text.insert(tk.END, "-" * 20 + "\n")
        
        for pid, score in sorted(scores.items()):
            try:
                player_id = int(pid)
            except (ValueError, TypeError):
                player_id = pid
            
            player_name = self.players.get(player_id, f'Player {int(player_id) + 1}')
            if player_id == self.player_id:
                self.score_text.insert(tk.END, f"👉 {player_name}: {score} wins\n")
            else:
                self.score_text.insert(tk.END, f"  {player_name}: {score} wins\n")
        
        self.score_text.config(state=tk.DISABLED)
    
    def show_round_result(self, result):
        self.result_text.config(state=tk.NORMAL)
        
        self.result_text.insert(tk.END, f"\n=== Round {result['round']} ===\n")
        self.result_text.insert(tk.END, f"Highest card: {result['max_card']}\n")
        self.result_text.insert(tk.END, f"Cards played:\n")
        
        for pid, card in sorted(result['cards'].items()):
            try:
                pid_int = int(pid)
                player_name = self.players.get(pid_int, f'Player {pid_int + 1}')
            except (ValueError, TypeError):
                player_name = self.players.get(pid, f'Player {int(pid) + 1}')
            
            if pid == self.player_id or (isinstance(self.player_id, int) and int(pid) == self.player_id):
                self.result_text.insert(tk.END, f"  → {player_name}: {card}\n")
            else:
                self.result_text.insert(tk.END, f"    {player_name}: {card}\n")
        
        winners_text = []
        for winner in result['winners']:
            try:
                winner_id = int(winner)
                player_name = self.players.get(winner_id, f'Player {winner_id + 1}')
            except (ValueError, TypeError):
                player_name = self.players.get(winner, f'Player {int(winner) + 1}')
            winners_text.append(player_name)
        
        self.result_text.insert(tk.END, f"🏆 Winner(s): {', '.join(winners_text)}\n")
        self.result_text.insert(tk.END, "-" * 30 + "\n")
        
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)
        
        self.play_status.config(text=f"Round {result['round']} completed. Highest card: {result['max_card']}")
    
    def show_final_results(self, final_scores, champions):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        
        self.result_text.insert(tk.END, "\n" + "="*30 + "\n")
        self.result_text.insert(tk.END, "🎮 GAME OVER! 🎮\n")
        self.result_text.insert(tk.END, "="*30 + "\n\n")
        self.result_text.insert(tk.END, "FINAL SCORES:\n")
        self.result_text.insert(tk.END, "-"*20 + "\n")
        
        final_scores_int = {}
        for pid_str, score in final_scores.items():
            try:
                pid_int = int(pid_str)
                final_scores_int[pid_int] = score
            except (ValueError, TypeError):
                final_scores_int[pid_str] = score
        
        for pid, score in sorted(final_scores_int.items()):
            player_name = self.players.get(pid, f'Player {int(pid) + 1}')
            if pid == self.player_id or (isinstance(self.player_id, int) and int(pid) == self.player_id):
                self.result_text.insert(tk.END, f"👉 {player_name}: {score} wins\n")
            else:
                self.result_text.insert(tk.END, f"  {player_name}: {score} wins\n")
        
        self.result_text.insert(tk.END, "\n")
        
        champion_names = []
        for champion in champions:
            try:
                champ_id = int(champion)
                player_name = self.players.get(champ_id, f'Player {champ_id + 1}')
            except (ValueError, TypeError):
                player_name = self.players.get(champion, f'Player {int(champion) + 1}')
            champion_names.append(player_name)
        
        self.result_text.insert(tk.END, "🏆 CHAMPION(S):\n")
        for champion in champion_names:
            self.result_text.insert(tk.END, f"  {champion}\n")
        
        self.result_text.insert(tk.END, "\n" + "="*30 + "\n")
        
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)
        
        self.play_status.config(text="Game Over! Check the results panel.")
    
    def reset_game(self):
        self.cards = []
        self.remaining_cards = []
        self.played_cards = []
        self.scores = {}
        self.current_round = 0
        self.selected_this_round = False
        self.create_card_buttons()
        self.round_label.config(text="Round: 0/7")
        self.selection_label.config(text="Not selected yet")
        self.ready_btn.config(text="Ready", state=tk.DISABLED)
        self.set_name_btn.config(state=tk.NORMAL)
    
    def run(self):
        if self.connect():
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
    
    def on_closing(self):
        self.running = False
        try:
            self.socket.close()
        except:
            pass
        self.root.quit()

if __name__ == '__main__':
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6002
    client = CardBattleClient(host, port)
    client.run()