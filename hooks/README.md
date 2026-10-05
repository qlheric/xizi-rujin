# hooks（可选 bootstrap 注入）

Claude Code / Codex / opencode 的 `skills/` 目录机制本身是「自动发现 + 按 description 触发」，
无需额外 hook。`hooks/` 目录保留给以下可选增强：

- 在全局指令里加一行触发提示，让 agent 更主动判断是否该压缩（而非等用户显式写 `/xizi`）。
  - Claude Code：在 `~/.claude/CLAUDE.md` 追加一行：
    `- 中文回复若用户在意 token 成本，可用「惜字如金」skill（/xizi）压缩。`
  - Codex：在 `~/.codex/AGENTS.md` 追加同义一行。

> 目前 SKILL.md 的 `description` 已写清触发条件，多数场景无需 bootstrap；此目录为扩展预留。
