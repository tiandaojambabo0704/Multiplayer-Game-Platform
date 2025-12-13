# server/database.py
import json
import os
from datetime import datetime
from threading import Lock

class Database:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.locks = {
            'developers': Lock(),
            'players': Lock(),
            'games': Lock(),
            'rooms': Lock(),
            'reviews': Lock(),
            'downloads': Lock()
        }
        self.init_database()
    
    def init_database(self):
        os.makedirs(self.data_dir, exist_ok=True)
        
        default_data = {
            'developers.json': {},
            'players.json': {},
            'games.json': {},
            'rooms.json': {},
            'reviews.json': {},
            'downloads.json': {}
        }
        
        for filename, default in default_data.items():
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                self.save_json(filepath, default)
    
    def load_json(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_json(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def register_developer(self, username, password):
        with self.locks['developers']:
            filepath = os.path.join(self.data_dir, 'developers.json')
            devs = self.load_json(filepath)
            
            if username in devs:
                return False, "帳號已存在"
            
            devs[username] = {
                'password': password,
                'created_at': datetime.now().isoformat(),
                'games': []
            }
            self.save_json(filepath, devs)
            return True, "註冊成功"
    
    def login_developer(self, username, password):
        with self.locks['developers']:
            filepath = os.path.join(self.data_dir, 'developers.json')
            devs = self.load_json(filepath)
            
            if username not in devs:
                return False, "帳號不存在"
            
            if devs[username]['password'] != password:
                return False, "密碼錯誤"
            
            return True, "登入成功"
    
    def register_player(self, username, password):
        with self.locks['players']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if username in players:
                return False, "帳號已存在"
            
            players[username] = {
                'password': password,
                'created_at': datetime.now().isoformat(),
                'downloaded_games': {},
                'played_games': [],
                'game_stats': {}
            }
            self.save_json(filepath, players)
            return True, "註冊成功"
    
    def login_player(self, username, password):
        with self.locks['players']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if username not in players:
                return False, "帳號不存在"
            
            if players[username]['password'] != password:
                return False, "密碼錯誤"
            
            return True, "登入成功"
    
    def add_game(self, game_id, game_data):
        with self.locks['games']:
            filepath = os.path.join(self.data_dir, 'games.json')
            games = self.load_json(filepath)
            
            # 記錄版本歷史
            if 'version_history' not in game_data:
                game_data['version_history'] = []
            
            game_data['version_history'].append({
                'version': game_data['version'],
                'time': datetime.now().isoformat(),
                'type': 'initial'
            })
            
            games[game_id] = game_data
            self.save_json(filepath, games)
            
            dev_filepath = os.path.join(self.data_dir, 'developers.json')
            devs = self.load_json(dev_filepath)
            if game_data['developer'] in devs:
                if game_id not in devs[game_data['developer']]['games']:
                    devs[game_data['developer']]['games'].append(game_id)
                    self.save_json(dev_filepath, devs)
    
    def get_all_games(self):
        with self.locks['games']:
            filepath = os.path.join(self.data_dir, 'games.json')
            return self.load_json(filepath)
    
    def get_game(self, game_id):
        games = self.get_all_games()
        return games.get(game_id)
    
    def update_game(self, game_id, game_data):
        with self.locks['games']:
            filepath = os.path.join(self.data_dir, 'games.json')
            games = self.load_json(filepath)
            
            if game_id in games:
                # 檢查遊戲是否已下架
                if games[game_id].get('status') == 'removed':
                    return False
                
                new_version = game_data.get('version')
                current_version = games[game_id].get('version')
                
                # 如果版本有更新，記錄版本歷史
                if new_version != current_version:
                    if 'version_history' not in games[game_id]:
                        games[game_id]['version_history'] = []
                    
                    games[game_id]['version_history'].append({
                        'version': new_version,
                        'time': datetime.now().isoformat(),
                        'type': 'update'
                    })
                
                # 更新遊戲資料
                games[game_id].update(game_data)
                self.save_json(filepath, games)
                return True
            return False
    
    def delete_game(self, game_id):
        with self.locks['games']:
            filepath = os.path.join(self.data_dir, 'games.json')
            games = self.load_json(filepath)
            if game_id in games:
                games[game_id]['status'] = 'removed'
                games[game_id]['removed_at'] = datetime.now().isoformat()
                self.save_json(filepath, games)
                return True
            return False
    
    def is_game_removed(self, game_id):
        games = self.get_all_games()
        if game_id in games:
            return games[game_id].get('status') == 'removed'
        return True
    
    def get_developer_games(self, developer):
        games = self.get_all_games()
        return {gid: gdata for gid, gdata in games.items() 
                if gdata.get('developer') == developer}
    
    def get_developer_active_games(self, developer):
        games = self.get_all_games()
        return {gid: gdata for gid, gdata in games.items() 
                if gdata.get('developer') == developer and gdata.get('status') != 'removed'}
    
    def create_room(self, room_id, room_data):
        with self.locks['rooms']:
            filepath = os.path.join(self.data_dir, 'rooms.json')
            rooms = self.load_json(filepath)
            rooms[room_id] = room_data
            self.save_json(filepath, rooms)
    
    def get_all_rooms(self):
        with self.locks['rooms']:
            filepath = os.path.join(self.data_dir, 'rooms.json')
            return self.load_json(filepath)
    
    def get_room(self, room_id):
        rooms = self.get_all_rooms()
        return rooms.get(room_id)
    
    def update_room(self, room_id, room_data):
        with self.locks['rooms']:
            filepath = os.path.join(self.data_dir, 'rooms.json')
            rooms = self.load_json(filepath)
            if room_id in rooms:
                rooms[room_id].update(room_data)
                self.save_json(filepath, rooms)
                return True
            return False
    
    def delete_room(self, room_id):
        with self.locks['rooms']:
            filepath = os.path.join(self.data_dir, 'rooms.json')
            rooms = self.load_json(filepath)
            if room_id in rooms:
                del rooms[room_id]
                self.save_json(filepath, rooms)
                return True
            return False
    
    def add_review(self, game_id, player, rating, comment):
        with self.locks['reviews']:
            filepath = os.path.join(self.data_dir, 'reviews.json')
            reviews = self.load_json(filepath)
            
            if game_id not in reviews:
                reviews[game_id] = []
            
            reviews[game_id].append({
                'player': player,
                'rating': rating,
                'comment': comment,
                'time': datetime.now().isoformat(),
                'validated': True
            })
            self.save_json(filepath, reviews)
    
    def get_game_reviews(self, game_id):
        with self.locks['reviews']:
            filepath = os.path.join(self.data_dir, 'reviews.json')
            reviews = self.load_json(filepath)
            return reviews.get(game_id, [])
    
    def record_download(self, player, game_id, version, is_update=False):
        with self.locks['downloads']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if player in players:
                if 'downloaded_games' not in players[player]:
                    players[player]['downloaded_games'] = {}
                
                players[player]['downloaded_games'][game_id] = {
                    'version': version,
                    'download_time': datetime.now().isoformat(),
                    'status': 'active',
                    'is_latest': True,  # 標記是否為最新版本
                    'last_check': datetime.now().isoformat(),
                    'update_available': False  # 是否有更新可用
                }
                
                # 如果是更新，保留舊的下載記錄
                if is_update and 'game_download_history' not in players[player]:
                    players[player]['game_download_history'] = {}
                
                if is_update:
                    if 'game_download_history' not in players[player]:
                        players[player]['game_download_history'] = {}
                    
                    if game_id not in players[player]['game_download_history']:
                        players[player]['game_download_history'][game_id] = []
                    
                    players[player]['game_download_history'][game_id].append({
                        'version': version,
                        'time': datetime.now().isoformat(),
                        'type': 'update'
                    })
                
                self.save_json(filepath, players)
    
    def get_player_downloads(self, player):
        with self.locks['downloads']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            if player in players:
                downloads = players[player].get('downloaded_games', {})
                # 檢查每個遊戲是否已下架
                all_games = self.get_all_games()
                for game_id in list(downloads.keys()):
                    if game_id in all_games:
                        game_info = all_games[game_id]
                        # 檢查遊戲狀態
                        if game_info.get('status') == 'removed':
                            downloads[game_id]['status'] = 'removed'
                        
                        # 檢查版本是否最新
                        server_version = game_info.get('version')
                        local_version = downloads[game_id].get('version')
                        
                        if server_version != local_version:
                            downloads[game_id]['update_available'] = True
                            downloads[game_id]['server_version'] = server_version
                            downloads[game_id]['is_latest'] = False
                        else:
                            downloads[game_id]['update_available'] = False
                            downloads[game_id]['is_latest'] = True
                    
                    # 移除已刪除的遊戲
                    elif game_id not in all_games:
                        downloads[game_id]['status'] = 'deleted'
                
                return downloads
            return {}
    
    def check_version_update(self, player, game_id):
        """檢查遊戲是否有新版本"""
        with self.locks['downloads']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if player in players:
                downloads = players[player].get('downloaded_games', {})
                if game_id in downloads:
                    # 獲取遊戲的最新版本
                    all_games = self.get_all_games()
                    if game_id in all_games:
                        game_info = all_games[game_id]
                        server_version = game_info.get('version')
                        local_version = downloads[game_id].get('version')
                        
                        # 比較版本
                        if server_version != local_version:
                            # 更新下載記錄中的狀態
                            downloads[game_id]['update_available'] = True
                            downloads[game_id]['server_version'] = server_version
                            downloads[game_id]['is_latest'] = False
                            downloads[game_id]['last_check'] = datetime.now().isoformat()
                            
                            self.save_json(filepath, players)
                            return {
                                'update_available': True,
                                'local_version': local_version,
                                'server_version': server_version,
                                'game_name': game_info.get('name', 'Unknown')
                            }
                        else:
                            # 已經是最新版本
                            downloads[game_id]['update_available'] = False
                            downloads[game_id]['is_latest'] = True
                            downloads[game_id]['last_check'] = datetime.now().isoformat()
                            self.save_json(filepath, players)
            
            return {'update_available': False}
    
    def mark_as_latest(self, player, game_id):
        """標記遊戲為最新版本"""
        with self.locks['downloads']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if player in players and game_id in players[player].get('downloaded_games', {}):
                players[player]['downloaded_games'][game_id]['update_available'] = False
                players[player]['downloaded_games'][game_id]['is_latest'] = True
                players[player]['downloaded_games'][game_id]['last_check'] = datetime.now().isoformat()
                self.save_json(filepath, players)
                return True
            return False
    
    def update_download_status(self, player, game_id, status):
        with self.locks['downloads']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if player in players and game_id in players[player].get('downloaded_games', {}):
                players[player]['downloaded_games'][game_id]['status'] = status
                self.save_json(filepath, players)
                return True
            return False
    
    def record_play(self, player, game_id):
        with self.locks['players']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if player in players:
                if game_id not in players[player]['played_games']:
                    players[player]['played_games'].append(game_id)
                
                if 'game_stats' not in players[player]:
                    players[player]['game_stats'] = {}
                
                if game_id not in players[player]['game_stats']:
                    players[player]['game_stats'][game_id] = {
                        'play_count': 1,
                        'first_played': datetime.now().isoformat(),
                        'last_played': datetime.now().isoformat()
                    }
                else:
                    stats = players[player]['game_stats'][game_id]
                    stats['play_count'] = stats.get('play_count', 0) + 1
                    stats['last_played'] = datetime.now().isoformat()
                
                self.save_json(filepath, players)
                return True
            return False
    
    def has_player_played_game(self, player, game_id):
        with self.locks['players']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if player in players:
                played_games = players[player].get('played_games', [])
                return game_id in played_games
            return False
    
    def get_player_played_games(self, player):
        with self.locks['players']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if player in players:
                return players[player].get('played_games', [])
            return []
    
    def get_player_game_stats(self, player, game_id):
        with self.locks['players']:
            filepath = os.path.join(self.data_dir, 'players.json')
            players = self.load_json(filepath)
            
            if player in players:
                return players[player].get('game_stats', {}).get(game_id, {})
            return {}