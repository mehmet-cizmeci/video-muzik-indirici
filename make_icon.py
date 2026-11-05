"""Uygulama simgesini (indirici.ico) üretir: mavi daire içinde aşağı ok."""
from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.ellipse((8, 8, S - 8, S - 8), fill=(229, 57, 53, 255))
w = (255, 255, 255, 255)
d.rectangle((108, 52, 148, 140), fill=w)                      # ok gövdesi
d.polygon([(64, 128), (192, 128), (128, 196)], fill=w)        # ok ucu
d.rounded_rectangle((64, 204, 192, 220), radius=8, fill=w)    # alt çizgi
img.save("indirici.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("indirici.ico oluşturuldu")
