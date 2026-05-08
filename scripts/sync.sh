#!/bin/bash
# buc-skills sync script
# Sourceable library - functions available when sourced, execution only when run directly

# Global flags (set by sync_skill_main orchestration)
FORCE=0

log() {
    local level="$1"
    shift
    echo "[$level] $*" >&2
}

help() {
    echo "Usage: sync.sh <COMMAND> [OPTIONS] "
    echo ""
    echo "Commands:"
    echo "  skills    Sync skills from the server (default when script is run directly)"
    echo "  help      Show this help message"
    echo ""
    echo "Options:"
    echo "  --force   Overwrite existing files without showing diff"
    echo "  -h, --help  Show this help message"
    echo ""
    echo "Examples:"
    echo "  curl https://server/sync.sh | bash -s skills"
    echo "  curl https://server/sync.sh | bash -s skills --force "
    echo "  curl https://server/sync.sh | bash -s help"
}

detect_agent() {
    if [[ -d ".claude/skills" ]]; then
        CLIENT_AGENT="claude"
    elif [[ ! -d ".agents/skills" ]]; then
        CLIENT_AGENT="opencode"
    else
        CLIENT_AGENT="opencode"
        log "warn" "No known agent directory found, defaulting to opencode"
    fi
}

resolve_skills_dir() {
    case "$CLIENT_AGENT" in
        opencode)
            echo ".agents/skills"
            ;;
        claude)
            echo ".claude/skills"
            ;;
    esac
}

fetch_skill_list() {
    local response
    response=$(curl -s -X POST "$SERVER_URL/buc-skills/mcp" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"resources/list","params":{}}')

    echo "$response" | jq -r '.result.resources[] | .uri | ltrimstr("skill://") | split("/")[0]' | sort -u
}

select_skills() {
    local skills
    if [[ $# -gt 0 ]]; then
        skills="$*"
    elif [[ ! -t 0 ]]; then
        skills=$(cat)
    else
        log "error" "No skills provided (no arguments or stdin)"
        return 1
    fi

    if [[ -z "$skills" ]]; then
        log "error" "No skills provided"
        return 1
    fi

    if command -v fzf >/dev/null 2>&1; then
        echo "$skills" | fzf --multi | sort
    else
        local -a skill_array
        readarray -t skill_array <<< "$skills"
        local i=1
        for skill in "${skill_array[@]}"; do
            echo "$i) $skill"
            ((i++))
        done
        echo ""
        echo "Enter skill number(s) separated by commas (e.g., 1,3):"
        read -r selection
        local -a selected
        IFS=',' read -ra selected <<< "$selection"
        for num in "${selected[@]}"; do
            num=$(echo "$num" | tr -d ' ')
            if [[ "$num" -ge 1 ]] && [[ "$num" -le "${#skill_array[@]}" ]]; then
                echo "${skill_array[$((num - 1))]}"
            fi
        done | sort
    fi
}

sync_file() {
    local resource_uri="$1"
    local local_path="$2"

    local response
    response=$(curl -s -X POST "$SERVER_URL/buc-skills/mcp" \
        -H "Content-Type: application/json" \
        -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"resources/read\",\"params\":{\"uri\":\"$resource_uri\"}}")

    local remote_content
    remote_content=$(echo "$response" | jq -r '.result.content // empty')

    if [[ -f "$local_path" ]] && [[ "$FORCE" -eq 0 ]]; then
        local diff_output
        diff_output=$(diff "$local_path" <(echo "$remote_content") 2>&1) || true
        if [[ -n "$diff_output" ]]; then
            echo "=== $local_path differs ==="
            echo "$diff_output"
            log "warn" "File differs. Re-run with --force to overwrite"
            return 0
        else
            echo "$local_path is up to date"
            return 0
        fi
    fi

    if [[ "$FORCE" -eq 1 ]]; then
        echo "[force] Writing $local_path"
    else
        echo "Writing new file $local_path"
    fi

    write_file "$local_path" "$remote_content"
}

write_file() {
    local file_path="$1"
    local content="$2"
    mkdir -p "$(dirname "$file_path")"
    echo "$content" > "$file_path"
}

fetch_skill_resources() {
    local skill_name="$1"
    local response
    response=$(curl -s -X POST "$SERVER_URL/buc-skills/mcp" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"resources/list","params":{}}')

    echo "$response" | jq -r ".result.resources[] | select(.uri | startswith(\"skill://$skill_name/\")) | .uri"
}

sync_skill_main() {
    local args=("$@")

    for arg in "${args[@]}"; do
        case "$arg" in
            --force) FORCE=1 ;;
        esac
    done

    echo "Detecting agent..."
    detect_agent
    echo "Detected agent: $CLIENT_AGENT"

    local agent_skills_dir
    agent_skills_dir=$(resolve_skills_dir)
    echo "Skills directory: $agent_skills_dir"

    echo "Fetching available skills..."
    local skill_list
    skill_list=$(fetch_skill_list)
    if [[ -z "$skill_list" ]]; then
        echo "Error: No skills found"
        exit 1
    fi
    echo "Available skills:"
    echo "$skill_list"

    echo "Selecting skills..."
    local selected
    selected=$(echo "$skill_list" | select_skills)
    if [[ -z "$selected" ]]; then
        echo "Error: No skills selected"
        exit 1
    fi
    echo "Selected skills:"
    echo "$selected"

    echo "Syncing skills to $agent_skills_dir..."
    while IFS= read -r skill_name; do
        [[ -z "$skill_name" ]] && continue
        echo ""
        echo "=== Syncing skill: $skill_name ==="

        local skill_dir="$agent_skills_dir/$skill_name"

        local resources
        resources=$(fetch_skill_resources "$skill_name")

        while IFS= read -r resource_uri; do
            [[ -z "$resource_uri" ]] && continue

            local relative_path
            relative_path=$(echo "$resource_uri" | ltrimstr "skill://")

            local local_path
            if [[ "$relative_path" == "SKILL.md" ]]; then
                local_path="$skill_dir/SKILL.md"
            else
                local_path="$skill_dir/resources/$relative_path"
            fi

            sync_file "$resource_uri" "$local_path"
        done <<< "$resources"
    done <<< "$selected"

    echo ""
    echo "Sync complete!"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then


    case "${1:-}" in
        --help|-h)
            help
            exit 0
            ;;
        help)
            help
            exit 0
            ;;
        skills)
            sync_skill_main "$@"
            ;;
        "")
            help
            exit 0
            ;;
        *)
            echo "Unknown command: $1" >&2
            help
            exit 1
            ;;
    esac
fi
