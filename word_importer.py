import json

input_file = "lista palabras.txt"
output_file = "words.json"

words = []

with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Saltar cabecera
for line in lines[1:]:
    line = line.strip()

    if not line:
        continue

    parts = line.split("\t")

    if len(parts) < 3:
        continue

    _, english, spanish = parts[:3]

    # Limpiar inglés (quitar espacios internos rotos)
    english = english.replace(" ", "").lower()

    # Español se deja tal cual
    spanish = spanish.strip().lower()

    words.append({
        "english": english,
        "spanish": spanish
    })

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(words, f, indent=4, ensure_ascii=False)

print(f"✔ words.json creado correctamente con {len(words)} palabras")
