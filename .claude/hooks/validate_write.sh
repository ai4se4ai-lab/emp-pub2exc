#!/usr/bin/env bash
# .claude/hooks/validate_write.sh
# PreToolUse hook: prevents writing to protected paths.

TOOL_NAME="$1"
FILE_PATH="$2"

PROTECTED_PATTERNS=(
  "CLAUDE.md"
  ".claude/rules/"
  ".claude/skills/"
)

if [[ "$TOOL_NAME" == "Write" || "$TOOL_NAME" == "create_file" || "$TOOL_NAME" == "str_replace" ]]; then
  for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" == *"$pattern"* ]]; then
      echo "ERROR: Write to protected path blocked: $FILE_PATH" >&2
      exit 1
    fi
  done
fi

exit 0
