# Default SERVER_URL (overridden by /sync.sh endpoint via Host header injection)
SERVER_URL="${SERVER_URL:-http://localhost:8000}"
# Normalize: strip trailing slash, default to http:// if no scheme
SERVER_URL="${SERVER_URL%/}"
case "$SERVER_URL" in
    http://*|https://*) ;;
    *) SERVER_URL="http://$SERVER_URL" ;;
esac

CLIENT_AGENT=""
MCP_SESSION_ID=""

help() {
    cat <<'HELP'
Usage: sync.sh

Sync AI Code-Agent configs from server

Requires: curl, jq
Optional: fzf (for fuzzy selection)
HELP
}

detect_agent() {
    if [[ -d ".claude" ]]; then
        CLIENT_AGENT="claude"
    elif [[ ! -d ".agents" ]]; then
        CLIENT_AGENT="opencode"
    else
        CLIENT_AGENT="opencode"
        log "warn" "No known agent directory found, defaulting to opencode"
    fi
}

resolve_path() {
    local kind="$1"
    case "$CLIENT_AGENT" in
        claude)
            case "$kind" in
                skills) echo ".claude/skills" ;;
                config) echo ".claude/mcp.json" ;;
            esac
            ;;
        *)
            case "$kind" in
                skills) echo ".agents/skills" ;;
                config) echo ".agents/opencode.json" ;;
            esac
            ;;
    esac
}

resolve_mcp_config_key() {
    [[ "$CLIENT_AGENT" == "claude" ]] && echo "mcpServers" || echo "mcp"
}

session_init() {
    MCP_SESSION_ID=""

    local raw
    raw=$(curl -s -i -X POST "$SERVER_URL/buc-skills/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -D - \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"sync","version":"1.0"}}}' 2>/dev/null)
    [[ -z "$raw" ]] && return 1

    MCP_SESSION_ID=$(echo "$raw" | grep -i 'mcp-session-id' | head -1 | awk '{print $2}' | tr -d '\r\n')
    [[ -z "$MCP_SESSION_ID" ]] && return 1

    curl -s -X POST "$SERVER_URL/buc-skills/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -H "Mcp-Session-Id: $MCP_SESSION_ID" \
        -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null 2>&1 || true
    return 0
}

prompt() {
    local title="$1"; shift
    local -a keys=() vals=() labels=()
    for arg in "$@"; do
        keys+=("${arg%%:*}")
        vals+=("${arg#*:}")
        labels+=("$arg")
    done

    while true; do
        if command -v fzf >/dev/null 2>&1; then
            local chosen
            chosen=$(printf "%s\n" "${labels[@]}" | fzf --select-1 --exact)
            [[ -z "$chosen" ]] && continue
            local i
            for i in "${!labels[@]}"; do
                if [[ "${labels[$i]}" == "${chosen%%(*}"* ]]; then
                    echo "${keys[$i]}"
                    return 0
                fi
            done
            continue
        else
            echo "$title:" >&2
            for i in "${!keys[@]}"; do
                echo "$((i+1))) ${labels[$i]}" >&2
            done
            printf "Enter choice: " >&2
            read -r num
            if [[ "$num" =~ ^[0-9]+$ ]] && (( num >= 1 && num <= ${#keys[@]} )); then
                echo "${keys[$((num-1))]}"
                return 0
            fi
            echo "Invalid. Try again." >&2
        fi
    done
}

select_skills() {
    local items
    if [[ $# -gt 0 ]]; then
        items=$(printf "%s\n" "$@")
    else
        items=$(cat)
    fi
    if [[ -z "$items" ]]; then
        return 1
    fi
    if command -v fzf >/dev/null 2>&1; then
        echo "$items" | fzf --multi --exact
    else
        local -a names
        mapfile -t names <<< "$items"
        local -a selected=()
        local -a nums
        echo "Available items:" >&2
        for i in "${!names[@]}"; do
            echo "$((i+1))) ${names[$i]}" >&2
        done
        while true; do
            printf "Enter numbers separated by spaces (or 0 to finish): " >&2
            read -r -a nums
            [[ ${#nums[@]} -eq 0 ]] && continue
            for n in "${nums[@]}"; do
                if [[ "$n" == "0" ]]; then
                    [[ ${#selected[@]} -gt 0 ]] && break 2 || { echo "No items selected." >&2; continue 2; }
                fi
                if [[ "$n" =~ ^[0-9]+$ ]] && [[ "$n" -ge 1 ]] && [[ "$n" -le "${#names[@]}" ]]; then
                    selected+=("${names[$((n-1))]}")
                fi
            done
            [[ ${#selected[@]} -gt 0 ]] && break
            echo "Invalid selection. Try again." >&2
        done
        printf "%s\n" "${selected[@]}"
    fi
}

prompt_yes_no() {
    local message="$1"
    local answer
    while true; do
        printf "%s (y/n): " "$message" >&2
        read -r answer
        case "${answer,,}" in
            y|yes) echo "y"; return 0 ;;
            n|no) echo "n"; return 0 ;;
            *) echo "Invalid. Enter y or n." >&2 ;;
        esac
    done
}

log() {
    local level="$1"
    local message="$2"
    echo "[$level] $message" >&2
}

_extract_json() {
    echo "$1" | sed -n 's/^data: //p' | head -1 | tr -d '\r'
}

_mcp_post() {
    local json_payload="$1"
    curl -s -X POST "$SERVER_URL/buc-skills/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        ${MCP_SESSION_ID:+-H "Mcp-Session-Id: $MCP_SESSION_ID"} \
        -d "$json_payload" 2>/dev/null
}

fetch_skill_list() {
    local response
    response=$(_mcp_post '{"jsonrpc":"2.0","id":1,"method":"resources/list","params":{}}')
    local json
    json=$(_extract_json "$response")
    [[ -z "$json" ]] && return 1
    echo "$json" | jq -r '.result.resources[]? | .uri' | while IFS= read -r uri; do
        [[ -n "$uri" ]] && echo "${uri#skill://}" | cut -d/ -f1
    done | sort -u
}

fetch_skill_resources() {
    local skill_name="$1"
    local response
    response=$(_mcp_post '{"jsonrpc":"2.0","id":1,"method":"resources/list","params":{}}')
    local json
    json=$(_extract_json "$response")
    [[ -z "$json" ]] && return 1
    echo "$json" | jq -r ".result.resources[]? | select(.uri | startswith(\"skill://$skill_name/\")) | .uri"
}

read_resource_content() {
    local resource_uri="$1"
    local response
    response=$(_mcp_post "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"resources/read\",\"params\":{\"uri\":\"$resource_uri\"}}")
    local json
    json=$(_extract_json "$response")
    [[ -z "$json" ]] && return 1
    echo "$json" | jq -r '.result.contents[0].text // .result.content // empty'
}

write_file() {
    local path="$1"
    local content="$2"
    mkdir -p "$(dirname "$path")"
    printf '%s\n' "$content" > "$path"
}

sync_file() {
    local resource_uri="$1"
    local local_path="$2"
    local conflict="$3"

    local remote_content
    remote_content=$(read_resource_content "$resource_uri")
    if [[ -z "$remote_content" ]]; then
        log "error" "Failed to read resource: $resource_uri"
        return 1
    fi

    if [[ ! -f "$local_path" ]]; then
        case "$conflict" in
            dry-run)
                echo "=== New file: $local_path ==="
                ;;
            *)
                echo "Writing new file: $local_path"
                write_file "$local_path" "$remote_content"
                ;;
        esac
        return 0
    fi

    local local_content
    local_content=$(cat "$local_path")
    if [[ "$local_content" == "$remote_content" ]]; then
        echo "Identical: $local_path"
        return 0
    fi

    case "$conflict" in
        sync)
            echo "=== $local_path differs (skipping) ==="
            log "warn" "File differs. Skipping to avoid overwriting local changes."
            ;;
        dry-run)
            echo "=== $local_path would differ ==="
            diff "$local_path" <(echo "$remote_content") 2>&1 || true
            ;;
        force)
            echo "[force] Writing $local_path"
            write_file "$local_path" "$remote_content"
            ;;
    esac
}

merge_configs() {
    local template_json="$1"
    local selected_servers="$2"
    local existing_config_path="$3"

    local key_name
    key_name=$(resolve_mcp_config_key)

    local merged
    if [[ -f "$existing_config_path" ]]; then
        merged=$(cat "$existing_config_path")
    else
        merged='{}'
    fi

    local server_name server_json
    while IFS= read -r server_name; do
        [[ -z "$server_name" ]] && continue
        server_json=$(echo "$template_json" | jq -c ".${key_name}[\"$server_name\"]")
        if [[ -n "$server_json" && "$server_json" != "null" ]]; then
            merged=$(echo "$merged" | jq -c --arg name "$server_name" --argjson val "$server_json" ".${key_name}[\$name] = \$val")
        fi
    done <<< "$selected_servers"

    echo "$merged"
}

merge_and_write() {
    local template_json="$1"
    local selected_servers="$2"
    local config_file="$3"

    local merged
    merged=$(merge_configs "$template_json" "$selected_servers" "$config_file")

    mkdir -p "$(dirname "$config_file")"
    echo "$merged" | jq '.' > "$config_file"
}

sync_skill_main() {
    local conflict
    conflict=$(prompt "Choose conflict resolution" \
        "sync:sync (skip differing)" \
        "dry-run:dry-run (preview only)" \
        "force:force (overwrite)")
    session_init
    if [[ -z "$MCP_SESSION_ID" ]]; then
        log "error" "Failed to initialize MCP session"
        exit 1
    fi
    echo "Session established."

    echo "Detecting agent..."
    detect_agent
    echo "Detected agent: $CLIENT_AGENT"

    local agent_skills_dir
    agent_skills_dir=$(resolve_path skills)
    echo "Skills directory: $agent_skills_dir"

    echo "Fetching available skills..."
    local skill_list
    skill_list=$(fetch_skill_list)
    if [[ -z "$skill_list" ]]; then
        log "error" "No skills found"
        exit 1
    fi
    echo "Available skills:"
    echo "$skill_list"

    echo "Selecting skills..."
    local selected
    selected=$(echo "$skill_list" | select_skills)
    if [[ -z "$selected" ]]; then
        log "error" "No skills selected"
        exit 1
    fi
    echo "Selected skills:"
    echo "$selected"

    echo "Syncing skills to $agent_skills_dir..."
    local skill_name skill_dir resources resource_uri relative_path local_path
    while IFS= read -r skill_name; do
        [[ -z "$skill_name" ]] && continue
        echo ""
        echo "=== Syncing skill: $skill_name ==="

        skill_dir="$agent_skills_dir/$skill_name"
        resources=$(fetch_skill_resources "$skill_name")

        while IFS= read -r resource_uri; do
            [[ -z "$resource_uri" ]] && continue

            relative_path="${resource_uri#skill://}"
            if [[ "$relative_path" == "$skill_name/SKILL.md" ]]; then
                local_path="$skill_dir/SKILL.md"
            else
                local_path="$skill_dir/${relative_path}"
            fi

            sync_file "$resource_uri" "$local_path" "$conflict"
        done <<< "$resources"
    done <<< "$selected"

    echo ""
    echo "Sync complete!"
}

sync_mcp_main() {
    local conflict
    conflict=$(prompt "Choose conflict resolution" \
        "sync:sync (skip differing)" \
        "dry-run:dry-run (preview only)" \
        "force:force (overwrite)")

    echo "Detecting agent..."
    detect_agent
    echo "Detected agent: $CLIENT_AGENT"

    local config_file
    config_file=$(resolve_path config)
    echo "Config file: $config_file"

    echo "Fetching MCP server list from server..."
    local config_json
    config_json=$(curl -s "$SERVER_URL/mcps.json?agent=$CLIENT_AGENT")
    if [[ -z "$config_json" ]]; then
        log "error" "Failed to fetch MCP config"
        exit 1
    fi

    local key_name
    key_name=$(resolve_mcp_config_key)

    local server_names
    server_names=$(echo "$config_json" | jq -r ".${key_name} | keys[]")
    if [[ -z "$server_names" ]]; then
        log "error" "No servers found in MCP config"
        exit 1
    fi
    echo "Available MCP servers:"
    echo "$server_names"

    echo "Selecting servers to sync..."
    local selected_servers
    selected_servers=$(echo "$server_names" | select_skills)
    if [[ -z "$selected_servers" ]]; then
        log "error" "No servers selected"
        exit 1
    fi
    echo "Selected servers:"
    echo "$selected_servers"

    case "$conflict" in
        dry-run)
            echo "=== Dry-run: would write the following config ==="
            merge_configs "$config_json" "$selected_servers" "$config_file"
            ;;
        force)
            echo "[force] Writing config to $config_file"
            merge_and_write "$config_json" "$selected_servers" "$config_file"
            ;;
        sync)
            if [[ -f "$config_file" ]]; then
                local should_write
                should_write=$(prompt_yes_no "Config file exists. Overwrite?")
                if [[ "$should_write" == "n" ]]; then
                    echo "Skipping config sync."
                    return 0
                fi
            fi
            merge_and_write "$config_json" "$selected_servers" "$config_file"
            ;;
    esac

    echo "MCP config sync complete!"
}

main() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        help
        return 0
    fi

    echo "buc-mcp Sync Tool"
    echo "================="

    local mode
    mode=$(prompt "Choose sync mode" \
        "skills:Skills" \
        "mcp:MCP configs")

    case "$mode" in
        skills) sync_skill_main ;;
        mcp) sync_mcp_main ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
