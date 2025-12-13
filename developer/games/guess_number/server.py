# developer/games/guess_number/server.py
import socket
import threading
import random
import sys
import os
import time

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class GuessNumberServer:
    def __init__(self, port=6000):
        self.port = port
        self.clients = []  
        self.player_info = {}  
        self.secret_number = random.randint(1, 100)
        self.game_started = False
        self.winner = None
        self.current_turn = 1  
        self.lock = threading.Lock() 
        
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(2)
        
        print(f"[Guess Number Game] Server started on port {self.port}")
        print(f"[Secret] The answer is: {self.secret_number}")
        
        for i in range(2):
            client, addr = server.accept()
            player_num = i + 1
            self.clients.append(client)
            self.player_info[client] = {
                'num': player_num,
                'turn': (player_num == 1),  
                'range': [1, 100]  
            }
            print(f"Player {player_num} connected from {addr}")
            welcome_msg = f"You are Player {player_num}! "
            if player_num == 1:
                welcome_msg += "You go first! Waiting for another player...\n"
            else:
                welcome_msg += "Waiting for Player 1 to start...\n"
            client.sendall(welcome_msg.encode())
        
        self.broadcast(f"\n{'='*50}\n")
        self.broadcast(f"Game started! Secret number is between 1 and 100\n")
        self.broadcast(f"{'='*50}\n")
        self.game_started = True
        
        self.notify_turn()
        
        for client in self.clients:
            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.start()
    
    def broadcast(self, message, exclude=None):
        for client in self.clients:
            if client != exclude:
                try:
                    client.sendall(message.encode())
                except:
                    pass
    
    def send_to_player(self, client, message):
        try:
            client.sendall(message.encode())
        except:
            pass
    
    def notify_turn(self):
        current_player = None
        for client, info in self.player_info.items():
            if info['num'] == self.current_turn:
                current_player = client
                info['turn'] = True
                low, high = info['range']
                turn_msg = f"\n{'='*40}\n"
                turn_msg += f"It's your turn!\n"
                turn_msg += f"🔢 Enter your guess ({low}-{high}): "
                self.send_to_player(client, turn_msg)
            else:
                info['turn'] = False
                wait_msg = f"\n{'='*40}\n"
                wait_msg += f"⏳ Waiting for Player {self.current_turn}'s turn...\n"
                wait_msg += f"{'='*40}\n"
                self.send_to_player(client, wait_msg)
        
        if current_player:
            self.broadcast(f"\n📢 Player {self.current_turn}'s turn now...\n", exclude=current_player)
    
    def handle_client(self, client):
        try:
            player_num = self.player_info[client]['num']
            player_range = self.player_info[client]['range']
            
            while not self.winner:
                if not self.player_info[client]['turn']:
                    time.sleep(0.1)  
                    continue
                
                data = client.recv(1024).decode().strip()
                if not data:
                    break
                
                if not self.player_info[client]['turn']:
                    self.send_to_player(client, "⏳ Not your turn! Wait for your turn.\n")
                    continue
                
                try:
                    guess = int(data)
                    
                    if guess < 1 or guess > 100:
                        self.send_to_player(client, f"⚠️  Warning: Number should be 1-100, but let's try it anyway!\n")
                    
                    guess_msg = f"\n{'='*30}\n"
                    guess_msg += f"Player {player_num} has made a guess!\n"
                    guess_msg += f"{'='*30}\n"
                    self.broadcast(guess_msg, exclude=client)
                    
                    if guess == self.secret_number:
                        with self.lock:
                            if not self.winner:  
                                self.winner = player_num
                                win_msg = f"\n{'🎉'*10}\n"
                                win_msg += f"🎉 Player {player_num} guessed correctly!\n"
                                win_msg += f"🎉 The answer is {self.secret_number}\n"
                                win_msg += f"{'🎉'*10}\n"
                                win_msg += "GAME_END\n"
                                self.broadcast(win_msg)
                                break
                    
                    if guess < self.secret_number:
                        if guess > player_range[0]:
                            player_range[0] = guess + 1
                        hint_msg = f"📈 Your guess {guess} is too low.\n"
                    else:
                        if guess < player_range[1]:
                            player_range[1] = guess - 1
                        hint_msg = f"📉 Your guess {guess} is too high.\n"
                    
                    low, high = player_range
                    hint_msg += f"🔍 Your new range: {low} ~ {high}\n"
                    
                    if low > high:
                        hint_msg += "⚠️  Something's wrong with the range!\n"
                    
                    self.send_to_player(client, hint_msg)
                    
                    continue_msg = f"\n➡️  Game continues...\n"
                    self.broadcast(continue_msg, exclude=client)
                    
                    self.current_turn = 2 if self.current_turn == 1 else 1
                    self.notify_turn()
                    
                except ValueError:
                    self.send_to_player(client, "❌ Please enter a valid number!\n")
        
        except Exception as e:
            print(f"Error with player {player_num}: {e}")
        finally:
            client.close()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    server = GuessNumberServer(port)
    server.start()