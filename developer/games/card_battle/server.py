# developer/games/card_battle/server.py
import socket
import threading
import json
import random
import time
import sys
import os

class CardBattleServer:
    def __init__(self, port=6002):
        self.port = port
        self.clients = []
        self.client_info = {} 
        self.players_ready = 0
        self.game_started = False
        self.deck = list(range(1, 101))
        self.player_cards = {}  
        self.selected_cards = {}  
        self.revealed_cards = {} 
        self.round_results = []
        self.current_round = 0
        self.max_rounds = 7
        self.scores = {}  
        self.lock = threading.Lock()
        self.game_thread = None
        self.shutting_down = False
        
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(5) 
        
        print(f"[Card Battle] Server started on port {self.port}")
        print("Waiting for players (2-5 players required)...")
        
        try:
            while not self.shutting_down:
                client, addr = server.accept()
                if len(self.clients) >= 5:
                    self.send_message(client, {
                        'type': 'error',
                        'message': 'Room is full (max 5 players)'
                    })
                    client.close()
                    continue
                    
                player_id = len(self.clients)
                
                with self.lock:
                    self.clients.append(client)
                    self.client_info[client] = {
                        'player_id': player_id,
                        'name': f'Player {player_id + 1}',
                        'ready': False,
                        'connected': True
                    }
                    self.scores[player_id] = 0
                
                self.send_message(client, {
                    'type': 'welcome',
                    'player_id': player_id,
                    'message': f'Welcome Player {player_id + 1}! Please set your name.'
                })
                
                self.broadcast({
                    'type': 'player_joined',
                    'player_id': player_id,
                    'name': f'Player {player_id + 1}',
                    'total_players': len(self.clients)
                })
                
                thread = threading.Thread(target=self.handle_client, args=(client, player_id))
                thread.daemon = True
                thread.start()
                
                print(f"Player {player_id + 1} connected from {addr}")
        except KeyboardInterrupt:
            print("\nServer shutting down...")
            self.shutting_down = True
            self.end_game_all("Server shutting down")
        finally:
            server.close()
    
    def send_message(self, client, data):
        try:
            message = json.dumps(data) + '\n'
            client.sendall(message.encode())
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def broadcast(self, data, exclude=None):
        exclude = exclude or []
        for client in list(self.clients):
            if client in exclude:
                continue
            if self.client_info.get(client, {}).get('connected', False):
                try:
                    self.send_message(client, data)
                except:
                    pass
    
    def broadcast_to_all(self, data):
        for client in list(self.clients):
            if self.client_info.get(client, {}).get('connected', False):
                try:
                    self.send_message(client, data)
                except:
                    pass
    
    def end_game_all(self, reason):
        """End game for all players with a reason"""
        end_message = {
            'type': 'game_end',
            'final_scores': self.scores.copy(),
            'champions': [],
            'round_results': self.round_results,
            'reason': reason,
            'forced_shutdown': True
        }
        
        for client in list(self.clients):
            if self.client_info.get(client, {}).get('connected', False):
                try:
                    self.send_message(client, end_message)
                    client.close()
                except:
                    pass
        
        print(f"Game ended: {reason}")
    
    def handle_client_disconnect(self, client, player_id):
        """Handle player disconnection"""
        with self.lock:
            if client in self.clients:
                self.clients.remove(client)
            
            if client in self.client_info:
                self.client_info[client]['connected'] = False
                player_name = self.client_info[client]['name']
                
                if self.client_info[client]['ready']:
                    self.players_ready -= 1
                    self.client_info[client]['ready'] = False
            
            print(f"Player {player_id + 1} ({player_name}) disconnected")
            
            # Update scores to remove disconnected player
            if player_id in self.scores:
                del self.scores[player_id]
        
        if self.game_started:
            # If game is in progress, end it for everyone
            disconnect_reason = f"Player {player_name} disconnected"
            self.broadcast_to_all({
                'type': 'player_disconnected',
                'player_id': player_id,
                'name': player_name,
                'reason': disconnect_reason
            })
            
            time.sleep(0.5)  # Give clients time to process message
            
            # Send game end message
            self.end_game_all(disconnect_reason)
            
            # Reset server state
            self.__init__(self.port)
        else:
            # If game hasn't started, just update player list
            self.broadcast({
                'type': 'player_left',
                'player_id': player_id,
                'ready_count': self.players_ready,
                'total_players': len(self.clients)
            })
    
    def handle_client(self, client, player_id):
        try:
            buffer = ''
            while True:
                if self.shutting_down:
                    break
                    
                try:
                    client.settimeout(1.0)
                    data = client.recv(1024).decode()
                    if not data:
                        break
                    
                    buffer += data
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line:
                            try:
                                message = json.loads(line)
                                self.process_message(client, player_id, message)
                            except json.JSONDecodeError:
                                print(f"Invalid JSON from player {player_id + 1}")
                                continue
                except socket.timeout:
                    continue
                except ConnectionError:
                    break
                except Exception as e:
                    print(f"Error receiving from player {player_id + 1}: {e}")
                    break
                
        except Exception as e:
            print(f"Player {player_id + 1} connection error: {e}")
        finally:
            self.handle_client_disconnect(client, player_id)
    
    def process_message(self, client, player_id, message):
        msg_type = message['type']
        
        if msg_type == 'set_name':
            new_name = message['name']
            with self.lock:
                self.client_info[client]['name'] = new_name
            
            print(f"Player {player_id + 1} set name to: {new_name}")
            
            self.broadcast({
                'type': 'player_joined',
                'player_id': player_id,
                'name': new_name,
                'total_players': len(self.clients)
            })
            
        elif msg_type == 'ready':
            with self.lock:
                if not self.client_info[client]['ready']:
                    self.client_info[client]['ready'] = True
                    self.players_ready += 1
                    print(f"Player {player_id + 1} is ready. Ready count: {self.players_ready}/{len(self.clients)}")
            
            self.broadcast({
                'type': 'player_ready',
                'player_id': player_id,
                'ready_count': self.players_ready,
                'total_players': len(self.clients)
            })
            
            if 2 <= len(self.clients) <= 5 and self.players_ready == len(self.clients):
                print(f"All players ready! Starting game...")
                time.sleep(1)  
                self.start_game()
                
        elif msg_type == 'select_card':
            if not self.game_started:
                print(f"Game not started yet, but player {player_id + 1} tried to select card")
                return
                
            if not self.client_info[client]['connected']:
                return
                
            card = message['card']
            round_num = message['round']
            
            print(f"Player {player_id + 1} selected card {card} in round {round_num}")
            
            with self.lock:
                if round_num not in self.selected_cards:
                    self.selected_cards[round_num] = {}
                
                if player_id in self.selected_cards[round_num]:
                    print(f"Player {player_id + 1} already selected a card in round {round_num}")
                    return
                
                self.selected_cards[round_num][player_id] = card
                
                if player_id in self.player_cards:
                    try:
                        self.player_cards[player_id].remove(card)
                        print(f"Removed card {card} from player {player_id + 1}'s hand")
                    except ValueError:
                        print(f"Card {card} not found in player {player_id + 1}'s hand")
            
            self.send_message(client, {
                'type': 'card_selected',
                'player_id': player_id,
                'card': card,
                'round': round_num,
                'remaining': len(self.selected_cards[round_num]),
                'total_players': len(self.clients)
            })
            
            print(f"Round {round_num}: {len(self.selected_cards[round_num])}/{len(self.clients)} players have selected")
            
            self.broadcast({
                'type': 'player_ready_in_round',
                'player_id': player_id,
                'round': round_num,
                'remaining': len(self.selected_cards[round_num]),
                'total_players': len(self.clients)
            }, exclude=[client])
            
            if len(self.selected_cards[round_num]) == len(self.clients):
                print(f"All players selected cards in round {round_num}. Revealing cards...")
                self.reveal_cards(round_num)
            else:
                print(f"Still waiting for {len(self.clients) - len(self.selected_cards[round_num])} players")
    
    def start_game(self):
        self.game_started = True
        
        self.deck = list(range(1, 101))
        random.shuffle(self.deck)
        self.player_cards = {}
        self.selected_cards = {}
        self.revealed_cards = {}
        self.round_results = []
        self.current_round = 1
        self.scores = {i: 0 for i in range(len(self.clients))}
        
        print("Game started! Dealing cards...")
        
        with self.lock:
            for i, client in enumerate(self.clients):
                if not self.client_info[client]['connected']:
                    continue
                    
                start_idx = i * 7
                end_idx = start_idx + 7
                cards = self.deck[start_idx:end_idx]
                self.player_cards[i] = cards.copy()
                
                print(f"Player {i + 1} got cards: {cards}")
                
                self.send_message(client, {
                    'type': 'game_start',
                    'player_id': i,
                    'cards': cards,
                    'total_players': len(self.clients)
                })
        
        time.sleep(1)
        
        print(f"Starting round {self.current_round}")
        
        self.broadcast_to_all({
            'type': 'round_start',
            'round': self.current_round,
            'total_rounds': self.max_rounds
        })
    
    def reveal_cards(self, round_num):
        print(f"\n=== Revealing Round {round_num} Cards ===")
        
        self.revealed_cards[round_num] = self.selected_cards[round_num].copy()
        
        max_card = max(self.revealed_cards[round_num].values())
        print(f"Highest card: {max_card}")
        
        winners = [pid for pid, card in self.revealed_cards[round_num].items() if card == max_card]
        print(f"Winners: {winners}")
        
        for winner in winners:
            self.scores[winner] += 1
            print(f"Player {winner + 1} gets 1 point. Total: {self.scores[winner]}")
        
        round_result = {
            'round': round_num,
            'cards': self.revealed_cards[round_num], 
            'max_card': max_card,
            'winners': winners,
            'scores': self.scores.copy()
        }
        self.round_results.append(round_result)
        
        print(f"Round {round_num} scores: {self.scores}")
        
        self.broadcast_to_all({
            'type': 'round_result',
            'result': round_result
        })
        
        print(f"Waiting 3 seconds before next round...")
        time.sleep(3)
        
        self.current_round += 1
        
        if self.current_round <= self.max_rounds:
            print(f"\n=== Starting Round {self.current_round} ===")
            
            self.selected_cards[self.current_round] = {}
            
            self.broadcast_to_all({
                'type': 'round_start',
                'round': self.current_round,
                'total_rounds': self.max_rounds
            })
        else:
            print("\n=== Game Over ===")
            self.end_game()
    
    def end_game(self):
        print("Game ended! Calculating final scores...")
        
        max_score = max(self.scores.values())
        champions = [pid for pid, score in self.scores.items() if score == max_score]
        
        print(f"Final scores: {self.scores}")
        print(f"Champions: {champions}")
        
        final_results = {
            'type': 'game_end',
            'final_scores': self.scores,
            'champions': champions,
            'round_results': self.round_results
        }
        
        self.broadcast_to_all(final_results)
        
        print("Resetting game state...")
        self.__init__(self.port)

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6002
    server = CardBattleServer(port)
    server.start()