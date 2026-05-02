import argparse
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
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
}

for c in 'abcdefghijklmnopqrstuvwxyz0123456789':
    VK[c] = ord(c.upper())


def get_pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def set_pos(x, y):
    user32.SetCursorPos(int(x), int(y))


def mouse_event(flags, data=0):
    user32.mouse_event(flags, 0, 0, data, 0)


def click(button='left'):
    if button == 'left':
        mouse_event(MOUSEEVENTF_LEFTDOWN)
        mouse_event(MOUSEEVENTF_LEFTUP)
    elif button == 'right':
        mouse_event(MOUSEEVENTF_RIGHTDOWN)
        mouse_event(MOUSEEVENTF_RIGHTUP)


def drag_to(x, y, steps=12, delay=0.01):
    sx, sy = get_pos()
    mouse_event(MOUSEEVENTF_LEFTDOWN)
    try:
        for i in range(1, steps + 1):
            nx = sx + (x - sx) * i / steps
            ny = sy + (y - sy) * i / steps
            set_pos(int(nx), int(ny))
            time.sleep(delay)
    finally:
        mouse_event(MOUSEEVENTF_LEFTUP)


def scroll(amount):
    mouse_event(MOUSEEVENTF_WHEEL, int(amount))


def key_down(vk):
    user32.keybd_event(vk, 0, 0, 0)


def key_up(vk):
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def send_hotkey(keys):
    codes = [VK[k.lower()] for k in keys]
    for code in codes:
        key_down(code)
        time.sleep(0.03)
    for code in reversed(codes):
        key_up(code)
        time.sleep(0.03)


def type_text(text):
    for ch in text:
        user32.SendMessageW(user32.GetForegroundWindow(), 0x0102, ord(ch), 0)
        time.sleep(0.01)


def send_key(key):
    code = VK[key.lower()]
    key_down(code)
    time.sleep(0.03)
    key_up(code)
    time.sleep(0.03)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)

    sub.add_parser('pos')

    p_move = sub.add_parser('move')
    p_move.add_argument('--x', type=int, required=True)
    p_move.add_argument('--y', type=int, required=True)

    p_move_rel = sub.add_parser('move-rel')
    p_move_rel.add_argument('--dx', type=int, required=True)
    p_move_rel.add_argument('--dy', type=int, required=True)

    sub.add_parser('click')
    sub.add_parser('double-click')
    sub.add_parser('right-click')

    p_drag = sub.add_parser('drag')
    p_drag.add_argument('--x', type=int, required=True)
    p_drag.add_argument('--y', type=int, required=True)
    p_drag.add_argument('--steps', type=int, default=12)

    p_scroll = sub.add_parser('scroll')
    p_scroll.add_argument('--amount', type=int, required=True)

    p_move_click = sub.add_parser('move-click')
    p_move_click.add_argument('--x', type=int, required=True)
    p_move_click.add_argument('--y', type=int, required=True)
    p_move_click.add_argument('--delay', type=float, default=0.1)

    p_delay = sub.add_parser('delay-click')
    p_delay.add_argument('--seconds', type=float, required=True)

    p_type = sub.add_parser('type')
    p_type.add_argument('--text', required=True)

    p_hotkey = sub.add_parser('hotkey')
    p_hotkey.add_argument('--keys', required=True)

    p_key = sub.add_parser('key')
    p_key.add_argument('--name', required=True)

    args = parser.parse_args()

    if args.action == 'pos':
        x, y = get_pos()
        print(f'{x},{y}')
    elif args.action == 'move':
        set_pos(args.x, args.y)
        print(f'moved:{args.x},{args.y}')
    elif args.action == 'move-rel':
        x, y = get_pos()
        nx, ny = x + args.dx, y + args.dy
        set_pos(nx, ny)
        print(f'moved:{nx},{ny}')
    elif args.action == 'click':
        click('left')
        print('clicked:left')
    elif args.action == 'double-click':
        click('left')
        time.sleep(0.08)
        click('left')
        print('clicked:double')
    elif args.action == 'right-click':
        click('right')
        print('clicked:right')
    elif args.action == 'drag':
        drag_to(args.x, args.y, steps=args.steps)
        print(f'dragged:{args.x},{args.y}')
    elif args.action == 'scroll':
        scroll(args.amount)
        print(f'scrolled:{args.amount}')
    elif args.action == 'move-click':
        set_pos(args.x, args.y)
        time.sleep(args.delay)
        click('left')
        print(f'move-clicked:{args.x},{args.y}')
    elif args.action == 'delay-click':
        time.sleep(args.seconds)
        click('left')
        print(f'delay-clicked:{args.seconds}')
    elif args.action == 'type':
        type_text(args.text)
        print('typed')
    elif args.action == 'hotkey':
        send_hotkey([k.strip() for k in args.keys.split(',') if k.strip()])
        print('hotkey-sent')
    elif args.action == 'key':
        send_key(args.name)
        print(f'key-sent:{args.name}')


if __name__ == '__main__':
    main()
