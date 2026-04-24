#!/usr/bin/env bash
# .claude/hooks/log_tool_use.sh
# PostToolUse hook: logs every tool invocation to .comms/tool_log.jsonl

TOOL_NAME="$1"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_DIR=".comms"
LOG_FILE="$LOG_DIR/tool_log.jsonl"

mkdir -p "$LOG_DIR"
echo "{\"timestamp\": \"$TIMESTAMP\", \"tool\": \"$TOOL_NAME\"}" >> "$LOG_FILE"
exit 0
