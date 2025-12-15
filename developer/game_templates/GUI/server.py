# developer/game_templates/GUI/server.py
import socket
import threading
import json
import sys

class GUIGameServerTemplate:
    def __init__(self, port):
        """
        Initialize GUI game server
        """
        self.port = port
        self.clients = []
        self.players = []
        self.game_state = self.initialize_game_state()
        self.current_turn = 0
        self.game_started = False
        self.game_over = False
        
    def initialize_game_state(self):
        """
        Override this method to initialize game-specific state
        """
        return {}
    
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
    
    def start(self):
        """
        Start server and wait for players
        """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(self.get_max_players())
        
        print(f"[{self.get_game_name()}] Server started on port {self.port}")
        
        while len(self.clients) < self.get_max_players():
            client, addr = server.accept()
            player_num = len(self.clients)
            self.clients.append(client)
            
            # Create player info
            player_info = self.create_player_info(player_num)
            self.players.append(player_info)
            
            print(f"Player {player_num + 1} connected from {addr}")
            
            # Send initialization message
            self.send_message(client, {
                'type': 'init',
                'player': player_num,
                'player_info': player_info,
                'game_state': self.game_state
            })
        
        self.game_started = True
        self.on_game_start()
        
        for i, client in enumerate(self.clients):
            thread = threading.Thread(target=self.handle_client, args=(client, i))
            thread.start()
    
    def get_game_name(self):
        """
        Override to return game name
        """
        return "GUI Game Template"
    
    def create_player_info(self, player_num):
        """
        Override to create player-specific information
        """
        return {
            'number': player_num,
            'symbol': 'X' if player_num == 0 else 'O',
            'score': 0
        }
    
    def send_message(self, client, data):
        """
        Send JSON message to client
        """
        try:
            message = json.dumps(data) + '\n'
            client.sendall(message.encode())
        except:
            pass
    
    def broadcast(self, data, exclude=None):
        """
        Broadcast message to all clients
        """
        for i, client in enumerate(self.clients):
            if exclude is None or i != exclude:
                self.send_message(client, data)
    
    def on_game_start(self):
        """
        Override to execute actions when game starts
        """
        self.broadcast({
            'type': 'start',
            'message': f'{self.get_game_name()} started!',
            'game_state': self.game_state
        })
        self.broadcast({
            'type': 'turn',
            'player': self.current_turn
        })
    
    def handle_client(self, client, player_num):
        """
        Handle client connection
        """
        try:
            while not self.game_over:
                data = client.recv(1024).decode().strip()
                if not data:
                    break
                
                try:
                    message = json.loads(data)
                    self.process_client_message(client, player_num, message)
                except json.JSONDecodeError:
                    self.send_message(client, {
                        'type': 'error',
                        'message': 'Invalid message format'
                    })
        
        except Exception as e:
            print(f"Error with player {player_num}: {e}")
        finally:
            client.close()
    
    def process_client_message(self, client, player_num, message):
        """
        Process messages from client
        """
        msg_type = message.get('type')
        
        if msg_type == 'move':
            self.handle_player_move(client, player_num, message)
        elif msg_type == 'action':
            self.handle_player_action(client, player_num, message)
        elif msg_type == 'chat':
            self.handle_chat_message(player_num, message)
    
    def handle_player_move(self, client, player_num, message):
        """
        Override to handle player moves
        """
        if player_num != self.current_turn:
            self.send_message(client, {
                'type': 'error',
                'message': 'Not your turn'
            })
            return
        
        move_result = self.validate_and_process_move(player_num, message)
        
        if not move_result.get('valid'):
            self.send_message(client, {
                'type': 'error',
                'message': move_result.get('message', 'Invalid move')
            })
            return
        
        # Broadcast move to all players
        self.broadcast({
            'type': 'move',
            'player': player_num,
            'move_data': move_result.get('move_data'),
            'game_state': self.game_state
        })
        
        # Check for game end
        game_result = self.check_game_result()
        if game_result:
            self.end_game(game_result)
            return
        
        # Switch turn
        self.switch_turn()
    
    def validate_and_process_move(self, player_num, message):
        """
        Override to validate and process a move
        Returns: {'valid': True/False, 'message': str, 'move_data': dict}
        """
        # Example validation - override in actual game
        return {
            'valid': True,
            'message': 'Move accepted',
            'move_data': {'action': 'placeholder'}
        }
    
    def handle_player_action(self, client, player_num, message):
        """
        Override to handle other player actions
        """
        pass
    
    def handle_chat_message(self, player_num, message):
        """
        Handle chat messages
        """
        self.broadcast({
            'type': 'chat',
            'player': player_num,
            'message': message.get('text', ''),
            'timestamp': message.get('timestamp')
        })
    
    def check_game_result(self):
        """
        Override to check if game has ended
        Returns: None if game continues, dict with result if game ends
        """
        return None
    
    def switch_turn(self):
        """
        Switch to next player's turn
        """
        self.current_turn = (self.current_turn + 1) % len(self.clients)
        self.broadcast({
            'type': 'turn',
            'player': self.current_turn
        })
    
    def end_game(self, result):
        """
        End the game with given result
        """
        self.game_over = True
        self.broadcast({
            'type': 'end',
            'result': result
        })

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    server = GUIGameServerTemplate(port)
    server.start()