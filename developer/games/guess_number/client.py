# developer/games/guess_number/client.py
import socket
import threading
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class GuessNumberClient:
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
                
                if "Enter your guess" in message:
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
        print("Waiting for other player...\n")
        
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()
        
        try:
            while self.running:
                if self.is_my_turn:
                    try:
                        sys.stdout.write("> ")
                        sys.stdout.flush()
                        guess = sys.stdin.readline().strip()
                        if not self.running:
                            break
                        
                        if guess.lower() == 'quit':
                            break
                            
                        self.socket.sendall((guess + '\n').encode())
                        self.is_my_turn = False
                    except EOFError:
                        break
                else:
                    import time
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\n\nGame interrupted by user.")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            self.socket.close()
            print("Disconnected from server.")

if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    client = GuessNumberClient(host, port)
    client.run()