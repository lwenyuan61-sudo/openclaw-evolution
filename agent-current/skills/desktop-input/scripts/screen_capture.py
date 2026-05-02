import sys
from pathlib import Path
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]


def save_bmp(path: Path, width: int, height: int, data: bytes):
    row_padded = (width * 3 + 3) & ~3
    pixel_bytes = bytearray()
    for y in range(height):
        start = y * width * 4
        row = bytearray()
        for x in range(width):
            i = start + x * 4
            b, g, r, _ = data[i:i+4]
            row.extend([b, g, r])
        while len(row) < row_padded:
            row.append(0)
        pixel_bytes.extend(row)
    filesize = 14 + 40 + len(pixel_bytes)
    with open(path, 'wb') as f:
        f.write(b'BM')
        f.write(filesize.to_bytes(4, 'little'))
        f.write((0).to_bytes(4, 'little'))
        f.write((54).to_bytes(4, 'little'))
        f.write((40).to_bytes(4, 'little'))
        f.write(width.to_bytes(4, 'little', signed=True))
        f.write((-height).to_bytes(4, 'little', signed=True))
        f.write((1).to_bytes(2, 'little'))
        f.write((24).to_bytes(2, 'little'))
        f.write((0).to_bytes(4, 'little'))
        f.write(len(pixel_bytes).to_bytes(4, 'little'))
        f.write((0).to_bytes(16, 'little'))
        f.write(pixel_bytes)


def capture(path_str: str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbm = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    gdi32.SelectObject(hdc_mem, hbm)
    gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, 0, 0, SRCCOPY)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB
    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(hdc_mem, hbm, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS)
    save_bmp(path, width, height, buffer.raw)
    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)
    print(str(path))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python screen_capture.py <output-path>')
        raise SystemExit(2)
    capture(sys.argv[1])
