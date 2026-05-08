#!/usr/bin/env bats

# BATS tests for sync.sh
# Source sync.sh and test functions in isolation

setup() {
    source "${BATS_TEST_DIRNAME}/sync.sh"
    TEST_DIR=$(mktemp -d)
    SERVER_URL="http://mock-server:8000"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# --- detect_agent tests ---

@test "detect_agent sets CLIENT_AGENT to opencode when .agents/skills exists" {
    local test_dir="$TEST_DIR/detect"
    mkdir -p "$test_dir/.agents/skills"
    cd "$test_dir"

    CLIENT_AGENT=""
    detect_agent

    [ "$CLIENT_AGENT" = "opencode" ]
}

@test "detect_agent sets CLIENT_AGENT to claude when only .claude/skills exists" {
    local test_dir="$TEST_DIR/detect_claude"
    mkdir -p "$test_dir/.claude/skills"
    cd "$test_dir"

    CLIENT_AGENT=""
    detect_agent

    [ "$CLIENT_AGENT" = "claude" ]
}

@test "detect_agent defaults to opencode when neither directory exists" {
    local test_dir="$TEST_DIR/detect_none"
    mkdir -p "$test_dir"
    cd "$test_dir"

    CLIENT_AGENT=""
    detect_agent

    [ "$CLIENT_AGENT" = "opencode" ]
}

# --- resolve_skills_dir tests ---

@test "resolve_skills_dir returns .agents/skills for opencode" {
    CLIENT_AGENT="opencode"
    local output
    output=$(resolve_skills_dir)

    [ "$output" = ".agents/skills" ]
}

@test "resolve_skills_dir returns .claude/skills for claude" {
    CLIENT_AGENT="claude"
    local output
    output=$(resolve_skills_dir)

    [ "$output" = ".claude/skills" ]
}

# --- Helper to create curl/jq mocks for sync_file ---

create_sync_mocks() {
    local mock_bin="$1"
    local content="$2"
    mkdir -p "$mock_bin"

    cat > "$mock_bin/curl" << MOCKEOF
#!/bin/bash
echo '{"jsonrpc":"2.0","id":1,"result":{"content":"${content}"}}'
MOCKEOF
    chmod +x "$mock_bin/curl"

    cat > "$mock_bin/jq" << 'JQEOF'
#!/bin/bash
# Extract .result.content from JSON
if [[ "$1" == "-r" ]] && [[ "$2" == ".result.content // empty" ]]; then
    cat | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('result',{}).get('content',''))"
else
    cat
fi
JQEOF
    chmod +x "$mock_bin/jq"
}

# --- fetch_skill_list tests ---

@test "fetch_skill_list returns sorted unique skill names" {
    local mock_bin="$TEST_DIR/fsl_mock"
    mkdir -p "$mock_bin"

    cat > "$mock_bin/curl" << 'MOCKEOF'
#!/bin/bash
echo '{"jsonrpc":"2.0","id":1,"result":{"resources":[{"uri":"skill://coding-passive/mattpocock-tdd/SKILL.md","name":"SKILL.md"},{"uri":"skill://kubernetes-passive/kubernetes-yaml/SKILL.md","name":"SKILL.md"}]}}'
MOCKEOF
    chmod +x "$mock_bin/curl"

    cat > "$mock_bin/jq" << 'MOCKEOF'
#!/bin/bash
cat
MOCKEOF
    chmod +x "$mock_bin/jq"

    local result
    result=$(PATH="$mock_bin:$PATH" fetch_skill_list)
    local status=$?

    [ "$status" -eq 0 ]
    echo "$result" | grep -q "coding-passive"
    echo "$result" | grep -q "kubernetes-passive"
}

# --- select_skills tests ---

@test "select_skills returns all skills from stdin with fzf" {
    local mock_bin="$TEST_DIR/ss_mock"
    mkdir -p "$mock_bin"

    # Fake fzf that echoes all input (simulates selecting everything)
    cat > "$mock_bin/fzf" << 'MOCKEOF'
#!/bin/bash
cat
MOCKEOF
    chmod +x "$mock_bin/fzf"

    local result
    result=$(echo -e "skill-a\nskill-b\nskill-c" | PATH="$mock_bin:$PATH" bash -c 'source '"$BATS_TEST_DIRNAME/sync.sh"' && select_skills' 2>&1)

    echo "$result" | grep -q "skill-a"
    echo "$result" | grep -q "skill-b"
    echo "$result" | grep -q "skill-c"
}

@test "select_skills exits with error when empty input" {
    local mock_bin="$TEST_DIR/ss_err_mock"
    mkdir -p "$mock_bin"
    cat > "$mock_bin/fzf" << 'MOCKEOF'
#!/bin/bash
cat
MOCKEOF
    chmod +x "$mock_bin/fzf"

    local output
    output=$(echo -n "" | PATH="$mock_bin:$PATH" bash -c 'source '"$BATS_TEST_DIRNAME/sync.sh"' && select_skills' 2>&1) || true

    echo "$output" | grep -q "No skills"
}

# --- write_file tests ---

@test "write_file creates directories and writes content" {
    local test_file="$TEST_DIR/wf/deep/nested/file.txt"
    write_file "$test_file" "hello world"

    [ -f "$test_file" ]
    [ "$(cat "$test_file")" = "hello world" ]
}

@test "write_file overwrites existing file" {
    local test_file="$TEST_DIR/wf/overwrite.txt"
    mkdir -p "$(dirname "$test_file")"
    echo "old content" > "$test_file"

    write_file "$test_file" "new content"
    [ "$(cat "$test_file")" = "new content" ]
}

@test "write_file creates parent directories automatically" {
    local test_file="$TEST_DIR/wf/aaa/bbb/ccc/ddd/file.txt"
    write_file "$test_file" "content"

    [ -d "$TEST_DIR/wf/aaa/bbb/ccc/ddd" ]
    [ "$(cat "$test_file")" = "content" ]
}

# --- sync_file tests ---

@test "sync_file writes new file when local path does not exist" {
    local mock_bin="$TEST_DIR/sync1"
    create_sync_mocks "$mock_bin" "new skill content"

    local test_file="$TEST_DIR/sync_test/new.txt"
    DRY_RUN=0
    FORCE=0

    local output
    output=$(PATH="$mock_bin:$PATH" sync_file "skill://test/new.txt" "$test_file" 2>&1)
    local status=$?

    [ "$status" -eq 0 ]
    [ -f "$test_file" ]
    echo "$output" | grep -q "Writing new file"
}

@test "sync_file shows up-to-date message when file matches" {
    local mock_bin="$TEST_DIR/sync2"
    create_sync_mocks "$mock_bin" "matching content"

    local test_file="$TEST_DIR/sync_test/match.txt"
    mkdir -p "$(dirname "$test_file")"
    echo "matching content" > "$test_file"
    DRY_RUN=0
    FORCE=0

    local output
    output=$(PATH="$mock_bin:$PATH" sync_file "skill://test/match.txt" "$test_file" 2>&1)
    local status=$?

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "up to date"
}

@test "sync_file shows diff and does not write when files differ and force=0" {
    local mock_bin="$TEST_DIR/sync3"
    create_sync_mocks "$mock_bin" "different content"

    local test_file="$TEST_DIR/sync_test/diff.txt"
    mkdir -p "$(dirname "$test_file")"
    echo "original content" > "$test_file"
    DRY_RUN=0
    FORCE=0

    local output
    output=$(PATH="$mock_bin:$PATH" sync_file "skill://test/diff.txt" "$test_file" 2>&1)
    local status=$?

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "differs"
    echo "$output" | grep -q "Re-run with --force"
    [ "$(cat "$test_file")" = "original content" ]
}

@test "sync_file with --force bypasses diff and writes" {
    local mock_bin="$TEST_DIR/sync5"
    create_sync_mocks "$mock_bin" "force content"

    local test_file="$TEST_DIR/sync_test/force.txt"
    mkdir -p "$(dirname "$test_file")"
    echo "original content" > "$test_file"
    DRY_RUN=0
    FORCE=1

    local output
    output=$(PATH="$mock_bin:$PATH" sync_file "skill://test/force.txt" "$test_file" 2>&1)
    local status=$?

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "force"
    [ "$(cat "$test_file")" = "force content" ]
}

# --- fetch_skill_resources tests ---

@test "fetch_skill_resources returns URIs for a specific skill" {
    local mock_bin="$TEST_DIR/fsr_mock"
    mkdir -p "$mock_bin"

    cat > "$mock_bin/curl" << 'MOCKEOF'
#!/bin/bash
echo '{"jsonrpc":"2.0","id":1,"result":{"resources":[{"uri":"skill://test-skill/SKILL.md","name":"SKILL.md"},{"uri":"skill://test-skill/resources/file.txt","name":"file.txt"},{"uri":"skill://other-skill/SKILL.md","name":"SKILL.md"}]}}'
MOCKEOF
    chmod +x "$mock_bin/curl"

    local result
    result=$(PATH="$mock_bin:$PATH" fetch_skill_resources "test-skill" 2>&1)
    local status=$?

    [ "$status" -eq 0 ]
    echo "$result" | grep -q "skill://test-skill/SKILL.md"
    echo "$result" | grep -q "skill://test-skill/resources/file.txt"
    [[ "$result" != *"other-skill"* ]]
}
