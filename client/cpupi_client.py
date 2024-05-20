"""
Client tool for the cpupi system.

Sends client info to the server for display.
"""
import toml
import psutil
import time
import websockets
import asyncio
import traceback
from math import floor


# Static info
hostname = None
cpu_count = None

def init(config):
    """
    Initialise static values from the config and system
    """
    global hostname
    global cpu_count

    hostname = config['hostname']
    cpu_count = psutil.cpu_count()

def make_stats():
    """
    Make the stats string to send to the server
    """
    mem = psutil.virtual_memory()
    load = psutil.getloadavg()
    days_up = floor(time.monotonic() / 86400)
    total_ram = mem.total / 1073741824

    return f'%{hostname}:{cpu_count}_{psutil.cpu_percent()}_{mem.percent}_{load[0]:.2f}_{load[1]:.2f}_{total_ram:.1f}#'

async def main(config):
    """
    Main method. Generates stats strings and sends them
    to the server.
    """

    uri = f'ws://{config["server"]}:{int(config["port"])}'
    async with websockets.connect(uri) as websocket:
        
        try:
            while True:
                stats = make_stats()
                if config['debug']:
                    print(f'Sending {stats}')
                await websocket.send(stats)
                await websocket.recv()
                time.sleep(1)
        except Exception:
            websocket.close()

if __name__ == "__main__":
    with open('config.toml') as c:
        config = toml.load(c)
    
    init(config)
    asyncio.run(main(config))