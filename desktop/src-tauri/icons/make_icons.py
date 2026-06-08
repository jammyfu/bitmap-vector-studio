import struct
import zlib
import os

def png_chunk(chunk_type, data):
    chunk = chunk_type + data
    crc = zlib.crc32(chunk) & 0xffffffff
    return struct.pack('>I', len(data)) + chunk + struct.pack('>I', crc)

# IHDR: 1x1, 8-bit RGBA
ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)
ihdr = png_chunk(b'IHDR', ihdr_data)

# IDAT: compressed image data (filter byte 0 + RGBA pixel)
raw = bytes([0, 0, 0, 0, 0])  # filter + RGBA
compressed = zlib.compress(raw)
idat = png_chunk(b'IDAT', compressed)

# IEND
iend = png_chunk(b'IEND', b'')

png = b'\x89PNG\r\n\x1a\n' + ihdr + idat + iend

# ICO containing the PNG
ico_header = struct.pack('<HHH', 0, 1, 1)
dir_entry = struct.pack('<BBBBHHII', 1, 1, 0, 0, 1, 32, len(png), 22)
ico = ico_header + dir_entry + png

base = 'E:/Works/SelfProject/bitmap-vector-studio/desktop/src-tauri/icons'

with open(os.path.join(base, 'icon.ico'), 'wb') as f:
    f.write(ico)

for name in ['32x32.png', '128x128.png', '128x128@2x.png']:
    with open(os.path.join(base, name), 'wb') as f:
        f.write(png)

# For icon.icns, just write the PNG (tauri will handle it or we can replace later)
with open(os.path.join(base, 'icon.icns'), 'wb') as f:
    f.write(png)

print('Icons recreated with valid PNG')
