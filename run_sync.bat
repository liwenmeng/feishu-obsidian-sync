@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "d:\vscode-projects\feishu-obsidian-sync"
"d:\vscode-projects\feishu-obsidian-sync\venv\Scripts\python.exe" main.py >> "d:\vscode-projects\feishu-obsidian-sync\sync.log" 2>&1
