import json, sys

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    raw = f.read()

# Replace smart/curly quotes with straight quotes
LEFT = chr(0x201C)   # left double quotation mark
RIGHT = chr(0x201D)  # right double quotation mark
STRAIGHT = '"'
fixed = raw.replace(LEFT, STRAIGHT).replace(RIGHT, STRAIGHT)

with open(path, 'w', encoding='utf-8') as f:
    f.write(fixed)

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)
print("JSON fixed. Keys:", list(data.keys()))
