# CHANGELOG

<!-- version list -->

## v0.6.0 (2026-05-08)

### Bug Fixes

- Typo in file path for new prompts
  ([`75608df`](https://github.com/thomasbuchinger/buc-mcp/commit/75608dfa69be8590ecba98677ea6300a2a7762ef))

### Documentation

- Add ADRs for existing decisions
  ([`2f0ec23`](https://github.com/thomasbuchinger/buc-mcp/commit/2f0ec23f1505ab850479cb8e31401393ca25f6da))

### Features

- Add additional skills by Matt Pocock
  ([`348e27c`](https://github.com/thomasbuchinger/buc-mcp/commit/348e27ce146d4f057667356fcf7f5353683cc9e1))

- Add mcp config template (prep for sync feature)
  ([`75a8673`](https://github.com/thomasbuchinger/buc-mcp/commit/75a867300fa6a83df37b01df01233471afbf5de1))


## v0.5.3 (2026-05-03)

### Bug Fixes

- Add noop-tool to prompt-only servers
  ([`77606e4`](https://github.com/thomasbuchinger/buc-mcp/commit/77606e4daca188f363744ddebbf55e7527a3fd96))


## v0.5.2 (2026-05-03)

### Bug Fixes

- Server path. was at /mcp/mcp
  ([`71423b8`](https://github.com/thomasbuchinger/buc-mcp/commit/71423b89a67c5a82849df3cfa0d1620458911e4c))


## v0.5.1 (2026-05-03)

### Bug Fixes

- Remove MCP inspector deployment
  ([`f061368`](https://github.com/thomasbuchinger/buc-mcp/commit/f0613689ed946c3baf55e18e5da8dcf161aace5b))

### Documentation

- Update README for multi path architecture
  ([`ba3efe6`](https://github.com/thomasbuchinger/buc-mcp/commit/ba3efe6ed3947561da61d16753cf830181014443))


## v0.5.0 (2026-05-03)

### Features

- Add context7 MCP proxy, because their cert can cause problems with envoy
  ([`f6fe5c5`](https://github.com/thomasbuchinger/buc-mcp/commit/f6fe5c5c3f73551091ab9413798c0c3210bb1bf6))

- Add frontend-design and test-driven-development skills
  ([`0c4e266`](https://github.com/thomasbuchinger/buc-mcp/commit/0c4e26685eb4cb51f2107288122e0296960a8a76))

- Split MCP into multiple server paths for different features
  ([`de7f230`](https://github.com/thomasbuchinger/buc-mcp/commit/de7f230a81918096556d78f48ff116412b4e1f4c))


## v0.4.4 (2026-04-28)

### Bug Fixes

- Mcp-inspector deployment / proxy
  ([`f6bd40d`](https://github.com/thomasbuchinger/buc-mcp/commit/f6bd40ddbccdc04d194bd816c3b8ee1190cd9adb))

- Mcp-inspector deployment / proxy
  ([`d943c97`](https://github.com/thomasbuchinger/buc-mcp/commit/d943c97d994abca9ab852eda3e93cfc38b87afd0))


## v0.4.3 (2026-04-28)

### Bug Fixes

- Mcp-inspector deployment / env vars
  ([`2097cf1`](https://github.com/thomasbuchinger/buc-mcp/commit/2097cf1c716224d31d83ac3120c7b269843de04e))


## v0.4.2 (2026-04-28)

### Bug Fixes

- Mcp-inspector deployment / uids
  ([`b34e0b5`](https://github.com/thomasbuchinger/buc-mcp/commit/b34e0b5f2aee0410c296614b3e0ff7a27f33043a))


## v0.4.1 (2026-04-28)

### Bug Fixes

- Mcp-inspector deployment
  ([`2dfe45b`](https://github.com/thomasbuchinger/buc-mcp/commit/2dfe45bee2007c5e2c92818d822a0db9a9811ad7))


## v0.4.0 (2026-04-28)

### Features

- Add mcp-inspactor to deployment
  ([`9747ad5`](https://github.com/thomasbuchinger/buc-mcp/commit/9747ad5252e1687bf515f261ef51535c0b47735f))


## v0.3.0 (2026-04-28)

### Features

- Add swe skills as prompts
  ([`a559127`](https://github.com/thomasbuchinger/buc-mcp/commit/a559127e42fad5fa2df030b2a8f1cff136565e64))


## v0.2.6 (2026-04-21)

### Bug Fixes

- Link skills with prompt, since clients don't support it yet
  ([`56b1e29`](https://github.com/thomasbuchinger/buc-mcp/commit/56b1e29b3defda1d9c45eb46821f92c7427548cd))

- Test fail after prompt rename
  ([`b70f6fb`](https://github.com/thomasbuchinger/buc-mcp/commit/b70f6fb3a8d3c8be46ea24e7fc4462329d6e28b7))


## v0.2.5 (2026-04-20)

### Bug Fixes

- Add placeholder tool
  ([`22aac17`](https://github.com/thomasbuchinger/buc-mcp/commit/22aac171923647f5007fad341d003c08bde2d648))


## v0.2.4 (2026-04-20)

### Bug Fixes

- Remove stateless-mode to better support clients
  ([`6cbc865`](https://github.com/thomasbuchinger/buc-mcp/commit/6cbc8653bfc8a5620f234120e70f9a364230297a))


## v0.2.3 (2026-04-20)

### Bug Fixes

- Set resource limits
  ([`bf836d3`](https://github.com/thomasbuchinger/buc-mcp/commit/bf836d3628e6448353c4b77fe7c443343565c58a))


## v0.2.2 (2026-04-20)

### Bug Fixes

- Run container as non-root
  ([`4fd86b1`](https://github.com/thomasbuchinger/buc-mcp/commit/4fd86b1957410098c8fbfff2d23b9bb2198a07bb))


## v0.2.1 (2026-04-20)

### Bug Fixes

- Run container as non-root
  ([`2d626e9`](https://github.com/thomasbuchinger/buc-mcp/commit/2d626e9a9c7cff38c0645397a51ad70f9c83f419))


## v0.2.0 (2026-04-20)

### Features

- Add kubernetes-yaml skill
  ([`e7a2eaa`](https://github.com/thomasbuchinger/buc-mcp/commit/e7a2eaa0c8d1e4ab330ba196b47cd2c455e8e24a))


## v0.1.1 (2026-04-19)

### Bug Fixes

- Change example-prompt to test the build pipeline
  ([`dd18b51`](https://github.com/thomasbuchinger/buc-mcp/commit/dd18b5179c903f83a4dae7cd4eab63fc64ffee7f))

### Continuous Integration

- Add changelog based on semantic commits
  ([`bc2daeb`](https://github.com/thomasbuchinger/buc-mcp/commit/bc2daebe5520b7dbb23e50cf5a4d0f94ff02fa49))


## v0.1.0 (2026-04-19)

- Initial Release
