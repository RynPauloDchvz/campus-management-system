import os
import re

directory = r"e:\Users\rynwl\Desktop\campus-management-system\templates\admin_dashboard"

for filename in os.listdir(directory):
    if not filename.endswith(".html"):
        continue

    filepath = os.path.join(directory, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove skeleton loader block entirely
    # We find <!-- 🟢 SKELETON LOADING STATE 🟢 -->
    # and we remove it, along with everything until <!-- 🟢 ACTUAL CONTENT
    # Regex explanation: match from <!-- 🟢 SKELETON LOADING STATE 🟢 --> up to but not including <!-- 🟢 ACTUAL CONTENT
    pattern_skeleton = r"([ \t]*<!-- 🟢 SKELETON LOADING STATE 🟢 -->.*?)(?=[ \t]*<!-- 🟢 ACTUAL CONTENT)"
    content = re.sub(pattern_skeleton, "", content, flags=re.DOTALL)

    # 2. Remove style="display: none;" from main-content-area
    content = re.sub(r'(<div\s+id="main-content-area"\s+)style="display:\s*none;?"\s*', r'\1', content)
    content = re.sub(r'(<div\s+id="main-content-area"\s+class="[^"]*"\s+)style="display:\s*none;?"', r'\1', content)
    
    # Let's also just try to replace: id="main-content-area" style="display: none;" class="fade-in"
    # with id="main-content-area" class="fade-in"
    content = content.replace('id="main-content-area" style="display: none;" class="fade-in"', 'id="main-content-area" class="fade-in"')

    # 3. Remove JS lines
    content = re.sub(r"[ \t]*document\.getElementById\('skeleton-loader'\)\.style\.display\s*=\s*'none';\n?", "", content)
    content = re.sub(r"[ \t]*document\.getElementById\('main-content-area'\)\.style\.display\s*=\s*'block';\n?", "", content)
    content = re.sub(r"[ \t]*const loader = document\.getElementById\('skeleton-loader'\);\n?", "", content)
    content = re.sub(r"[ \t]*const content = document\.getElementById\('main-content-area'\);\n?", "", content)
    content = re.sub(r"[ \t]*if\s*\(loader\)\s*loader\.style\.display\s*=\s*'none';\n?", "", content)
    content = re.sub(r"[ \t]*if\s*\(content\)\s*content\.style\.display\s*=\s*'block';\n?", "", content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done removing skeletons.")
