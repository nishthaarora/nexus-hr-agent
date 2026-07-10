#!/bin/bash
set -a
source /Users/appfire-nishthaarora/Documents/code/docs/.env
set +a

exec /Users/appfire-nishthaarora/Documents/code/docs/.venv/bin/python3 \
  /Users/appfire-nishthaarora/Documents/code/docs/nexus-hr-agent/backend/mcp_server.py
