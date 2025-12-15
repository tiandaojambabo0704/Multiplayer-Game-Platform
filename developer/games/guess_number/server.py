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
        self.game_ended = False  
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
                'range': [1, 100],
                'active': True  
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
            thread.daemon = True
            thread.start()
            
        try:
            while threading.active_count() > 1 and not self.game_ended:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.end_game("Server shutdown")
    
    def broadcast(self, message, exclude=None):
        if self.game_ended:
            return
            
        for client in self.clients:
            if client != exclude and self.player_info.get(client, {}).get('active', False):
                try:
                    client.sendall(message.encode())
                except:
                    pass
    
    def send_to_player(self, client, message):
        if self.game_ended or not self.player_info.get(client, {}).get('active', False):
            return
            
        try:
            client.sendall(message.encode())
        except:
            pass
    
    def end_game(self, reason="Game ended"):
        with self.lock:
            if self.game_ended:
                return
                
            self.game_ended = True
            self.winner = None
            
            end_msg = f"\n{'⚠️'*10}\n"
            end_msg += f"⚠️  {reason}\n"
            end_msg += f"⚠️  Game terminated!\n"
            end_msg += f"{'⚠️'*10}\n"
            end_msg += "GAME_END\n"
            
            for client in self.clients:
                if self.player_info.get(client, {}).get('active', False):
                    try:
                        client.sendall(end_msg.encode())
                        client.close()
                    except:
                        pass
            
            print(f"\n[Game ended] {reason}")
    
    def notify_turn(self):
        if self.game_ended:
            return
            
        current_player = None
        for client, info in self.player_info.items():
            if not info['active']:
                continue
                
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
            
            while not self.game_ended:
                if not self.player_info[client]['active'] or not self.player_info[client]['turn']:
                    time.sleep(0.1)  
                    continue
                
                try:
                    client.settimeout(1.0)
                    data = client.recv(1024).decode().strip()
                    
                    if not data:
                        self.player_disconnected(client, player_num)
                        break
                    
                    if not self.player_info[client]['turn'] or not self.player_info[client]['active']:
                        self.send_to_player(client, "⏳ Not your turn! Wait for your turn.\n")
                        continue
                    
                    try:
                        guess = int(data)
                    except ValueError:
                        guess = 0
                        guess_msg = f"\n{'='*30}\n"
                        guess_msg += f"Player {player_num} entered non-number, default to 0!\n"
                        guess_msg += f"{'='*30}\n"
                        self.broadcast(guess_msg, exclude=client)
                    
                    if guess < 1 or guess > 100:
                        self.send_to_player(client, f"⚠️  Warning: Number should be 1-100, but let's try it anyway!\n")
                    
                    guess_msg = f"\n{'='*30}\n"
                    guess_msg += f"Player {player_num} has made a guess!\n"
                    guess_msg += f"{'='*30}\n"
                    self.broadcast(guess_msg, exclude=client)
                    
                    if guess == self.secret_number:
                        with self.lock:
                            if not self.winner and not self.game_ended:
                                self.winner = player_num
                                win_msg = f"\n{'🎉'*10}\n"
                                win_msg += f"🎉 Player {player_num} guessed correctly!\n"
                                win_msg += f"🎉 The answer is {self.secret_number}\n"
                                win_msg += f"{'🎉'*10}\n"
                                win_msg += "GAME_END\n"
                                self.broadcast(win_msg)
                                self.game_ended = True
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
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    self.player_disconnected(client, player_num)
                    break
        
        except Exception as e:
            print(f"Error with player {player_num}: {e}")
            self.player_disconnected(client, player_num)
        finally:
            try:
                client.close()
            except:
                pass
    
    def player_disconnected(self, client, player_num):
        if self.game_ended:
            return
            
        self.player_info[client]['active'] = False
        print(f"\n[System] Player {player_num} disconnected")
        
        for other_client, info in self.player_info.items():
            if other_client != client and info['active']:
                disconnect_msg = f"\n{'⚠️'*10}\n"
                disconnect_msg += f"⚠️  Player {player_num} has disconnected!\n"
                disconnect_msg += f"⚠️  Game cannot continue.\n"
                disconnect_msg += f"{'⚠️'*10}\n"
                disconnect_msg += "GAME_END\n"
                
                try:
                    other_client.sendall(disconnect_msg.encode())
                except:
                    pass
        
        self.end_game(f"Player {player_num} disconnected")

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    server = GuessNumberServer(port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\n[Server] Shutting down...")
        server.end_game("Server manually stopped")