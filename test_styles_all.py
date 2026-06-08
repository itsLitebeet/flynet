import re
import os

for root, _, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                text = f.read()
                styles = set(re.findall(r'style="([^"]+)"', text)) | set(re.findall(r"style='([^']+)'", text))
                if styles:
                    print(f'{file}: {styles}')
