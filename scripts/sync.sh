#!/usr/bin/env bash
# Default SERVER_URL (overridden by /sync.sh endpoint via Host header injection)
SERVER_URL="${SERVER_URL:-http://localhost:8000}"
# Normalize: strip trailing slash, default to http:// if no scheme
SERVER_URL="${SERVER_URL%/}"
case "$SERVER_URL" in
    http://*|https://*) ;;
    *) SERVER_URL="http://$SERVER_URL" ;;
esac

# Model server is at a fixed address, independent of where this script is served from
MODEL_API_URL="${MODEL_API_URL:-http://10.0.0.190:32434/v1}"

CLIENT_AGENT=""
MCP_SESSION_ID=""

help() {
    cat <<'HELP'
Usage: sync.sh

Sync AI Code-Agent configs from server.
Modes: Skills, MCP configs, Models

Requires: curl, jq
Models mode: yq
Optional: fzf (for fuzzy selection)
HELP
}

log() {
    local level="$1"
    local message="$2"
    echo "[$level] $message" >&2
}

has_fzf() {
    command -v fzf >/dev/null 2>&1
}

# Read user input from the terminal. The script is usually run as
# `curl ... | bash`, where stdin is the script itself — interactive reads
# must come from /dev/tty. Set SYNC_STDIN=1 to read stdin instead (tests).
read_input() {
    if [[ -n "${SYNC_STDIN:-}" ]] || ! { : </dev/tty; } 2>/dev/null; then
        read -r "$@"
    else
        read -r "$@" </dev/tty
    fi
}

detect_agent() {
    if [[ -d ".claude" ]]; then
        CLIENT_AGENT="claude"
    else
        CLIENT_AGENT="opencode"
        [[ -d ".agents" ]] || log "warn" "No agent directory found, defaulting to opencode"
    fi
}

resolve_path() {
    local kind="$1"
    case "$CLIENT_AGENT:$kind" in
        claude:skills) echo ".claude/skills" ;;
        claude:config) echo ".claude/mcp.json" ;;
        claude:config-key) echo "mcpServers" ;;
        *:skills) echo ".agents/skills" ;;
        *:config) echo ".agents/opencode.json" ;;
        *:config-key) echo "mcp" ;;
    esac
}

# Single-choice menu. Args are "key:label" pairs; prints the chosen key.
# Returns non-zero if the user cancels (ESC in fzf).
prompt() {
    local title="$1"; shift
    local -a keys=() labels=()
    local arg
    for arg in "$@"; do
        keys+=("${arg%%:*}")
        labels+=("$arg")
    done

    if has_fzf; then
        local chosen
        chosen=$(printf '%s\n' "${labels[@]}" | fzf --exact --prompt="$title> ") || return 1
        echo "${chosen%%:*}"
        return 0
    fi

    local num
    while true; do
        echo "$title:" >&2
        local i
        for i in "${!labels[@]}"; do
            echo "$((i+1))) ${labels[$i]}" >&2
        done
        printf "Enter choice: " >&2
        read_input num || return 1
        if [[ "$num" =~ ^[0-9]+$ ]] && (( num >= 1 && num <= ${#keys[@]} )); then
            echo "${keys[$((num-1))]}"
            return 0
        fi
        echo "Invalid. Try again." >&2
    done
}

# Multi-select core. $1 = newline-separated items, $2 = newline-separated
# pre-selected items. Prints the selected items; an empty selection is valid.
#
# fzf path: pre-selection is real fzf selection state — start with only the
# pre-selected items, select-all, then reload the full list (selections
# persist across reload because fzf tracks them by item content).
# Fallback: numbered toggle menu, 0 finishes.
_select_multi() {
    local items="$1"
    local preselected="${2:-}"
    [[ -z "$items" ]] && return 1

    if [[ -n "$preselected" ]]; then
        # keep only pre-selected items that still exist, in list order
        preselected=$(grep -xF -f <(printf '%s\n' "$preselected") <<< "$items" || true)
    fi

    if has_fzf; then
        if [[ -z "$preselected" ]]; then
            fzf --multi --exact <<< "$items"
            return
        fi
        local all_file rc=0
        all_file=$(mktemp)
        printf '%s\n' "$items" > "$all_file"
        fzf --multi --exact --sync \
            --bind "start:select-all+reload(cat \"$all_file\")" \
            <<< "$preselected" || rc=$?
        rm -f "$all_file"
        return $rc
    fi

    local -a names selected
    mapfile -t names <<< "$items"
    local i
    for i in "${!names[@]}"; do
        if grep -qxF "${names[$i]}" <<< "$preselected"; then
            selected[i]=1
        else
            selected[i]=0
        fi
    done

    local -a nums
    local n finished=""
    while [[ -z "$finished" ]]; do
        echo "Toggle items (0 to finish):" >&2
        for i in "${!names[@]}"; do
            local mark=" "
            (( selected[i] )) && mark="x"
            echo "$((i+1))) [$mark] ${names[$i]}" >&2
        done
        printf "Toggle numbers (space-separated, 0 to finish): " >&2
        read_input -a nums || break
        for n in "${nums[@]}"; do
            if [[ "$n" == "0" ]]; then
                finished=1
            elif [[ "$n" =~ ^[0-9]+$ ]] && (( n >= 1 && n <= ${#names[@]} )); then
                selected[n-1]=$(( 1 - selected[n-1] ))
            else
                echo "Invalid: $n" >&2
            fi
        done
    done

    for i in "${!names[@]}"; do
        (( selected[i] )) && echo "${names[$i]}"
    done
    return 0
}

# Multi-select items given as args or on stdin. Nothing pre-selected.
select_skills() {
    local items
    if [[ $# -gt 0 ]]; then
        items=$(printf '%s\n' "$@")
    else
        items=$(cat)
    fi
    _select_multi "$items" ""
}

# Multi-select model ids from stdin; $1 = newline-separated pre-selected ids.
select_models() {
    _select_multi "$(cat)" "${1:-}"
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

    _mcp_post '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null || true
    return 0
}

# Fetch all resource URIs from the MCP server in one call.
fetch_resource_uris() {
    local response json
    response=$(_mcp_post '{"jsonrpc":"2.0","id":1,"method":"resources/list","params":{}}')
    json=$(_extract_json "$response")
    [[ -z "$json" ]] && return 1
    echo "$json" | jq -r '.result.resources[]?.uri'
}

read_resource_content() {
    local resource_uri="$1"
    local response json
    response=$(_mcp_post "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"resources/read\",\"params\":{\"uri\":\"$resource_uri\"}}")
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
                echo "$remote_content"
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
    key_name=$(resolve_path config-key)

    local merged='{}'
    if [[ -f "$existing_config_path" ]]; then
        merged=$(sed '/^[[:space:]]*\/\//d' "$existing_config_path" | jq -c '.')
    fi

    jq -c --argjson template "$template_json" --arg servers "$selected_servers" --arg key "$key_name" '
        ($servers | split("\n") | map(select(length > 0))) as $sel |
        ($template[$key] // {} | to_entries | map(select(.key as $k | $sel | index($k)))) as $entries |
        .[$key] = ((.[$key] // {}) + ($entries | from_entries))
    ' <<< "$merged"
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

# --- Models mode ---

# Prints one "id<TAB>name" line per model from the /v1/models endpoint.
fetch_models() {
    local response
    response=$(curl -sf "$MODEL_API_URL/models" 2>/dev/null) || return 1
    [[ -z "$response" ]] && return 1
    echo "$response" | jq -r '.data[] | [.id, (.name // "")] | @tsv'
}

humanize_display_name() {
    local id="$1"
    local name="${2:-}"
    echo "local / ${name:-$id}"
}

summarize_model_changes() {
    local existing selected
    existing=$(sort -u <<< "$1" | sed '/^$/d')
    selected=$(sort -u <<< "$2" | sed '/^$/d')

    local added removed unchanged
    added=$(comm -13 <(echo "$existing") <(echo "$selected"))
    removed=$(comm -23 <(echo "$existing") <(echo "$selected"))
    unchanged=$(comm -12 <(echo "$existing") <(echo "$selected"))

    echo "Summary of changes:"
    local label list
    for label in added removed unchanged; do
        list="${!label}"
        echo "  ${label} ($(grep -c . <<< "$list")):"
        [[ -n "$list" ]] && sed 's/^/    /' <<< "$list"
    done
    return 0
}

# Writes the "local" provider (creating it if missing) with exactly the given
# models. $2 is a JSON object: {"<id>": {"name": "<display name>"}, ...}.
# Only the provider block is touched; other sections and $schema survive.
update_opencode_json() {
    local config_file="$1"
    local models_json="$2"

    mkdir -p "$(dirname "$config_file")"
    [[ -f "$config_file" ]] || echo '{}' > "$config_file"

    MODELS_JSON="$models_json" BASE_URL="$MODEL_API_URL" \
    yq -p=json -o=json -i '
        .provider.local.npm = "@ai-sdk/openai-compatible" |
        .provider.local.name = "Local" |
        .provider.local.options.baseURL = strenv(BASE_URL) |
        .provider.local.options.apiKey = "aaa" |
        .provider.local.models = env(MODELS_JSON)
    ' "$config_file"
}

sync_model_main() {
    if ! command -v yq >/dev/null 2>&1; then
        log "error" "yq is required for model sync (https://github.com/mikefarah/yq)"
        exit 1
    fi

    # Models mode is opencode-only (see PRD 0006: Out of Scope)
    local config_file=".agents/opencode.json"

    echo "Fetching models from $MODEL_API_URL..."
    local models_tsv
    if ! models_tsv=$(fetch_models) || [[ -z "$models_tsv" ]]; then
        log "error" "Model API unreachable at $MODEL_API_URL"
        exit 1
    fi

    local all_ids existing=""
    all_ids=$(cut -f1 <<< "$models_tsv")
    if [[ -f "$config_file" ]]; then
        existing=$(yq -p=json '.provider.local.models // {} | keys | .[]' "$config_file" 2>/dev/null || true)
    fi

    echo "Selecting models (currently configured ones are pre-selected)..."
    local selected
    selected=$(select_models "$existing" <<< "$all_ids") || {
        log "error" "Selection cancelled"
        exit 1
    }

    summarize_model_changes "$existing" "$selected"

    local models_json='{}'
    local id name display
    while IFS=$'\t' read -r id name; do
        [[ -z "$id" ]] && continue
        grep -qxF "$id" <<< "$selected" || continue
        display=$(humanize_display_name "$id" "$name")
        models_json=$(jq --arg id "$id" --arg name "$display" '.[$id] = {name: $name}' <<< "$models_json")
    done <<< "$models_tsv"

    update_opencode_json "$config_file" "$models_json"
    echo "Model sync complete! Wrote $config_file"
}

# --- Mode entry points ---

sync_skill_main() {
    local conflict
    conflict=$(prompt "Choose conflict resolution" \
        "sync:sync (skip differing)" \
        "dry-run:dry-run (preview only)" \
        "force:force (overwrite)") || exit 1

    if ! session_init; then
        log "error" "Failed to initialize MCP session"
        exit 1
    fi
    echo "Session established."

    detect_agent
    echo "Detected agent: $CLIENT_AGENT"

    local agent_skills_dir
    agent_skills_dir=$(resolve_path skills)
    echo "Skills directory: $agent_skills_dir"

    echo "Fetching available skills..."
    local uris skill_list
    uris=$(fetch_resource_uris)
    skill_list=$(sed 's|^skill://||' <<< "$uris" | cut -d/ -f1 | sed '/^$/d' | sort -u)
    if [[ -z "$skill_list" ]]; then
        log "error" "No skills found"
        exit 1
    fi

    echo "Selecting skills..."
    local selected
    selected=$(select_skills <<< "$skill_list")
    if [[ -z "$selected" ]]; then
        log "error" "No skills selected"
        exit 1
    fi

    echo "Syncing skills to $agent_skills_dir..."
    local skill_name resource_uri local_path
    while IFS= read -r skill_name; do
        [[ -z "$skill_name" ]] && continue
        echo ""
        echo "=== Syncing skill: $skill_name ==="
        while IFS= read -r resource_uri; do
            [[ -z "$resource_uri" ]] && continue
            local_path="$agent_skills_dir/$skill_name/${resource_uri#skill://"$skill_name"/}"
            [[ "$local_path" == */_manifest ]] && continue
            sync_file "$resource_uri" "$local_path" "$conflict"
        done <<< "$(grep "^skill://$skill_name/" <<< "$uris" || true)"
    done <<< "$selected"

    echo ""
    echo "Sync complete!"
}

sync_mcp_main() {
    local conflict
    conflict=$(prompt "Choose conflict resolution" \
        "sync:sync (skip differing)" \
        "dry-run:dry-run (preview only)" \
        "force:force (overwrite)") || exit 1

    detect_agent
    echo "Detected agent: $CLIENT_AGENT"

    local config_file
    config_file=$(resolve_path config)
    echo "Config file: $config_file"

    echo "Fetching MCP server list from server..."
    local config_json
    config_json=$(curl -s "$SERVER_URL/mcp.json?agent=$CLIENT_AGENT")
    if [[ -z "$config_json" ]]; then
        log "error" "Failed to fetch MCP config"
        exit 1
    fi

    local key_name server_names
    key_name=$(resolve_path config-key)
    server_names=$(echo "$config_json" | jq -r ".${key_name} | keys[]")
    if [[ -z "$server_names" ]]; then
        log "error" "No servers found in MCP config"
        exit 1
    fi

    echo "Selecting servers to sync..."
    local selected_servers
    selected_servers=$(echo "$server_names" | select_skills)
    if [[ -z "$selected_servers" ]]; then
        log "error" "No servers selected"
        exit 1
    fi

    case "$conflict" in
        force|sync)
            echo "Merging servers into $config_file"
            merge_and_write "$config_json" "$selected_servers" "$config_file"
            ;;
        dry-run)
            local merged
            merged=$(merge_configs "$config_json" "$selected_servers" "$config_file")
            if [[ -f "$config_file" ]]; then
                echo "=== Dry-run: diff between $config_file and merged result ==="
                diff "$config_file" <(echo "$merged" | jq '.') 2>&1 || true
            else
                echo "=== Dry-run: would create $config_file with ==="
                echo "$merged" | jq '.'
            fi
            ;;
    esac

    echo "MCP config sync complete!"
}

main() {
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        help
        return 0
    fi
    set -u

    echo "buc-mcp Sync Tool"
    echo "================="

    local mode
    mode=$(prompt "Choose sync mode" \
        "skills:Skills" \
        "mcp:MCP configs" \
        "models:Models") || exit 1

    case "$mode" in
        skills) sync_skill_main ;;
        mcp) sync_mcp_main ;;
        models) sync_model_main ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
