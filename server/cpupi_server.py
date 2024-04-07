import toml
import threading
import time
import asyncio
import websockets
import re
import traceback
from datetime import datetime

CLIENT_STATS = {}

async def main(config):
    # Start the display thread
    display_thread = threading.Thread(target=stats_display)
    display_thread.daemon = True
    display_thread.start()

    # Start the cleanup thread
    cleanup_thread = threading.Thread(target=cleanup, args=(int(config['client_timeout']),))
    cleanup_thread.daemon = True
    cleanup_thread.start()

    # Now start the server to receive stats messages
    try:
        print(f'Starting server on port {config["port"]}')
        async with websockets.serve(receive_client, '', int(config['port'])):
            await asyncio.Future()  # run forever
    except Exception:
        print('*** ERROR IN SERVER')
        print(traceback.format_exc())


async def receive_client(websocket):
    global CLIENT_STATS

    try:
        while True:
            message = await websocket.recv()
            print(message)
            hostname = get_hostname(message)
            CLIENT_STATS[hostname] = make_stats_object(message)
            
            # Send a response so the connection stays alive
            await websocket.send('')
    except websockets.exceptions.ConnectionClosedOK:
        pass
    except Exception as e:
        print('*** ERROR IN CLIENT HANDLER')
        print(e)
        print('---------')
        print(traceback.format_exc())

def get_hostname(message):
    p = re.compile('^%(.*):')
    return p.match(message).group(1)

def make_stats_object(message):
    obj = {}
    obj['timestamp'] = datetime.now()
    
    # Take the part after the : and split on _s
    values = message[message.index(':') + 1:-1].split('_')
    obj['cores'] = values[0]
    obj['cpu%'] = values[1]
    obj['mem%'] = values[2]
    return obj

def init(config):
    print('Processing config')

def stats_display():
    while True:
        print(CLIENT_STATS)
        time.sleep(2)

def cleanup(timeout):
    global CLIENT_STATS

    while True:
        to_delete = []
        for client in CLIENT_STATS:
            age = datetime.now() - CLIENT_STATS[client]['timestamp']
            if age.total_seconds() > timeout:
                to_delete.append(client)

        for client in to_delete:
            print(f'Deleting client {client}')
            del CLIENT_STATS[client]

        time.sleep(1)


if __name__ == "__main__":
    with open('config.toml') as c:
        config = toml.load(c)
    
    init(config)
    asyncio.run(main(config))