# Agents Catalog — Portable Setup

All agents are defined in `.opencode/agents/` + `.opencode/opencode.jsonc`. Copy both to any PC.

## Setup on New PC

```bash
git clone <repo> && cd hoverboard-ros-ws
# Option A: project-scoped (auto-picked up by OpenCode)
# .opencode/opencode.jsonc is already in repo — just restart OpenCode

# Option B: also install as global default
cp .opencode/opencode.jsonc ~/.config/opencode/opencode.jsonc
cp .opencode/agents/*.md ~/.config/opencode/agent/
# Restart OpenCode
```

## Primary Agents (Tab-switchable)

| Agent | File | Model | Temp | Purpose | Invoke |
|-------|------|-------|------|---------|--------|
| **session-maintainer** | `.opencode/agents/session-maintainer.md` | `opencode/nemotron-3.5-lightning-free` | 0.3 | Project work + docs + opt-in GitHub commits | default |
| **brainstorm** | `.opencode/agents/brainstorm.md` | `opencode/nemotron-3-ultra-free` | 0.8 | Creative ideation, read-only + web search, summary for Build | Tab / `@brainstorm` |
| **branch-diff-analyzer** | `.opencode/agents/branch-diff-analyzer.md` | `opencode/muse-spark-1.2-contributor-free` | 0.1 | Diff two branches, explain how each file acts now | Tab / prompt "compare branches" |
| **brutal-critique-panel** | `.opencode/agents/brutal-critique-panel.md` | `opencode/nemotron-3-ultra-free` | 0.0 | 4 roasting judges, simple plans, P0/P1/P2 roadmap | Tab / prompt "review environment" |

`mode: all` on brainstorm means it works as primary (Tab) **and** subagent (`@brainstorm` from Plan).

## Subagents (invoked via Task or @mention)

| Agent | File | Mode | Purpose |
|-------|------|------|---------|
| **embedded-serial-agent** | `.opencode/agents/embedded-serial-agent.md` | subagent | ESP32/ESP8266 firmware, UART, GPIO, baud |
| **ros-control-agent** | `.opencode/agents/ros-control-agent.md` | subagent | ROS 2 nodes, topics, safety overrides, locks |
| **integration-ops-agent** | `.opencode/agents/integration-ops-agent.md` | subagent | Launch files, colcon builds, hotspot, docs |
| **ui-frontend-agent** | `.opencode/agents/ui-frontend-agent.md` | subagent | Flask web controllers, Electron Eilik UI |

Subagents inherit the invoking primary's model unless they have their own `model:` field (currently they don't — intentional).

## Built-ins (not in repo, defined in global config)

| Agent | Model | Temp | Config |
|-------|-------|------|--------|
| **plan** | `opencode/nemotron-3-ultra-free` | default (0.0) | `~/.config/opencode/opencode.jsonc:plan` |
| **build** | `opencode/muse-spark-1.2-contributor-free` | 0.1 | `~/.config/opencode/opencode.jsonc:build` |

Plan/Build are global — not committed. Copy `~/.config/opencode/opencode.jsonc` to sync them.

## Global Config

`~/.config/opencode/opencode.jsonc` pins models/temps for `plan`, `build`, `session-maintainer`, `brainstorm`. The project copy `.opencode/opencode.jsonc` mirrors this for portability.

## Verify

```bash
opencode models | grep -E "muse-spark|nemotron"
ls .opencode/agents/
cat .opencode/opencode.jsonc
```
