from datetime import datetime
import json
from pynput.keyboard import Listener

def on_press(key):
    key_str = str(key).replace("'", "").replace('"', '')
    record = {
        'char': key_str,
        'eventType': 'keydown',
        'recordTimestamp': str(datetime.now())
    }
    try:
        json.loads(json.dumps(record))
    except json.JSONDecodeError:
        return
    with open('keystrokes.csv', 'a', buffering=1) as f:
        json.dump(record, f)
        f.write('\n')
        f.flush()

def on_release(key):
    key_str = str(key).replace("'", "").replace('"', '')
    record = {
        'char': key_str,
        'eventType': 'keyup',
        'recordTimestamp': str(datetime.now())
    }
    try:
        json.loads(json.dumps(record))
    except json.JSONDecodeError:
        return
    with open('keystrokes.csv', 'a', buffering=1) as f:
        json.dump(record, f)
        f.write('\n')
        f.flush()

def listen_to_typing():
    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
