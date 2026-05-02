import argparse
import ctypes
import time

user32 = ctypes.windll.user32
KEYEVENTF_KEYUP = 0x0002

VK = {
    'ctrl': 0x11,
    'shift': 0x10,
    'alt': 0x12,
    'win': 0x5B,
    'enter': 0x0D,
    'esc': 0x1B,
    'tab': 0x09,
    'space': 0x20,
    'backspace': 0x08,
    'delete': 0x2E,
    'up': 0x26,
    'down': 0x28,
    'left': 0x25,
    'right': 0x27,
    'home': 0x24,
    'end': 0x23,
}

for c in 'abcdefghijklmnopqrstuvwxyz0123456789':
    VK[c] = ord(c.upper())


def key_down(vk):
    user32.keybd_event(vk, 0, 0, 0)


def key_up(vk):
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def send_key(name):
    code = VK[name.lower()]
    key_down(code)
    time.sleep(0.03)
    key_up(code)
    time.sleep(0.03)


def send_hotkey(keys):
    codes = [VK[k.lower()] for k in keys]
    for code in codes:
        key_down(code)
        time.sleep(0.03)
    for code in reversed(codes):
        key_up(code)
        time.sleep(0.03)


def type_text(text):
    hwnd = user32.GetForegroundWindow()
    for ch in text:
        user32.SendMessageW(hwnd, 0x0102, ord(ch), 0)
        time.sleep(0.01)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)

    p_type = sub.add_parser('type')
    p_type.add_argument('--text', required=True)

    p_key = sub.add_parser('key')
    p_key.add_argument('--name', required=True)

    p_hotkey = sub.add_parser('hotkey')
    p_hotkey.add_argument('--keys', required=True)

    args = parser.parse_args()

    if args.action == 'type':
        type_text(args.text)
        print('typed')
    elif args.action == 'key':
        send_key(args.name)
        print(f'key-sent:{args.name}')
    elif args.action == 'hotkey':
        send_hotkey([k.strip() for k in args.keys.split(',') if k.strip()])
        print('hotkey-sent')


if __name__ == '__main__':
    main()
