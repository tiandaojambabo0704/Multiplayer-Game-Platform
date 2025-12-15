# developer/game_templates/CLI/server.py
import socket
import threading
import random
import sys

class GameServerTemplate:
    def __init__(self, port):
        """
        Initialize game server with game-specific parameters
        """
        self.port = port
        self.clients = []
        self.player_info = {}
        self.game_state = {}  # Custom game state
        self.game_started = False
        self.game_ended = False
        self.current_turn = 1
        self.lock = threading.Lock()
        
        # Game-specific initialization
        self.initialize_game()
    
    def initialize_game(self):
        """
        Override this method to initialize game-specific logic
        Called during server initialization
        """
        pass
    
    def start(self):
        """
        Start server and wait for players
        """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(self.get_max_players())  # Use game-specific player count
        
        print(f"[{self.get_game_name()}] Server started on port {self.port}")
        
        # Wait for all players to connect
        for i in range(self.get_max_players()):
            client, addr = server.accept()
            player_num = i + 1
            self.clients.append(client)
            self.player_info[client] = {
                'num': player_num,
                'turn': (player_num == 1),
                'data': {}  # Player-specific data
            }
            print(f"Player {player_num} connected from {addr}")
            welcome_msg = self.generate_welcome_message(player_num)
            client.sendall(welcome_msg.encode())
        
        self.broadcast(f"\n{'='*50}\n")
        self.broadcast(f"{self.get_game_name()} started!\n")
        self.broadcast(f"{'='*50}\n")
        self.game_started = True
        
        # Game-specific start logic
        self.on_game_start()
        
        self.notify_turn()
        
        for client in self.clients:
            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.start()
    
    def get_game_name(self):
        """
        Override to return game name
        """
        return "Game Template"
    
    def get_max_players(self):
        """
        Override to return maximum number of players
        """
        return 2
    
    def get_min_players(self):
        """
        Override to return minimum number of players
        """
        return 2
    
    def generate_welcome_message(self, player_num):
        """
        Override to generate custom welcome message
        """
        return f"You are Player {player_num}!\n"
    
    def broadcast(self, message, exclude=None):
        """
        Send message to all connected clients
        """
        for client in self.clients:
            if client != exclude:
                try:
                    client.sendall(message.encode())
                except:
                    pass
    
    def send_to_player(self, client, message):
        """
        Send message to specific player
        """
        try:
            client.sendall(message.encode())
        except:
            pass
    
    def notify_turn(self):
        """
        Notify players whose turn it is
        """
        current_player = None
        for client, info in self.player_info.items():
            if info['num'] == self.current_turn:
                current_player = client
                info['turn'] = True
                turn_msg = self.generate_turn_message(info)
                self.send_to_player(client, turn_msg)
            else:
                info['turn'] = False
                wait_msg = self.generate_wait_message(self.current_turn)
                self.send_to_player(client, wait_msg)
        
        if current_player:
            self.broadcast(f"\nPlayer {self.current_turn}'s turn now...\n", exclude=current_player)
    
    def generate_turn_message(self, player_info):
        """
        Override to generate turn message
        """
        return f"\nIt's your turn!\nEnter your move: "
    
    def generate_wait_message(self, current_turn_player):
        """
        Override to generate wait message
        """
        return f"\nWaiting for Player {current_turn_player}'s turn...\n"
    
    def handle_client(self, client):
        """
        Handle client connection and game logic
        """
        try:
            player_num = self.player_info[client]['num']
            player_data = self.player_info[client]['data']
            
            while not self.game_ended:
                if not self.player_info[client]['turn']:
                    import time
                    time.sleep(0.1)
                    continue
                
                data = client.recv(1024).decode().strip()
                if not data:
                    break
                
                if not self.player_info[client]['turn']:
                    self.send_to_player(client, "Not your turn! Wait for your turn.\n")
                    continue
                
                # Process player input
                result = self.process_player_input(player_num, data, player_data)
                
                if result.get('end_game'):
                    self.end_game(result.get('winner'))
                    break
                
                if result.get('switch_turn'):
                    self.switch_turn()
                
                if result.get('broadcast_message'):
                    self.broadcast(result['broadcast_message'])
                
                if result.get('player_message'):
                    self.send_to_player(client, result['player_message'])
                
                if result.get('update_player_data'):
                    player_data.update(result['update_player_data'])
                
        except Exception as e:
            print(f"Error with player {player_num}: {e}")
        finally:
            client.close()
    
    def process_player_input(self, player_num, input_data, player_data):
        """
        Override this method to process player input
        Return a dictionary with results:
        {
            'end_game': True/False,
            'winner': player_num/None,
            'switch_turn': True/False,
            'broadcast_message': str,
            'player_message': str,
            'update_player_data': dict
        }
        """
        # Example implementation - override in actual game
        return {
            'end_game': False,
            'switch_turn': True,
            'broadcast_message': f"Player {player_num} input: {input_data}\n",
            'player_message': f"You entered: {input_data}\n",
            'update_player_data': {'last_input': input_data}
        }
    
    def switch_turn(self):
        """
        Switch to next player's turn
        """
        total_players = len(self.clients)
        self.current_turn = (self.current_turn % total_players) + 1
        self.notify_turn()
    
    def end_game(self, winner=None):
        """
        End the game
        """
        with self.lock:
            if not self.game_ended:
                self.game_ended = True
                end_message = self.generate_end_message(winner)
                self.broadcast(end_message)
    
    def generate_end_message(self, winner):
        """
        Override to generate game end message
        """
        if winner:
            return f"\nPlayer {winner} wins!\nGAME_END\n"
        else:
            return f"\nGame ended!\nGAME_END\n"
    
    def on_game_start(self):
        """
        Override to execute custom logic when game starts
        """
        pass

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    server = GameServerTemplate(port)
    server.start()