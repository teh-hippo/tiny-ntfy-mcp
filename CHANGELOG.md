# CHANGELOG


## v2.0.12 (2026-05-04)

### Build System

- **deps**: Upgrade
  ([`6eeb8eb`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/6eeb8eb68fe86d7875a70100bb1ec4bda10b2965))


## v2.0.11 (2026-05-04)

### Bug Fixes

- Keep stdin open in stdio test to survive mcp>=1.27.0 transport-close cancel
  ([`be334dc`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/be334dca5711f8c578d06801a7ae158650e49a3f))

### Testing

- Signal tools/list response via Event to avoid reader-thread race
  ([`bf23522`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/bf2352244d870f2908cf68f65d0827fde31a8729))


## v2.0.10 (2026-04-26)

### Build System

- **deps**: Update astral-sh/setup-uv action to v8
  ([`3d3ebde`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/3d3ebdeb5d99a8fffddd2622bf5f5e4dd10bcb9e))

- **deps**: Update softprops/action-gh-release action to v3
  ([`a5f909c`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/a5f909c01ea2a69050b38a7fd648c2e122a65abb))

- **deps**: Upgrade
  ([`55b28c9`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/55b28c9e29962eb5f32f8aced74adbd97d098c78))


## v2.0.9 (2026-04-14)

### Build System

- **deps**: Update dependency pytest to v9.0.3 [SECURITY]
  ([`5126d0d`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/5126d0d464a6d28607362eaa786b50cbdf601fd9))


## v2.0.8 (2026-04-05)

### Build System

- **deps**: Upgrade
  ([`fdba4da`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/fdba4dae2620d5a10aef58b1c11e2de17377947d))


## v2.0.7 (2026-04-05)

### Build System

- Update Renovate config for weekly grouped updates
  ([`3c1ff8b`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/3c1ff8b060e45c362e2d62aa110167f367b35695))


## v2.0.6 (2026-03-30)

### Build System

- **deps**: Upgrade
  ([`003a99d`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/003a99dd9510faeae5385e4a2df7d7a0d4185487))


## v2.0.5 (2026-03-30)

### Build System

- **deps**: Upgrade
  ([`a4ea9b4`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/a4ea9b4e7922fec28a40d96f45a5d0d386a2ce49))


## v2.0.4 (2026-03-30)

### Build System

- **deps**: Upgrade
  ([`8718360`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/8718360918bd23f28f635834eb8b146990043382))


## v2.0.3 (2026-03-30)

### Build System

- **deps**: Upgrade
  ([`43a0790`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/43a07904c41f79bf4531347f2fbba3b824ba7074))

### Continuous Integration

- Enable global automerge and fix semantic-release patch_tags
  ([`1094f7a`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/1094f7ae7a4ba4d91662bd1944ffe73607c7bd9e))


## v2.0.2 (2026-03-24)

### Bug Fixes

- Version strings, jsonschema dep, robust shutdown
  ([`11d5eb5`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/11d5eb5679d0f8a1ee9645583c7d3fe83498bad9))

### Build System

- **deps**: Update dependency uv_build to >=0.11.0,<0.12.0
  ([`0c4791c`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/0c4791cdfadd0953eda9cbd8cf9c268360bfa858))


## v2.0.1 (2026-03-23)

### Bug Fixes

- **ci**: Move build from patch_tags to other_allowed_tags
  ([`37adaf6`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/37adaf6a540e63cd6c3a335f900cc4efb28076ed))

- **ci**: Pass RELEASE_TOKEN to checkout for git push auth
  ([`e5e1514`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/e5e1514cde3018a7ceeb450e09265be6582eeda2))

- **ci**: Use RELEASE_TOKEN for semantic-release push
  ([`fac3678`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/fac3678eb3c179da51e21f34fd70243979e1a0bf))

### Build System

- **deps**: Bump astral-sh/setup-uv from 6 to 7
  ([`294b5b2`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/294b5b24fd774a6be24e2ccc1acb7444020b3450))

- **deps**: Bump github/codeql-action from 3 to 4
  ([`0914614`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/0914614c17888948e68be00c8f44d25ecea904ab))

- **deps**: Update actions/checkout action to v6
  ([`297e010`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/297e0106c29df4f10dd2a0260ed4353808032575))

- **deps**: Update python Docker tag to v3.14
  ([`072ddc6`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/072ddc6a45cfdb626120fb87ac3106c630682362))

- **deps**: Upgrade
  ([`2e77134`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/2e77134b5e17ccf192563990ad4209b52003de4e))

### Continuous Integration

- Add Renovate configuration
  ([`8b4079e`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/8b4079ed29bc096faf58bc8d74a27ac92f5dcbf7))

- Remove dependabot-automerge workflow, Renovate handles automerge
  ([`9b2d7bc`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/9b2d7bc5e4570befa09a715fed737734365adc41))

- Remove dependabot.yml, replaced by Renovate
  ([`a4b59bb`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/a4b59bb840c631b66d3b0ab4f110b27c121f9c32))


## v2.0.0 (2026-02-26)

### Features

- Enrich attachment and action descriptions to guide agent usage
  ([`ffc8d17`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/ffc8d171d167af38ed8ffd970776b225ac57e537))

- Remove all filesystem I/O; config via env vars only
  ([`1abae24`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/1abae24ec20817b35e6fc274f0c80f9da6f55e83))


## v1.0.4 (2026-02-26)

### Bug Fixes

- Format server for CI
  ([`e399533`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/e3995336e09bab3e059994e3c1561e7fdf83c6f0))

- Rewrite MCP notifications to ntfy_me/ntfy_off
  ([`ee8b691`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/ee8b69148e9c51b419a88c88c1a79c566ff3052d))

### Continuous Integration

- Keep latest tag aligned with stable release
  ([`577ecae`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/577ecae52db6d327661da4aa3e6aa3c5e9e9da8d))

- Publish latest release alias
  ([`3d8bde7`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/3d8bde7beff4719d7b56ecbfa9f092972c3b0072))


## v1.0.3 (2026-02-25)

### Bug Fixes

- Use underscore MCP tool names
  ([`7aa0bc4`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/7aa0bc498790d857bf064b70c36a0f9f1a59acc9))

### Chores

- Prepare v1.0.3 release
  ([`d3e7520`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/d3e7520057233a4b6ecfb3b1bb41b8fa21ec5b45))


## v1.0.2 (2026-02-24)

### Bug Fixes

- Make tool schemas object-only
  ([`005cce7`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/005cce75b1546652bbfb1392f658c64da1dbe35c))

### Documentation

- Fix Copilot MCP config path
  ([`129f193`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/129f193f502bf416f0cca225528b7c551f500900))


## v1.0.1 (2026-02-24)

### Bug Fixes

- Include ntfy_mcp in build
  ([`d135518`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/d1355186ff50233eaf11f1ae5d65c72184596d18))

### Chores

- Update uv.lock
  ([`65e9271`](https://github.com/teh-hippo/tiny-ntfy-mcp/commit/65e927197824aa7b4b6a6f271ae7c7b3e83ba565))


## v1.0.0 (2026-02-24)

- Initial Release
