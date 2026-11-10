"""Uygulama simgesini (indirici.ico + indirici.png) üretir: degrade yuvarlak kare, aşağı ok ve nota."""
from PIL import Image, ImageDraw

S = 1024                      # büyük çizip küçültmek kenarları yumuşatır
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

# degrade zemin (sol üst pembe-kırmızı -> sağ alt turuncu)
grad = Image.new("RGBA", (S, S))
gp = grad.load()
c1, c2 = (255, 65, 108), (255, 122, 69)
for y in range(S):
    for x in range(S):
        t = (x + y) / (2 * (S - 1))
        gp[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (255,)
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((40, 40, S - 40, S - 40), radius=230, fill=255)
img.paste(grad, (0, 0), mask)

d = ImageDraw.Draw(img)
w = (255, 255, 255, 255)
# aşağı ok
d.rounded_rectangle((452, 210, 572, 560), radius=40, fill=w)
d.polygon([(300, 500), (724, 500), (512, 720)], fill=w)
# alt çizgi (tepsi)
d.rounded_rectangle((300, 770, 724, 830), radius=30, fill=w)
# küçük nota (sağ üst)
d.ellipse((700, 300, 790, 380), fill=(255, 255, 255, 230))
d.rounded_rectangle((768, 170, 792, 345), radius=10, fill=(255, 255, 255, 230))
d.polygon([(780, 170), (860, 200), (860, 245), (780, 215)], fill=(255, 255, 255, 230))

img.resize((512, 512), Image.LANCZOS).save("indirici.png")
img.resize((256, 256), Image.LANCZOS).save(
    "indirici.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("indirici.ico ve indirici.png oluşturuldu")
