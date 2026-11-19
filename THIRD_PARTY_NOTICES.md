# Sources and attribution

Capo (skill identifier: capo) is an independent Codex skill. It is not an official OpenAI or DeepSeek product and does not bundle a Codex runtime.

The coordination design was informed by source review of:

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), reviewed commit `2e39e70496aa02986ca6a820c5d497e816b69d7e`: instruction provenance, goal lifecycle, continuation and integration concepts. The reviewed repository carries an MIT license, copyright 2026 DeepSeek.
- [DSH Superagent Prototype](https://github.com/deepseek-ai/dsh-superagent-prototype), reviewed commit `8c32a9dc5d72c033816c6a8110b37f40cf94fba4`: task routing and separate delivery/acceptance concepts. The reviewed repository carries an MIT license, copyright 2026 DeepSeek Harness Team.

This release contains original coordination instructions and synthetic examples. It does not redistribute those repositories, their source files, the earlier upstream-based ticket CLI, screenshots, or private session transcripts. These are conceptual adaptations to the host's available tools, not a port of DeepSeek's runtime enforcement.

The project license is in [LICENSE](LICENSE). Future additions of upstream code must carry its applicable notices and identify the source and revision.
