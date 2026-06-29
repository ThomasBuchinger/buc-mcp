import pytest

from e2e_actions import *
from e2e_actions import read_prompt, read_resource

@pytest.mark.anyio
async def test_e2e_client_can_list_prompts_on_coding_server():
    start_mcpserver_for_e2e_tests()
    client = get_e2emcpclient("buc-coding")
    prompts = await fetch_prompts(client)
    names = map_prompts_result_to_names(prompts)
    assert "grill_me" in names


@pytest.mark.anyio
async def test_e2e_client_can_list_prompts_on_kubernetes_server():
    start_mcpserver_for_e2e_tests()
    client = get_e2emcpclient("buc-kubernetes")
    prompts = await fetch_prompts(client)
    names = map_prompts_result_to_names(prompts)
    assert "kubernetes_yaml" in names


@pytest.mark.anyio
async def test_e2e_client_can_read_prompt_by_name():
    start_mcpserver_for_e2e_tests()
    client = get_e2emcpclient("buc-coding")
    result = await read_prompt(client, "grill_me")
    assert result  # non-empty
    assert result.messages  # FastMCP GetPromptResult has .messages

@pytest.mark.anyio
async def test_e2e_client_can_list_skills_as_resources():
    start_mcpserver_for_e2e_tests()
    client = get_e2emcpclient("buc-skills")
    resources = await fetch_resources(client)
    uris = map_resources_to_uris(resources)
    assert any(uri.endswith("/SKILL.md") for uri in uris)


@pytest.mark.anyio
async def test_e2e_client_can_read_skill_md():
    start_mcpserver_for_e2e_tests()
    client = get_e2emcpclient("buc-skills")
    resources = await fetch_resources(client)
    uris = map_resources_to_uris(resources)
    skill_md = next(uri for uri in uris if uri.endswith("/SKILL.md"))
    content = await read_resource(client, skill_md)
    assert content
    assert len(str(content)) > 0


@pytest.mark.anyio
async def test_e2e_skills_directory_auto_discovered_multiple_skills():
    """SkillsDirectoryProvider picks up every skill subdirectory without code changes."""
    start_mcpserver_for_e2e_tests()
    client = get_e2emcpclient("buc-skills")
    resources = await fetch_resources(client)
    uris = map_resources_to_uris(resources)
    skill_md_uris = [u for u in uris if u.endswith("/SKILL.md")]
    # multiple distinct skills are discovered, not just one
    assert len(skill_md_uris) >= 2


@pytest.mark.anyio
async def test_e2e_prompts_directory_auto_discovered():
    """FileSystemProvider picks up prompt files without code changes."""
    start_mcpserver_for_e2e_tests()
    client = get_e2emcpclient("buc-coding")
    # prompts are discovered via the FileSystemProvider on the coding server
    # coding also exposes coding-passive skills as resources via SkillsDirectoryProvider
    resources = await fetch_resources(client)
    uris = map_resources_to_uris(resources)
    assert any("frontend-design" in uri for uri in uris)

