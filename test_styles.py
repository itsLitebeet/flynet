import re
with open('app/keyboards.py', 'r', encoding='utf-8') as f:
    text = f.read()
styles = set(re.findall(r'style="([^"]+)"', text)) | set(re.findall(r"style='([^']+)'", text))
print("Styles found:", styles)
