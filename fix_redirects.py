#!/usr/bin/env python3

# Script to fix incorrect redirect statements in views.py

with open('compliance/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the remaining incorrect redirect statements
content = content.replace("return redirect('dashboard')", "return redirect('compliance:dashboard_view')")

with open('compliance/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed all remaining redirect statements in views.py')
