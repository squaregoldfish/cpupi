import toml
import threading
import time
import asyncio
import websockets
import re
import traceback
from datetime import datetime
from rpi_hardware_pwm import HardwarePWM
import board
import busio
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd
from num2words import num2words
import locale
from unidecode import unidecode


DEBUG = False
locale.setlocale(locale.LC_TIME, 'nl_NL.UTF8')

CLIENT_STATS = {}
CLIENT_ORDER = []

CPU_METER = None
MEM_METER = None
LCD = None

CURRENT_CLIENT = None

TIME_MODE_TIME = 0
TIME_MODE_DATE = 1

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
            if DEBUG:
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
    p = re.compile('^%(.*?):')
    return p.match(message).group(1)

def make_stats_object(message):
    obj = {}
    obj['timestamp'] = datetime.now()
    
    # Take the part after the : and split on _s
    values = message[message.index(':') + 1:-1].split('_')
    obj['cores'] = values[0]
    obj['cpu_percent'] = values[1]
    obj['mem_percent'] = values[2]
    obj['load1'] = values[3]
    obj['load5'] = values[4]
    obj['mem_total'] = values[5]
    
    return obj

def init(config):
    global DEBUG
    global CLIENT_ORDER
    global CPU_METER
    global MEM_METER
    global LCD

    DEBUG = config['debug']
    CLIENT_ORDER = config['client_order']

    CPU_METER = HardwarePWM(pwm_channel=0, hz=60, chip=0)
    CPU_METER.start(0)
    MEM_METER = HardwarePWM(pwm_channel=1, hz=60, chip=0)
    MEM_METER.start(0)

    i2c = busio.I2C(board.SCL, board.SDA)
    LCD = character_lcd.Character_LCD_RGB_I2C(i2c, 16, 2)

    #clear_display()

def get_year_percent(timestamp):
    # Start and end of the year
    start_of_year = datetime(timestamp.year, 1, 1)
    start_of_next_year = datetime(timestamp.year + 1, 1, 1)
    
    # Total seconds in the year
    total_seconds_in_year = (start_of_next_year - start_of_year).total_seconds()
    
    # Seconds passed since the start of the year
    seconds_passed = (timestamp - start_of_year).total_seconds()
    
    # Percentage of year passed
    percentage = (seconds_passed / total_seconds_in_year) * 100
    return percentage

def stats_display():
    global CURRENT_CLIENT

    last_time_mode = -1

    while True:
        chosen_client = None
        
        for ordered_client in CLIENT_ORDER:
            if ordered_client in CLIENT_STATS:
                chosen_client = ordered_client
                break

        if chosen_client is None and len(CLIENT_STATS) > 0:
            chosen_client = sorted(CLIENT_STATS.keys())[0]

        if chosen_client is None:
            CURRENT_CLIENT = None

            now = datetime.now()

            current_time_mode = TIME_MODE_TIME if now.second % 20 < 10 else TIME_MODE_DATE

            if current_time_mode != last_time_mode:
                # Meters - percent of day and percent of year            
                day_percent = (now.hour * 3600 + now.minute * 60 + now.second) / 86400 * 100
                set_meter_percent(CPU_METER, day_percent)
                set_meter_percent(MEM_METER, get_year_percent(now))

                if current_time_mode == TIME_MODE_TIME:
                    if now.hour == 0:
                        hour_word = 'Twaalf'
                    elif now.hour < 13:
                        hour_word = unidecode(num2words(now.hour, lang='nl')).capitalize()
                    else:
                        hour_word = unidecode(num2words(now.hour - 12, lang='nl')).capitalize()

                    hour_text = hour_word.center(16)
                    if now.hour < 12:
                        hour_text = '|' + hour_text[1:]
                    else:
                        hour_text = hour_text[:15] + '|'

                    if now.minute == 0:
                        minute_text = "uur"
                    elif now.minute < 10:
                        minute_text = f"uur {unidecode(num2words(now.minute, lang='nl'))}"
                    else:
                        minute_text = unidecode(num2words(now.minute, lang='nl'))

                    minute_text = minute_text.center(16)

                    LCD.cursor_position(0, 0)
                    LCD.message = hour_text
                    LCD.cursor_position(0, 1)
                    LCD.message = minute_text.center(16)
                else:
                    day_text = now.strftime("%A").ljust(16)
                    if now.day < 10:
                        day_text = day_text[:13] + str(now.day)
                    else:
                        day_text = day_text[:14] + str(now.day)

                    month_text = now.strftime("%B").ljust(16)
                    month_text = month_text[:12] + str(now.year)

                    LCD.cursor_position(0, 0)
                    LCD.message = day_text
                    LCD.cursor_position(0, 1)
                    LCD.message = month_text


                LCD.color = [100, 100, 100]
                last_time_mode = current_time_mode

        else:
            last_time_mode = -1
            stats = CLIENT_STATS[chosen_client]
            # Set the meters
            set_meter_percent(CPU_METER, stats['cpu_percent'])
            set_meter_percent(MEM_METER, stats['mem_percent'])

            if chosen_client != CURRENT_CLIENT:
                print(f'Connected client {chosen_client}')
                CURRENT_CLIENT = chosen_client
                LCD.clear()
                LCD.cursor_position(0, 0)
                LCD.message = f'{stats["cores"] + "#": >16}'
                LCD.cursor_position(0, 0)
                LCD.message = chosen_client
                LCD.cursor_position(0, 1)

            # We only update the LCD stats every 5 seconds
            if datetime.now().second % 5 == 0:
                load_string_1 = '**.**' if float(stats['load1']) > 100 else stats['load1']
                load_string_5 = '**.**' if float(stats['load5']) > 100 else stats['load5']
                
                mem_total = float(stats["mem_total"])
                if mem_total > 10:
                    mem_string = f'{mem_total:.0f}G'
                else:
                    mem_string = f'{mem_total:.1f}G'

                component_length = len(load_string_1) + len(load_string_5) + len(mem_string) + 2
                pad = 16 - component_length
                
                bottom_message = f'{load_string_1} {load_string_5} '
                for i in range(0, pad):
                    bottom_message += ' '
                
                bottom_message += mem_string

                load_percent = int(float(stats['load1']) / float(stats['cores']) * 100)
                color = [0, 0, 0]
                if load_percent >= 100:
                    color = [100, 0, 0]
                elif load_percent >= 66:
                    color = [100, 100, 0]
                elif load_percent >= 33:
                    color = [0, 100, 0]
                else:
                    color = [100, 100, 100]

                # We used to have blue below 20%, but it doesn't display well

                LCD.color = color
                LCD.cursor_position(0, 1)
                LCD.message = bottom_message

        time.sleep(1)

def clear_display():
    set_meter_percent(CPU_METER, 0)
    set_meter_percent(MEM_METER, 0)
    LCD.clear()
    LCD.color = [0, 0, 0]

def set_meter_percent(meter, percent):
    meter_value = float(percent)
    if meter_value < 0:
        meter_value = 0
    elif meter_value > 100:
        meter_value = 100

    meter.change_duty_cycle(meter_value)

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
