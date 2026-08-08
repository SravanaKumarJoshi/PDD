import json
path = r'D:\Sravan\PDD\apppp\android\PolysaccharideProject\app_assets\master_dataset.json'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('"Approved FDA"', '"Recognized US"')
text = text.replace('"Approved EU"', '"Recognized EU"')
text = text.replace('"Approved"', '"Available"')
text = text.replace('"Prebiotic therapy"', '"Prebiotic supplement"')

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

path2 = r'D:\Sravan\PDD\apppp\android\PolysaccharideProject\scripts\download_datasets.py'
with open(path2, 'r', encoding='utf-8') as f:
    text2 = f.read()

text2 = text2.replace('"Prebiotic therapy"', '"Prebiotic supplement"')

with open(path2, 'w', encoding='utf-8') as f:
    f.write(text2)
