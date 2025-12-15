# developer/game_templates/Multiplayer/server.py
import socket
import threading
import json
import random
import time
import sys

class MultiplayerGUIServerTemplate:
    def __init__(self, port):
        """
        Initialize multiplayer GUI game server
        """
        self.port = port
        self.clients = []  # List of connected client sockets
        self.client_info = {}  # client -> player info dict
        self.players_ready = 0
        self.game_started = False
        self.game_state = {}
        self.current_round = 0
        self.max_rounds = 1  # Default, override in subclass
        self.scores = {}
        self.lock = threading.Lock()
        self.min_players = 2
        self.max_players = 5
        
        # Game-specific initialization
        self.initialize_game()
    
    def initialize_game(self):
        """
        Override this method for game-specific initialization
        """
        self.game_state = {
            'phase': 'lobby',
            'players': {},
            'ready_count': 0
        }
    
    def start(self):
        """
        Start server and accept connections
        """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(self.max_players)
        
        print(f"[{self.get_game_name()}] Server started on port {self.port}")
        print(f"Waiting for players ({self.min_players}-{self.max_players} players required)...")
        
        while True:
            client, addr = server.accept()
            
            with self.lock:
                if len(self.clients) >= self.max_players:
                    self.send_message(client, {
                        'type': 'error',
                        'message': f'Room is full (max {self.max_players} players)'
                    })
                    client.close()
                    continue
            
            player_id = len(self.clients)
            
            with self.lock:
                self.clients.append(client)
                player_info = self.create_player_info(player_id)
                self.client_info[client] = player_info
                self.scores[player_id] = 0
                
                # Update game state
                self.game_state['players'][player_id] = {
                    'id': player_id,
                    'name': player_info['name'],
                    'ready': False,
                    'connected': True
                }
            
            # Send welcome message
            self.send_message(client, {
                'type': 'welcome',
                'player_id': player_id,
                'message': f'Welcome {player_info["name"]}!',
                'game_state': self.game_state
            })
            
            # Notify all players about new player
            self.broadcast({
                'type': 'player_joined',
                'player_id': player_id,
                'name': player_info['name'],
                'total_players': len(self.clients),
                'game_state': self.game_state
            })
            
            # Start client handler thread
            thread = threading.Thread(target=self.handle_client, args=(client, player_id))
            thread.start()
            
            print(f"Player {player_id + 1} ({player_info['name']}) connected from {addr}")
    
    def get_game_name(self):
        """
        Override to return game name
        """
        return "Multiplayer Game Template"
    
    def create_player_info(self, player_id):
        """
        Override to create player-specific information
        """
        return {
            'player_id': player_id,
            'name': f'Player {player_id + 1}',
            'ready': False,
            'connected': True
        }
    
    def send_message(self, client, data):
        """
        Send JSON message to client
        """
        try:
            message = json.dumps(data) + '\n'
            client.sendall(message.encode())
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def broadcast(self, data, exclude=None):
        """
        Broadcast message to all clients except those in exclude list
        """
        exclude = exclude or []
        for client in list(self.clients):
            if client in exclude:
                continue
            try:
                self.send_message(client, data)
            except:
                pass
    
    def broadcast_to_all(self, data):
        """
        Broadcast message to all connected clients
        """
        for client in list(self.clients):
            try:
                self.send_message(client, data)
            except:
                pass
    
    def handle_client(self, client, player_id):
        """
        Handle client connection
        """
        try:
            while True:
                data = client.recv(1024).decode().strip()
                if not data:
                    break
                
                try:
                    message = json.loads(data)
                    self.process_message(client, player_id, message)
                except json.JSONDecodeError:
                    print(f"Invalid JSON from player {player_id + 1}")
                    continue
                
        except Exception as e:
            print(f"Player {player_id + 1} disconnected: {e}")
        finally:
            self.handle_disconnect(client, player_id)
    
    def process_message(self, client, player_id, message):
        """
        Process messages from client
        """
        msg_type = message.get('type')
        
        if msg_type == 'set_name':
            self.handle_set_name(client, player_id, message)
            
        elif msg_type == 'ready':
            self.handle_ready(client, player_id, message)
            
        elif msg_type == 'game_action':
            self.handle_game_action(client, player_id, message)
            
        elif msg_type == 'chat':
            self.handle_chat_message(client, player_id, message)
            
        else:
            self.handle_custom_message(client, player_id, message)
    
    def handle_set_name(self, client, player_id, message):
        """
        Handle player name change
        """
        new_name = message.get('name', f'Player {player_id + 1}')
        
        with self.lock:
            if client in self.client_info:
                self.client_info[client]['name'] = new_name
                self.game_state['players'][player_id]['name'] = new_name
        
        print(f"Player {player_id + 1} set name to: {new_name}")
        
        self.broadcast({
            'type': 'player_joined',
            'player_id': player_id,
            'name': new_name,
            'total_players': len(self.clients),
            'game_state': self.game_state
        })
    
    def handle_ready(self, client, player_id, message):
        """
        Handle player ready status
        """
        with self.lock:
            if client in self.client_info and not self.client_info[client]['ready']:
                self.client_info[client]['ready'] = True
                self.players_ready += 1
                self.game_state['players'][player_id]['ready'] = True
                self.game_state['ready_count'] = self.players_ready
        
        print(f"Player {player_id + 1} is ready. Ready count: {self.players_ready}/{len(self.clients)}")
        
        self.broadcast({
            'type': 'player_ready',
            'player_id': player_id,
            'ready_count': self.players_ready,
            'total_players': len(self.clients),
            'game_state': self.game_state
        })
        
        # Check if we can start the game
        if (self.min_players <= len(self.clients) <= self.max_players and 
            self.players_ready == len(self.clients)):
            print(f"All players ready! Starting game...")
            time.sleep(1)
            self.start_game()
    
    def handle_game_action(self, client, player_id, message):
        """
        Override to handle game-specific actions
        """
        action_type = message.get('action_type')
        data = message.get('data', {})
        
        if not self.game_started:
            print(f"Game not started yet, but player {player_id + 1} tried to perform action")
            return
        
        # Process the action
        result = self.process_game_action(player_id, action_type, data)
        
        if result:
            # Broadcast result to all players
            self.broadcast({
                'type': 'game_update',
                'player_id': player_id,
                'action_type': action_type,
                'data': data,
                'result': result,
                'game_state': self.game_state
            })
            
            # Check if round/game should end
            self.check_game_progress()
    
    def process_game_action(self, player_id, action_type, data):
        """
        Override to process game-specific actions
        Return: result dict or None
        """
        # Example implementation
        return {
            'success': True,
            'message': f'Player {player_id} performed {action_type}'
        }
    
    def handle_chat_message(self, client, player_id, message):
        """
        Handle chat messages
        """
        text = message.get('text', '')
        timestamp = message.get('timestamp', time.strftime("%H:%M:%S"))
        
        player_name = self.client_info.get(client, {}).get('name', f'Player {player_id + 1}')
        
        self.broadcast({
            'type': 'chat',
            'player_id': player_id,
            'player_name': player_name,
            'text': text,
            'timestamp': timestamp
        })
    
    def handle_custom_message(self, client, player_id, message):
        """
        Override to handle custom message types
        """
        pass
    
    def start_game(self):
        """
        Start the game
        """
        self.game_started = True
        self.current_round = 1
        
        # Game-specific setup
        self.setup_game()
        
        print(f"Game started with {len(self.clients)} players!")
        
        # Notify all players
        self.broadcast_to_all({
            'type': 'game_start',
            'game_state': self.game_state,
            'total_players': len(self.clients),
            'current_round': self.current_round
        })
        
        # Start first round
        self.start_round(self.current_round)
    
    def setup_game(self):
        """
        Override for game-specific setup
        """
        # Initialize scores
        with self.lock:
            for player_id in range(len(self.clients)):
                self.scores[player_id] = 0
            
            self.game_state['phase'] = 'playing'
            self.game_state['scores'] = self.scores.copy()
    
    def start_round(self, round_num):
        """
        Start a new round
        """
        print(f"Starting round {round_num}")
        
        self.broadcast_to_all({
            'type': 'round_start',
            'round': round_num,
            'total_rounds': self.max_rounds,
            'game_state': self.game_state
        })
    
    def check_game_progress(self):
        """
        Check if round or game should end
        Override for game-specific logic
        """
        pass
    
    def end_round(self, round_num, results):
        """
        End current round and send results
        """
        print(f"Ending round {round_num}")
        
        # Update scores
        for player_id, points in results.get('score_changes', {}).items():
            if player_id in self.scores:
                self.scores[player_id] += points
        
        # Update game state
        with self.lock:
            self.game_state['scores'] = self.scores.copy()
        
        # Send round results
        self.broadcast_to_all({
            'type': 'round_result',
            'round': round_num,
            'results': results,
            'game_state': self.game_state
        })
        
        time.sleep(3)  # Give players time to see results
        
        # Check if game should continue
        self.current_round += 1
        
        if self.current_round <= self.max_rounds:
            self.start_round(self.current_round)
        else:
            self.end_game()
    
    def end_game(self):
        """
        End the game and show final results
        """
        print("Game ended! Calculating final scores...")
        
        # Determine winners
        max_score = max(self.scores.values())
        winners = [pid for pid, score in self.scores.items() if score == max_score]
        
        print(f"Final scores: {self.scores}")
        print(f"Winners: {winners}")
        
        final_results = {
            'final_scores': self.scores,
            'winners': winners
        }
        
        self.broadcast_to_all({
            'type': 'game_end',
            'results': final_results,
            'game_state': self.game_state
        })
        
        print("Resetting game state...")
        self.reset_game()
    
    def reset_game(self):
        """
        Reset game state for new game
        """
        self.game_started = False
        self.players_ready = 0
        self.current_round = 0
        self.scores = {}
        
        # Reset player ready status
        with self.lock:
            for client in self.clients:
                if client in self.client_info:
                    self.client_info[client]['ready'] = False
            
            self.game_state['phase'] = 'lobby'
            self.game_state['ready_count'] = 0
            for player_id in self.game_state['players']:
                self.game_state['players'][player_id]['ready'] = False
    
    def handle_disconnect(self, client, player_id):
        """
        Handle client disconnection
        """
        print(f"\nPlayer {player_id + 1} disconnected")
        
        with self.lock:
            if client in self.clients:
                self.clients.remove(client)
            if client in self.client_info:
                del self.client_info[client]
            if player_id in self.game_state['players']:
                self.game_state['players'][player_id]['connected'] = False
        
        if self.game_started:
            print("Game in progress, handling player disconnect...")
            self.handle_in_game_disconnect(player_id)
        else:
            with self.lock:
                self.players_ready = sum(1 for c in self.clients 
                                      if self.client_info.get(c, {}).get('ready', False))
                self.game_state['ready_count'] = self.players_ready
            
            self.broadcast({
                'type': 'player_left',
                'player_id': player_id,
                'ready_count': self.players_ready,
                'total_players': len(self.clients),
                'game_state': self.game_state
            })
    
    def handle_in_game_disconnect(self, player_id):
        """
        Override to handle disconnection during game
        Default behavior: end game
        """
        print("Ending game due to player disconnect")
        self.broadcast({
            'type': 'player_left',
            'player_id': player_id,
            'message': 'Game ended due to player disconnect',
            'game_state': self.game_state
        })
        self.reset_game()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    server = MultiplayerGUIServerTemplate(port)
    server.start()