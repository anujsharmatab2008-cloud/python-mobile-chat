import socket
import threading
import random
import string
import time
from database import init_db, save_message, get_room_history

HOST = '0.0.0.0'  # Broadcasts across your entire local network interface
PORT = 55555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(50)  # Max connection queue backlog optimized for up to 50 active users

rooms = {}       # State tracking: { "ROOM_CODE": [socket1, socket2] }
client_data = {} # Config mapping: { socket1: ("Username", "ROOM_CODE") }

def broadcast(room_code, text, skip_client=None):
    """Instantly forwards a message to every device inside a targeted room."""
    if room_code in rooms:
        for client in rooms[room_code]:
            if client != skip_client:
                try:
                    client.send(text.encode('utf-8'))
                except:
                    disconnect(client)

def disconnect(client):
    """Removes broken or manual disconnection entries cleanly."""
    if client in client_data:
        nick, room = client_data[client]
        if room in rooms and client in rooms[room]:
            rooms[room].remove(client)
            if not rooms[room]: 
                del rooms[room]
            else: 
                broadcast(room, f"📡 {nick} left.")
        del client_data[client]
    try: 
        client.close()
    except: 
        pass

def handle_client(client):
    """Continuous loop watching for incoming user chat frames."""
    while True:
        try:
            msg = client.recv(1024).decode('utf-8')
            if not msg: 
                break
            if client in client_data:
                nick, room = client_data[client]
                save_message(room, nick, msg)  # Fire and forget SQL record insertion
                broadcast(room, f"💬 {nick}: {msg}")
        except:
            break
    disconnect(client)

def receive():
    print(f"🚀 Discord-like Server running on port {PORT}. Ready for up to 50 users...")
    while True:
        client, addr = server.accept()
        try:
            # Entry Payload String Contract: "NICKNAME|ACTION|ROOM_CODE"
            payload = client.recv(1024).decode('utf-8')
            nick, action, target_room = payload.split('|')
            
            if action == "CREATE":
                room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                rooms[room_code] = [client]
                client_data[client] = (nick, room_code)
                client.send(f"CREATED|{room_code}".encode('utf-8'))
                print(f"🎯 Room {room_code} built by {nick}")
                
            elif action == "JOIN":
                room_code = target_room.upper().strip()
                if room_code in rooms:
                    rooms[room_code].append(client)
                    client_data[client] = (nick, room_code)
                    client.send(f"JOINED|{room_code}".encode('utf-8'))
                    
                    # Dump historical messages to sync UI display state
                    history = get_room_history(room_code)
                    for sender, content in history:
                        client.send(f"💬 {sender}: {content}".encode('utf-8'))
                        time.sleep(0.01) # Avoid frame buffering collisions
                        
                    broadcast(room_code, f"📡 {nick} joined!", skip_client=client)
                else:
                    client.send("ERROR|Code non-existent.".encode('utf-8'))
                    client.close()
                    continue
                    
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
        except:
            client.close()

if __name__ == "__main__":
    init_db()
    receive()
