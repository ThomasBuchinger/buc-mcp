setup() {
    source "$BATS_TEST_DIRNAME/sync.sh"
    export SYNC_STDIN=1
    SERVER_URL="http://test:8000"
    CLIENT_AGENT=""
    MCP_SESSION_ID=""
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# --- detect_agent ---

@test "detect_agent defaults to opencode" {
    detect_agent
    [[ "$CLIENT_AGENT" == "opencode" ]]
}

@test "detect_agent warns when no agent directory exists" {
    run detect_agent
    echo "$output" | grep -q "warn"
}

@test "detect_agent does not warn when .agents exists" {
    mkdir -p .agents
    run detect_agent
    [[ -z "$output" ]]
}

@test "detect_agent detects claude via .claude/skills" {
    mkdir -p .claude/skills
    detect_agent
    [[ "$CLIENT_AGENT" == "claude" ]]
}

@test "detect_agent detects claude via .claude" {
    mkdir -p .claude
    detect_agent
    [[ "$CLIENT_AGENT" == "claude" ]]
}

@test "detect_agent detects opencode via .agents/skills" {
    mkdir -p .agents/skills
    detect_agent
    [[ "$CLIENT_AGENT" == "opencode" ]]
}

@test "detect_agent detects opencode via .agents" {
    mkdir -p .agents
    detect_agent
    [[ "$CLIENT_AGENT" == "opencode" ]]
}

@test "detect_agent prefers .claude/skills over .agents" {
    mkdir -p .claude/skills .agents
    detect_agent
    [[ "$CLIENT_AGENT" == "claude" ]]
}

# --- resolve_path ---

@test "resolve_path returns .agents/skills for opencode skills" {
    CLIENT_AGENT="opencode"
    run resolve_path skills
    [[ "$output" == ".agents/skills" ]]
}

@test "resolve_path returns .claude/skills for claude skills" {
    CLIENT_AGENT="claude"
    run resolve_path skills
    [[ "$output" == ".claude/skills" ]]
}

@test "resolve_path defaults to .agents/skills for unknown agent" {
    CLIENT_AGENT="unknown"
    run resolve_path skills
    [[ "$output" == ".agents/skills" ]]
}

@test "resolve_path returns .agents/opencode.json for opencode config" {
    CLIENT_AGENT="opencode"
    run resolve_path config
    [[ "$output" == ".agents/opencode.json" ]]
}

@test "resolve_path returns .claude/mcp.json for claude config" {
    CLIENT_AGENT="claude"
    run resolve_path config
    [[ "$output" == ".claude/mcp.json" ]]
}

@test "resolve_path returns mcp config-key for opencode" {
    CLIENT_AGENT="opencode"
    run resolve_path config-key
    [[ "$output" == "mcp" ]]
}

@test "resolve_path returns mcpServers config-key for claude" {
    CLIENT_AGENT="claude"
    run resolve_path config-key
    [[ "$output" == "mcpServers" ]]
}

# --- write_file ---

@test "write_file creates directory and writes content" {
    write_file "sub/test.txt" "hello world"
    [[ -f "sub/test.txt" ]]
    [[ "$(cat sub/test.txt)" == "hello world" ]]
}

@test "write_file overwrites existing file" {
    write_file "test.txt" "first"
    write_file "test.txt" "second"
    [[ "$(cat test.txt)" == "second" ]]
}

# --- log ---

@test "log outputs to stderr only" {
    run log "warn" "test message"
    [[ "$output" == "[warn] test message" ]]
}

# --- SERVER_URL normalization ---

@test "SERVER_URL default normalization adds http scheme" {
    SERVER_URL="localhost:8000"
    source "$BATS_TEST_DIRNAME/sync.sh"
    [[ "$SERVER_URL" == "http://localhost:8000" ]]
}

@test "SERVER_URL normalization strips trailing slash" {
    SERVER_URL="http://example.com/"
    source "$BATS_TEST_DIRNAME/sync.sh"
    [[ "$SERVER_URL" == "http://example.com" ]]
}

@test "SERVER_URL normalization keeps https scheme" {
    SERVER_URL="https://example.com"
    source "$BATS_TEST_DIRNAME/sync.sh"
    [[ "$SERVER_URL" == "https://example.com" ]]
}

@test "MODEL_API_URL has a default and is env-overridable" {
    [[ "$MODEL_API_URL" == "http://10.0.0.190:32434/v1" ]]
    MODEL_API_URL="http://other:1234/v1"
    source "$BATS_TEST_DIRNAME/sync.sh"
    [[ "$MODEL_API_URL" == "http://other:1234/v1" ]]
}

# --- prompt ---

@test "prompt with fzf returns key of chosen label" {
    function fzf() { head -1; }
    export -f fzf

    run prompt "Choose" "sync:sync (skip differing)" "force:force (overwrite)"
    [[ "$status" -eq 0 ]]
    [[ "$output" == "sync" ]]
}

@test "prompt returns non-zero when fzf is cancelled" {
    function fzf() { return 130; }
    export -f fzf

    run prompt "Choose" "a:A" "b:B"
    [[ "$status" -ne 0 ]]
}

@test "prompt numbered fallback returns key for chosen number" {
    has_fzf() { return 1; }

    result=$(echo "2" | prompt "Choose" "a:A" "b:B" 2>/dev/null)
    [[ "$result" == "b" ]]
}

# --- select_skills / _select_multi ---

@test "select_skills with fzf returns all items" {
    function fzf() { cat; }
    export -f fzf

    run select_skills "skill-a" "skill-b"
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "skill-a"
    echo "$output" | grep -q "skill-b"
}

@test "select_skills with fzf handles single item" {
    function fzf() { cat; }
    export -f fzf

    run select_skills "only-one"
    [[ "$status" -eq 0 ]]
    [[ "$output" == "only-one" ]]
}

@test "_select_multi fails on empty input" {
    run _select_multi "" ""
    [[ "$status" -ne 0 ]]
}

@test "_select_multi with fzf feeds pre-selected items first" {
    # mocked fzf prints its input: with pre-selection the initial list is
    # exactly the pre-selected items (full list arrives via reload binding)
    function fzf() { cat; }
    export -f fzf

    run _select_multi $'model-a\nmodel-b\nmodel-c' $'model-b'
    [[ "$status" -eq 0 ]]
    [[ "$output" == "model-b" ]]
}

@test "_select_multi drops pre-selected items missing from the list" {
    function fzf() { cat; }
    export -f fzf

    # "stale" is not in the item list; falls back to the plain full-list path
    run _select_multi $'model-a\nmodel-b' $'stale'
    [[ "$status" -eq 0 ]]
    [[ "$output" == $'model-a\nmodel-b' ]]
}

@test "_select_multi toggle menu shows pre-selected items with [x]" {
    has_fzf() { return 1; }

    output=$(echo "0" | _select_multi $'a\nb\nc' $'b' 2>&1 >/dev/null)
    echo "$output" | grep -qF "2) [x] b"
    echo "$output" | grep -qF "1) [ ] a"
}

@test "_select_multi toggle menu keeps pre-selected items on finish" {
    has_fzf() { return 1; }

    result=$(echo "0" | _select_multi $'a\nb\nc' $'b' 2>/dev/null)
    [[ "$result" == "b" ]]
}

@test "_select_multi toggle menu toggles items on and off" {
    has_fzf() { return 1; }

    # toggle a on, toggle b off, finish
    result=$(echo "1 2 0" | _select_multi $'a\nb\nc' $'b' 2>/dev/null)
    [[ "$result" == "a" ]]
}

@test "_select_multi toggle menu allows empty selection" {
    has_fzf() { return 1; }

    result=$(echo "2 0" | _select_multi $'a\nb\nc' $'b' 2>/dev/null)
    [[ -z "$result" ]]
}

# --- fetch_resource_uris ---

@test "fetch_resource_uris lists all resource uris" {
    MCP_SESSION_ID="test-session"
    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"resources":[{"uri":"skill://mattpocock-tdd/SKILL.md"},{"uri":"skill://mattpocock-tdd/resources/tests.md"},{"uri":"skill://kubernetes-yaml/SKILL.md"}]}}\n'
    }
    export -f curl

    run fetch_resource_uris
    [[ "$status" -eq 0 ]]
    [[ "$(echo "$output" | wc -l)" -eq 3 ]]
    echo "$output" | grep -q "skill://mattpocock-tdd/resources/tests.md"
    echo "$output" | grep -q "skill://kubernetes-yaml/SKILL.md"
}

@test "fetch_resource_uris fails on empty response" {
    function curl() { echo ""; }
    export -f curl

    run fetch_resource_uris
    [[ "$status" -ne 0 ]]
}

@test "read_resource_content extracts content from MCP response" {
    MCP_SESSION_ID="test-session"
    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"skill://test/SKILL.md","text":"# Test Skill\\n\\nSome content"}]}}\n'
    }
    export -f curl

    run read_resource_content "skill://test/SKILL.md"
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "Test Skill"
}

# --- session_init ---

@test "session_init sends initialize and extracts mcp-session-id" {
    function curl() {
        if echo "$*" | grep -q "initialize"; then
            echo "HTTP/1.1 200 OK"
            echo "mcp-session-id: test-session-abc"
            echo "content-type: application/json"
            echo ""
            echo '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05"}}'
        else
            echo ""
        fi
    }
    export -f curl

    session_init
    [[ "$MCP_SESSION_ID" == "test-session-abc" ]]
}

@test "session_init fails when no session id returned" {
    function curl() {
        echo "HTTP/1.1 200 OK"
        echo ""
        echo '{"jsonrpc":"2.0","id":1,"result":{}}'
    }
    export -f curl

    run session_init
    [[ "$status" -ne 0 ]]
    [[ -z "$MCP_SESSION_ID" ]]
}

# --- sync_file with dry-run ---

@test "sync_file with dry-run shows diff for existing differing file" {
    MCP_SESSION_ID="test-session"

    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"skill://test/SKILL.md","text":"new content"}]}}\n'
    }
    export -f curl

    mkdir -p test
    echo "old content" > test/file.txt

    run sync_file "skill://test/SKILL.md" "test/file.txt" "dry-run"
    echo "$output" | grep -q "would differ"
}

@test "sync_file with dry-run shows new file content" {
    MCP_SESSION_ID="test-session"

    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"skill://test/SKILL.md","text":"new content"}]}}\n'
    }
    export -f curl

    run sync_file "skill://test/SKILL.md" "test/new.txt" "dry-run"
    echo "$output" | grep -q "New file"
    echo "$output" | grep -q "new content"
}

# --- sync_file with force ---

@test "sync_file with force overwrites existing file" {
    MCP_SESSION_ID="test-session"

    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"skill://test/SKILL.md","text":"new content"}]}}\n'
    }
    export -f curl

    mkdir -p test
    echo "old content" > test/file.txt

    run sync_file "skill://test/SKILL.md" "test/file.txt" "force"
    [[ "$(cat test/file.txt)" == "new content" ]]
}

@test "sync_file with force writes new file" {
    MCP_SESSION_ID="test-session"

    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"skill://test/SKILL.md","text":"new content"}]}}\n'
    }
    export -f curl

    run sync_file "skill://test/SKILL.md" "test/new_file.txt" "force"
    [[ "$(cat test/new_file.txt)" == "new content" ]]
}

# --- sync_file with sync ---

@test "sync_file with sync skips differing file" {
    MCP_SESSION_ID="test-session"

    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"skill://test/SKILL.md","text":"new content"}]}}\n'
    }
    export -f curl

    mkdir -p test
    echo "old content" > test/file.txt

    run sync_file "skill://test/SKILL.md" "test/file.txt" "sync"
    echo "$output" | grep -q "differs (skipping)"
    [[ "$(cat test/file.txt)" == "old content" ]]
}

@test "sync_file with sync writes identical file" {
    MCP_SESSION_ID="test-session"

    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"skill://test/SKILL.md","text":"same content"}]}}\n'
    }
    export -f curl

    mkdir -p test
    echo "same content" > test/file.txt

    run sync_file "skill://test/SKILL.md" "test/file.txt" "sync"
    echo "$output" | grep -q "Identical"
}

@test "sync_file with sync writes new file" {
    MCP_SESSION_ID="test-session"

    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"skill://test/SKILL.md","text":"new content"}]}}\n'
    }
    export -f curl

    run sync_file "skill://test/SKILL.md" "test/new_file.txt" "sync"
    [[ "$(cat test/new_file.txt)" == "new content" ]]
}

# --- merge_configs ---

@test "merge_configs additively merges selected servers" {
    CLIENT_AGENT="opencode"

    local template='{"mcp":{"server-a":{"type":"remote","url":"http://a"}}}'
    local existing='{"mcp":{"server-b":{"type":"remote","url":"http://b"}}}'
    echo "$existing" > config.json

    run merge_configs "$template" $'server-a' "config.json"

    echo "$output" | jq -e '.mcp["server-a"]' >/dev/null
    echo "$output" | jq -e '.mcp["server-b"]' >/dev/null
    local a_url
    a_url=$(echo "$output" | jq -r '.mcp["server-a"].url')
    [[ "$a_url" == "http://a" ]]
}

@test "merge_configs keeps existing servers not in selected" {
    CLIENT_AGENT="opencode"

    local template='{"mcp":{"server-a":{"type":"remote","url":"http://a"},"server-c":{"type":"remote","url":"http://c"}}}'
    local existing='{"mcp":{"server-b":{"type":"remote","url":"http://b"}}}'
    echo "$existing" > config.json

    run merge_configs "$template" $'server-a\nserver-c' "config.json"

    echo "$output" | jq -e '.mcp["server-a"]' >/dev/null
    echo "$output" | jq -e '.mcp["server-b"]' >/dev/null
    echo "$output" | jq -e '.mcp["server-c"]' >/dev/null
}

@test "merge_configs creates mcp key when existing config is empty" {
    CLIENT_AGENT="opencode"

    local template='{"mcp":{"server-a":{"type":"remote","url":"http://a"}}}'

    run merge_configs "$template" $'server-a' "/nonexistent/config.json"
    echo "$output" | jq -e '.mcp["server-a"]' >/dev/null
}

@test "merge_configs works with claude key name" {
    CLIENT_AGENT="claude"

    local template='{"mcpServers":{"server-a":{"type":"http","url":"http://a"}}}'
    local existing='{"mcpServers":{"server-b":{"type":"http","url":"http://b"}}}'
    echo "$existing" > config.json

    run merge_configs "$template" $'server-a' "config.json"
    echo "$output" | jq -e '.mcpServers["server-a"]' >/dev/null
    echo "$output" | jq -e '.mcpServers["server-b"]' >/dev/null
}

# --- merge_and_write ---

@test "merge_and_write creates parent directory and writes valid JSON" {
    CLIENT_AGENT="opencode"

    local template='{"mcp":{"server-a":{"type":"remote","url":"http://a"}}}'

    merge_and_write "$template" $'server-a' "subdir/config.json"
    [[ -f "subdir/config.json" ]]
    jq -e '.mcp["server-a"]' "subdir/config.json" >/dev/null
}

# --- fetch_models ---

@test "fetch_models extracts id and name as TSV" {
    function curl() {
        printf '{"data":[{"id":"gemma4-26b","object":"model","name":"Gemma 4 26B (80tps)"},{"id":"gptoss-20b","object":"model"}]}'
    }
    export -f curl

    run fetch_models
    [[ "$status" -eq 0 ]]
    [[ "${lines[0]}" == $'gemma4-26b\tGemma 4 26B (80tps)' ]]
    [[ "${lines[1]}" == "gptoss-20b"* ]]
}

@test "fetch_models fails when API is unreachable" {
    function curl() { return 7; }
    export -f curl

    run fetch_models
    [[ "$status" -ne 0 ]]
}

@test "fetch_models fails on empty response" {
    function curl() { printf ''; }
    export -f curl

    run fetch_models
    [[ "$status" -ne 0 ]]
}

# --- humanize_display_name ---

@test "humanize_display_name uses name when present" {
    run humanize_display_name "gemma4-26b" "Gemma 4 26B (80tps)"
    [[ "$output" == "local / Gemma 4 26B (80tps)" ]]
}

@test "humanize_display_name falls back to id" {
    run humanize_display_name "gptoss-20b" ""
    [[ "$output" == "local / gptoss-20b" ]]
}

# --- summarize_model_changes ---

@test "summarize_model_changes reports added, removed and unchanged" {
    run summarize_model_changes $'model-a\nmodel-b' $'model-b\nmodel-c'
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "added (1):"
    echo "$output" | grep -q "removed (1):"
    echo "$output" | grep -q "unchanged (1):"
    echo "$output" | grep -A1 "added" | grep -q "model-c"
    echo "$output" | grep -A1 "removed" | grep -q "model-a"
}

@test "summarize_model_changes handles empty existing set" {
    run summarize_model_changes "" $'model-a'
    echo "$output" | grep -q "added (1):"
    echo "$output" | grep -q "removed (0):"
}

# --- update_opencode_json ---

@test "update_opencode_json creates config and provider from scratch" {
    update_opencode_json ".agents/opencode.json" '{"model-a":{"name":"local / model-a"}}'

    [[ -f ".agents/opencode.json" ]]
    jq -e '.provider.local' .agents/opencode.json >/dev/null
    [[ "$(jq -r '.provider.local.npm' .agents/opencode.json)" == "@ai-sdk/openai-compatible" ]]
    [[ "$(jq -r '.provider.local.name' .agents/opencode.json)" == "Local" ]]
    [[ "$(jq -r '.provider.local.options.baseURL' .agents/opencode.json)" == "$MODEL_API_URL" ]]
    [[ "$(jq -r '.provider.local.options.apiKey' .agents/opencode.json)" == "aaa" ]]
    [[ "$(jq -r '.provider.local.models["model-a"].name' .agents/opencode.json)" == "local / model-a" ]]
}

@test "update_opencode_json preserves schema and other sections" {
    mkdir -p .agents
    printf '{"$schema":"https://opencode.ai/config.json","mcp":{"srv":{"type":"remote","url":"http://x"}}}\n' > .agents/opencode.json

    update_opencode_json ".agents/opencode.json" '{"model-a":{"name":"local / model-a"}}'

    [[ "$(jq -r '."$schema"' .agents/opencode.json)" == "https://opencode.ai/config.json" ]]
    [[ "$(jq -r '.mcp.srv.url' .agents/opencode.json)" == "http://x" ]]
}

@test "update_opencode_json replaces models removing unselected ones" {
    update_opencode_json ".agents/opencode.json" '{"model-a":{"name":"a"},"model-b":{"name":"b"}}'
    update_opencode_json ".agents/opencode.json" '{"model-b":{"name":"b"}}'

    run jq -r '.provider.local.models | keys[]' .agents/opencode.json
    [[ "$output" == "model-b" ]]
}

# --- sync_model_main ---

@test "sync_model_main full flow writes selected models" {
    function curl() {
        printf '{"data":[{"id":"model-a","name":"Model A"},{"id":"model-b"}]}'
    }
    function fzf() { cat; }
    export -f curl fzf

    run sync_model_main
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "added (2):"
    [[ "$(jq -r '.provider.local.models["model-a"].name' .agents/opencode.json)" == "local / Model A" ]]
    [[ "$(jq -r '.provider.local.models["model-b"].name' .agents/opencode.json)" == "local / model-b" ]]
}

@test "sync_model_main pre-selects existing models and reports unchanged" {
    mkdir -p .agents
    printf '{"provider":{"local":{"models":{"model-a":{"name":"local / Model A"}}}}}\n' > .agents/opencode.json

    function curl() {
        printf '{"data":[{"id":"model-a","name":"Model A"},{"id":"model-b"}]}'
    }
    # mocked fzf prints its input: the pre-selected existing model
    function fzf() { cat; }
    export -f curl fzf

    run sync_model_main
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "unchanged (1):"
    [[ "$(jq -r '.provider.local.models | keys | length' .agents/opencode.json)" -eq 1 ]]
}

@test "sync_model_main exits with error when API is unreachable" {
    function curl() { return 7; }
    export -f curl

    run sync_model_main
    [[ "$status" -ne 0 ]]
    echo "$output" | grep -q "unreachable"
    [[ ! -f ".agents/opencode.json" ]]
}
