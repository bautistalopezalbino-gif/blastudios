from PIL import Image

img = Image.open(r'C:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\Campaña kume\kume_fullpage.png')
h = img.height
chunk_h = h // 3
out = r'C:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\Campaña kume'

for i in range(3):
    top = i * chunk_h
    bottom = (i + 1) * chunk_h if i < 2 else h
    crop = img.crop((0, top, img.width, bottom))
    path = out + f'\\kume_chunk_{i}.png'
    crop.save(path, optimize=True)
    print(f'chunk_{i}: {top}px - {bottom}px, size: {crop.size}')

print('Listo.')
