# Dual-Provider Pattern: SkillsDirectoryProvider + FileSystemProvider

Skills are exposed through two FastMCP providers: `SkillsDirectoryProvider` (exposes skill files as MCP resources) and `FileSystemProvider` (scans `prompts/` for `@prompt`-decorated Python files). Single-file skills that make sense as direct user commands get both — their SKILL.md content is served as a `skill://` resource *and* wrapped in a `@prompt` that reads the same file content. Multi-file skills are served only through `SkillsDirectoryProvider`.

This is not a design preference — it's a workaround. MCP clients do not treat skill resources the same as local skills. Clients have `/prompt` commands but no `/skill` command to invoke resources directly. `SkillsDirectoryProvider` alone would work if clients treated exposed resources the same as local skills, but they don't.
