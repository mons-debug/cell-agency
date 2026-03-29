#!/bin/bash
# Cell Agency — Gateway Startup Script
# Sources environment variables and starts OpenClaw gateway

set -a  # Export all variables automatically
source /Users/mac/agency/.env
set +a

# Add pyenv to PATH
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"

echo "Starting Cell Agency Gateway..."
echo "OPENAI_API_KEY loaded: ${OPENAI_API_KEY:0:20}..."
echo "TELEGRAM_BOT_TOKEN loaded: ${TELEGRAM_BOT_TOKEN:0:20}..."

exec /usr/local/bin/openclaw gateway run
