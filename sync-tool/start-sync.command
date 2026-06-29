#!/bin/bash
# Double-click this file to start the Card Notes & Pay sync server.
# (macOS opens it in Terminal; the server logs appear there. Close the window to stop.)
cd "$(dirname "$0")"
clear
echo "╭───────────────────────────────────────────────╮"
echo "│   Card Notes & Pay — sync server starting…    │"
echo "╰───────────────────────────────────────────────╯"
exec python3 sync_server.py
