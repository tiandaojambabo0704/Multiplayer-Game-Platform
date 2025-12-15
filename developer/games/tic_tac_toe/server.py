# developer/games/tic_tac_toe/server.py
import socket
import threading
import json
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class TicTacToeServer:
    def __init__(self, port=6001):
        self.port = port
        self.clients = []
        self.board = [['' for _ in range(3)] for _ in range(3)]
        self.current_player = 0
        self.game_over = False
        self.players_active = [False, False]  # Track active players
        
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(2)
        
        print(f"[Tic Tac Toe] Server started on port {self.port}")
        
        while len(self.clients) < 2:
            client, addr = server.accept()
            player_num = len(self.clients)
            self.clients.append(client)
            self.players_active[player_num] = True
            symbol = 'X' if player_num == 0 else 'O'
            print(f"Player {player_num + 1} ({symbol}) connected from {addr}")
            self.send_message(client, {
                'type': 'init',
                'player': player_num,
                'symbol': symbol
            })
        
        self.broadcast({'type': 'start', 'message': 'Game started!'})
        self.broadcast({'type': 'turn', 'player': 0})
        
        for i, client in enumerate(self.clients):
            thread = threading.Thread(target=self.handle_client, args=(client, i))
            thread.daemon = True
            thread.start()
        
        # Keep server running
        try:
            while not self.game_over:
                threading.Event().wait(0.1)
        except KeyboardInterrupt:
            self.end_game("Server stopped")
    
    def send_message(self, client, data):
        try:
            message = json.dumps(data) + '\n'
            client.sendall(message.encode())
        except:
            pass
    
    def broadcast(self, data):
        for i, client in enumerate(self.clients):
            if self.players_active[i]:
                self.send_message(client, data)
    
    def end_game(self, reason):
        if self.game_over:
            return
        
        self.game_over = True
        print(f"[System] Game ended: {reason}")
        
        end_msg = {'type': 'end', 'result': 'disconnect', 'reason': reason}
        
        for i, client in enumerate(self.clients):
            if self.players_active[i]:
                try:
                    self.send_message(client, end_msg)
                    client.close()
                except:
                    pass
    
    def check_winner(self):
        # Check rows
        for row in self.board:
            if row[0] == row[1] == row[2] != '':
                return row[0]
        
        # Check columns
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] != '':
                return self.board[0][col]
        
        # Check diagonals
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != '':
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != '':
            return self.board[0][2]
        
        # Check draw
        if all(self.board[i][j] != '' for i in range(3) for j in range(3)):
            return 'DRAW'
        
        return None
    
    def handle_client_disconnect(self, player_num):
        self.players_active[player_num] = False
        
        if self.game_over:
            return
        
        reason = f"Player {player_num + 1} disconnected"
        print(f"[System] {reason}")
        
        # Notify other player
        other_player = 1 - player_num
        if self.players_active[other_player]:
            disconnect_msg = {'type': 'disconnect', 'reason': reason}
            self.send_message(self.clients[other_player], disconnect_msg)
        
        # End the game
        self.end_game(reason)
    
    def handle_client(self, client, player_num):
        try:
            while not self.game_over:
                data = client.recv(1024).decode().strip()
                if not data:
                    # Client disconnected
                    self.handle_client_disconnect(player_num)
                    break
                
                message = json.loads(data)
                
                if message['type'] == 'move':
                    if not self.players_active[player_num]:
                        break
                        
                    if player_num != self.current_player:
                        self.send_message(client, {'type': 'error', 'message': 'Not your turn!'})
                        continue
                    
                    row, col = message['row'], message['col']
                    
                    if self.board[row][col] != '':
                        self.send_message(client, {'type': 'error', 'message': 'This cell is already taken!'})
                        continue
                    
                    symbol = 'X' if player_num == 0 else 'O'
                    self.board[row][col] = symbol
                    
                    self.broadcast({
                        'type': 'move',
                        'player': player_num,
                        'row': row,
                        'col': col,
                        'symbol': symbol
                    })
                    
                    winner = self.check_winner()
                    if winner:
                        self.game_over = True
                        if winner == 'DRAW':
                            self.broadcast({'type': 'end', 'result': 'draw'})
                        else:
                            winner_player = 0 if winner == 'X' else 1
                            self.broadcast({'type': 'end', 'result': 'win', 'winner': winner_player})
                        break
                    
                    self.current_player = 1 - self.current_player
                    self.broadcast({'type': 'turn', 'player': self.current_player})
        
        except ConnectionError:
            self.handle_client_disconnect(player_num)
        except json.JSONDecodeError:
            self.handle_client_disconnect(player_num)
        except Exception as e:
            print(f"Error with player {player_num + 1}: {e}")
            self.handle_client_disconnect(player_num)
        finally:
            try:
                client.close()
            except:
                pass

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6001
    server = TicTacToeServer(port)
    server.start()