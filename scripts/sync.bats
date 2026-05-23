setup() {
    source "$BATS_TEST_DIRNAME/sync.sh"
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

# --- prompt_yes_no ---

@test "prompt_yes_no returns y for y input" {
    run bash -c 'source "$1"; echo "y" | prompt_yes_no "Continue?" 2>/dev/null' _ "$BATS_TEST_DIRNAME/sync.sh"
    [[ "$status" -eq 0 ]]
    [[ "$output" == "y" ]]
}

@test "prompt_yes_no returns n for n input" {
    run bash -c 'source "$1"; echo "n" | prompt_yes_no "Continue?" 2>/dev/null' _ "$BATS_TEST_DIRNAME/sync.sh"
    [[ "$status" -eq 0 ]]
    [[ "$output" == "n" ]]
}

@test "log outputs to stderr only" {
    run log "warn" "test message"
    [[ "$output" == "[warn] test message" ]]
}

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

# --- fetch_skill_list ---

@test "fetch_skill_list parses MCP resources/list response" {
    MCP_SESSION_ID="test-session"
    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"resources":[{"uri":"skill://mattpocock-tdd/SKILL.md"},{"uri":"skill://mattpocock-tdd/resources/tests.md"},{"uri":"skill://kubernetes-yaml/SKILL.md"}]}}\n'
    }
    export -f curl

    run fetch_skill_list
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "mattpocock-tdd"
    echo "$output" | grep -q "kubernetes-yaml"
    [[ "$(echo "$output" | wc -l)" -eq 2 ]]
}

@test "fetch_skill_resources filters by skill name" {
    MCP_SESSION_ID="test-session"
    function curl() {
        printf 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"resources":[{"uri":"skill://mattpocock-tdd/SKILL.md"},{"uri":"skill://mattpocock-tdd/resources/tests.md"},{"uri":"skill://kubernetes-yaml/SKILL.md"}]}}\n'
    }
    export -f curl

    run fetch_skill_resources "mattpocock-tdd"
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "skill://mattpocock-tdd/SKILL.md"
    echo "$output" | grep -q "skill://mattpocock-tdd/resources/tests.md"
    ! echo "$output" | grep -q "kubernetes-yaml"
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
