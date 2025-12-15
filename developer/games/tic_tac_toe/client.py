# developer/games/tic_tac_toe/client.py
import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class TicTacToeClient:
    def __init__(self, host='localhost', port=6001):
        self.host = host
        self.port = port
        self.socket = None
        self.player_num = None
        self.symbol = None
        self.current_turn = None
        self.connected = False
        
        self.root = tk.Tk()
        self.root.title("Tic Tac Toe")
        self.root.geometry("400x450")
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.info_label = tk.Label(self.root, text="Connecting...", font=("Arial", 14))
        self.info_label.pack(pady=10)
        
        self.board_frame = tk.Frame(self.root)
        self.board_frame.pack(pady=10)
        
        self.buttons = []
        for i in range(3):
            row = []
            for j in range(3):
                btn = tk.Button(self.board_frame, text='', font=("Arial", 24), 
                               width=5, height=2,
                               command=lambda r=i, c=j: self.make_move(r, c))
                btn.grid(row=i, column=j, padx=5, pady=5)
                row.append(btn)
            self.buttons.append(row)
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
        except:
            messagebox.showerror("Error", "Cannot connect to game server")
            return False
    
    def send_message(self, data):
        try:
            message = json.dumps(data) + '\n'
            self.socket.sendall(message.encode())
        except:
            pass
    
    def receive_messages(self):
        buffer = ''
        while self.connected:
            try:
                self.socket.settimeout(1.0)
                data = self.socket.recv(1024).decode()
                if not data:
                    self.handle_disconnect("Lost connection to server")
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        message = json.loads(line)
                        self.handle_message(message)
                        
            except socket.timeout:
                continue
            except ConnectionError:
                self.handle_disconnect("Lost connection to server")
                break
            except json.JSONDecodeError:
                continue
            except Exception:
                self.handle_disconnect("Connection error")
                break
    
    def handle_disconnect(self, message):
        if not self.connected:
            return
            
        self.connected = False
        
        # Update GUI in main thread
        self.root.after(0, lambda: self.show_disconnect_message(message))
    
    def show_disconnect_message(self, message):
        messagebox.showinfo("Game Ended", message)
        self.root.quit()
    
    def handle_message(self, message):
        msg_type = message['type']
        
        if msg_type == 'init':
            self.player_num = message['player']
            self.symbol = message['symbol']
            self.info_label.config(text=f"You are Player {self.player_num + 1} ({self.symbol})")
        
        elif msg_type == 'start':
            self.info_label.config(text=f"Game started! You are {self.symbol}")
        
        elif msg_type == 'turn':
            self.current_turn = message['player']
            if self.current_turn == self.player_num:
                self.info_label.config(text=f"Your turn! ({self.symbol})", fg='green')
            else:
                self.info_label.config(text=f"Waiting for opponent...", fg='red')
        
        elif msg_type == 'move':
            row, col = message['row'], message['col']
            symbol = message['symbol']
            self.buttons[row][col].config(text=symbol, state=tk.DISABLED)
        
        elif msg_type == 'end':
            result = message['result']
            if result == 'draw':
                messagebox.showinfo("Game Over", "Draw!")
                self.root.quit()
            elif result == 'win':
                winner = message['winner']
                if winner == self.player_num:
                    messagebox.showinfo("Game Over", "You win! 🎉")
                else:
                    messagebox.showinfo("Game Over", "You lose!")
                self.root.quit()
            elif result == 'disconnect':
                reason = message.get('reason', 'Opponent disconnected')
                messagebox.showinfo("Game Ended", reason)
                self.root.quit()
        
        elif msg_type == 'disconnect':
            reason = message.get('reason', 'Opponent disconnected')
            messagebox.showinfo("Game Ended", reason)
            self.root.quit()
        
        elif msg_type == 'error':
            messagebox.showwarning("Error", message['message'])
    
    def make_move(self, row, col):
        if not self.connected:
            return
            
        if self.current_turn != self.player_num:
            return
        
        self.send_message({
            'type': 'move',
            'row': row,
            'col': col
        })
    
    def on_closing(self):
        if self.connected:
            self.connected = False
            try:
                self.socket.close()
            except:
                pass
        self.root.quit()
    
    def run(self):
        if self.connect():
            self.root.mainloop()
        try:
            if self.socket:
                self.socket.close()
        except:
            pass

if __name__ == '__main__':
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6001
    client = TicTacToeClient(host, port)
    client.run()