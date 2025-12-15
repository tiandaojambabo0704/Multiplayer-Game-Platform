# developer/game_templates/CLI/client.py
import socket
import threading
import sys

class GameClientTemplate:
    def __init__(self, host='localhost', port=6000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True
        self.is_my_turn = False
        
    def connect(self):
        try:
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Cannot connect to game server: {e}")
            return False
    
    def receive_messages(self):
        while self.running:
            try:
                message = self.socket.recv(1024).decode('utf-8')
                if not message:
                    break
                
                if "GAME_END" in message:
                    self.running = False
                    print(message.replace("GAME_END", ""))
                    break
                
                if "Enter your" in message or "your turn" in message:
                    self.is_my_turn = True
                elif "Waiting for Player" in message:
                    self.is_my_turn = False
                
                sys.stdout.write(message)
                sys.stdout.flush()
                
            except Exception as e:
                print(f"\nConnection error: {e}")
                break
    
    def run(self):
        if not self.connect():
            return
        
        print("Connected to game server!")
        
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()
        
        try:
            while self.running:
                if self.is_my_turn:
                    try:
                        sys.stdout.write("> ")
                        sys.stdout.flush()
                        user_input = sys.stdin.readline().strip()
                        if not self.running:
                            break
                        
                        if user_input.lower() == 'quit':
                            break
                            
                        self.socket.sendall((user_input + '\n').encode())
                        self.is_my_turn = False
                    except EOFError:
                        break
                else:
                    import time
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\nGame interrupted by user.")
        finally:
            self.socket.close()
            print("Disconnected from server.")

if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    client = GameClientTemplate(host, port)
    client.run()