# Reference Project Study Plan

Date: 2026-07-14

## Purpose

This document defines how to study mature coding-agent projects before writing
SafeSWE-Lite's `SPEC.md` and `PLAN.md`.

The goal is not to copy implementations. The goal is to build a clear mental
model of existing coding-agent architecture, then choose a course-sized design
that satisfies AI4SE A-class harness requirements:

- self-implemented agent loop
- mockable LLM abstraction
- deterministic tool dispatch
- deterministic guardrails
- test-feedback loop
- minimum memory and config support
- CI/CD, Docker distribution, and online WebUI inspection

All reference repositories are kept outside this repository at:

```text
D:\SophemoreYearSummerVacation\智能软件 工程师\agent-references\
```

Do not copy their source files into `safe-swe-lite`.

## Downloaded Reference Repositories

| Project | Local Path | Role in This Project |
|---|---|---|
| mini-SWE-agent | `..\agent-references\mini-swe-agent` | Main minimal architecture reference |
| SWE-agent | `..\agent-references\SWE-agent` | Full harness reference for parser, guardrail, history, trajectory |
| Aider | `..\agent-references\aider` | Feedback loop and edit-validation reference |
| AutoCodeRover | `..\agent-references\auto-code-rover` | Context localization before patching |
| Agentless | `..\agent-references\Agentless` | Non-agent pipeline as design contrast |

## Study Principles

1. Read with questions, not curiosity alone.
2. Focus on mechanisms that map to course requirements.
3. Record design lessons in our own words.
4. Prefer small reproducible mechanisms over broad feature lists.
5. Do not copy code. Borrow architecture, terminology, and test strategy.

## Reading Order

### 1. mini-SWE-agent: Understand the Smallest Useful Harness

Why first:

mini-SWE-agent is the closest reference to our desired project scale. It is
small enough to understand before building, while still representing the
SWE-agent family.

Read these files first:

```text
..\agent-references\mini-swe-agent\README.md
..\agent-references\mini-swe-agent\src\minisweagent\agents\
..\agent-references\mini-swe-agent\src\minisweagent\models\
..\agent-references\mini-swe-agent\src\minisweagent\environments\
..\agent-references\mini-swe-agent\tests\models\
```

Questions to answer:

- Where is the agent loop?
- How is the model interface separated from the agent?
- How are actions represented?
- What does the environment execute?
- How do deterministic test models work?
- Which parts are too minimal for our course requirements?

What SafeSWE-Lite should borrow:

- simple agent/model/environment separation
- small and readable agent loop
- mock model testing style
- trace-oriented execution

What SafeSWE-Lite should not borrow blindly:

- relying mostly on one powerful shell tool
- thin or absent deterministic guardrails
- limited memory/config story

Expected output:

Add notes to `reference_projects_analysis.md` or `SPEC_PROCESS.md` explaining
the minimal harness architecture we will use.

### 2. SWE-agent: Study the Full System for Mechanism Ideas

Why second:

Full SWE-agent is larger and more complex. It is best used as a mechanism
catalog, not as something to replicate.

Read these files/directories:

```text
..\agent-references\SWE-agent\README.md
..\agent-references\SWE-agent\sweagent\agent\
..\agent-references\SWE-agent\sweagent\tools\
..\agent-references\SWE-agent\sweagent\tools\parsing.py
..\agent-references\SWE-agent\sweagent\environment\
..\agent-references\SWE-agent\config\
..\agent-references\SWE-agent\tests\test_parsing.py
..\agent-references\SWE-agent\tests\test_history_processors.py
..\agent-references\SWE-agent\tests\test_tools_command_parsing.py
```

Questions to answer:

- How does SWE-agent parse actions?
- How does it decide whether an action is blocked?
- How are observations added back to history?
- What goes into trajectory files?
- Which settings live in YAML config?
- How does the test suite isolate parser/history/tool behavior?

What SafeSWE-Lite should borrow:

- action parsing as a separate unit
- trajectory/trace as a first-class artifact
- config-driven safety policy
- history processing as a testable module

What SafeSWE-Lite should improve for course purposes:

- make guardrails more explicit and layered
- expose guardrail decisions in WebUI
- implement mock-LLM mechanism demos as first-class tests

Expected output:

In `SPEC.md`, include a "Domain and Mechanism Design" section that states how
SafeSWE-Lite's guardrails differ from SWE-agent's blocklist approach.

### 3. Aider: Study Feedback After Edits

Why third:

Aider is not the same kind of harness, but it is strong at the edit -> lint/test
-> feedback -> retry loop. This is directly relevant to our secondary deep
mechanism.

Read these files/directories:

```text
..\agent-references\aider\README.md
..\agent-references\aider\aider\main.py
..\agent-references\aider\aider\commands.py
..\agent-references\aider\aider\linter.py
..\agent-references\aider\aider\repo.py
..\agent-references\aider\aider\history.py
..\agent-references\aider\tests\
```

Questions to answer:

- When does Aider run lint or test validation?
- How are failures presented back to the model/user?
- How does it limit retry loops?
- How does it track edited files?
- Which parts are product features rather than harness mechanisms?

What SafeSWE-Lite should borrow:

- validation after edits
- bounded retry loop, such as max 3 attempts
- clear failure summaries
- edited-file tracking

What SafeSWE-Lite should not borrow:

- full interactive chat product complexity
- broad model/provider support
- repo map complexity in the first version

Expected output:

In `SPEC.md`, define the feedback loop as:

```text
write action -> validator chain -> observation -> next agent step
```

with a bounded retry count.

### 4. AutoCodeRover: Study Context Localization

Why fourth:

AutoCodeRover is useful for one idea: a coding agent should not blindly load
the whole repository. It should localize relevant context before patching.

Read these files/directories:

```text
..\agent-references\auto-code-rover\README.md
..\agent-references\auto-code-rover\ACR.py
..\agent-references\auto-code-rover\app\search\
..\agent-references\auto-code-rover\app\agents\
..\agent-references\auto-code-rover\test\app\search\
..\agent-references\auto-code-rover\test\app\agents\
```

Questions to answer:

- What are the stages before writing a patch?
- How does the project search or localize code?
- Which search tools are simple enough for SafeSWE-Lite?
- What should be out of scope for a course-sized harness?

What SafeSWE-Lite should borrow:

- localization before patching as a design principle
- simple `list_files`, `search_text`, and `read_file` tools
- the idea that context selection is a mechanism, not just a prompt

What SafeSWE-Lite should not borrow:

- full SWE-bench pipeline
- heavy benchmark infrastructure
- multi-agent search/review orchestration

Expected output:

In `SPEC.md`, define context tools as minimal but explicit:

```text
list_files -> search_text -> read_file -> write_file -> run_tests
```

### 5. Agentless: Study the Non-Agent Counterpoint

Why fifth:

Agentless is useful because it argues that many software repair tasks can be
handled by structured localization, repair, and validation pipelines without a
fully autonomous multi-turn agent.

Read these files/directories:

```text
..\agent-references\Agentless\README.md
..\agent-references\Agentless\agentless\fl\
..\agent-references\Agentless\agentless\repair\
..\agent-references\Agentless\agentless\test\
..\agent-references\Agentless\get_repo_structure\
```

Questions to answer:

- How does Agentless split localization, repair, and validation?
- What does this project do deterministically instead of agentically?
- Which parts should SafeSWE-Lite keep deterministic?
- How can this become a reflection point in `REFLECTION.md`?

What SafeSWE-Lite should borrow:

- staged thinking: localization -> repair -> validation
- deterministic validation as a core signal
- skepticism toward giving the LLM too much freedom

What SafeSWE-Lite should not borrow:

- abandoning the agent loop, because A-class requires a harness main loop
- large benchmark scripts

Expected output:

In `REFLECTION.md`, compare the chosen harness design against Agentless and
explain why this course project still implements an agent loop.

## Cross-Project Mechanism Matrix

Use this table while reading.

| Mechanism | mini-SWE-agent | SWE-agent | Aider | AutoCodeRover | Agentless | SafeSWE-Lite Decision |
|---|---|---|---|---|---|---|
| Agent loop | Minimal | Full | Chat/edit oriented | Multi-stage agents | Mostly pipeline | Implement our own minimal loop |
| LLM abstraction | Yes | Yes | Yes | Yes | Yes | Mock + OpenAI-compatible provider |
| Action protocol | Tool call / text | Multiple parsers | Edit formats | Search/patch stages | Pipeline calls | JSON Action Protocol |
| Tool dispatch | Environment shell | Environment + tools | File edits / commands | Search + patch agents | Scripts | Explicit dispatcher |
| Guardrail | Thin | Blocklist/filter | Git safety/undo | Limited | Pipeline control | Main contribution: layered guardrail |
| Feedback | Observation | Observation/history | Lint/test retry | Validation | Test validation | Secondary: validator chain |
| Memory/context | Message history | history processors | repo map/history | localization | repo structure | Minimum memory + compaction |
| Config | Config files | YAML | CLI/config | many configs | scripts | YAML config with policy |
| Testing | deterministic models | parser/history tests | broad tests | search/agent tests | pipeline tests | mock LLM mechanism demos |

## Study Schedule

Recommended three-day study sprint before implementation:

```text
Day 1 morning: mini-SWE-agent agent loop and model tests
Day 1 afternoon: SWE-agent parser, guardrail, history, config

Day 2 morning: Aider lint/test feedback and retry behavior
Day 2 afternoon: AutoCodeRover search/localization flow

Day 3 morning: Agentless localization/repair/validation pipeline
Day 3 afternoon: update SPEC.md and PLAN.md with final design decisions
```

If time is tight:

```text
Must read:
  mini-SWE-agent agent/model/environment
  SWE-agent parsing/guardrail/history
  Aider linter/test feedback

Skim:
  AutoCodeRover search
  Agentless pipeline
```

## Questions to Answer Before Writing SPEC.md

1. What is the exact action JSON schema?
2. Which actions are allowed in v1?
3. Which actions are denied, allowed, or require HITL approval?
4. How does a blocked action appear in the trace?
5. What validators run after a write action?
6. How many feedback retry rounds are allowed?
7. What data is persisted as memory?
8. What configuration belongs in YAML?
9. Which mechanism demos will be implemented as tests?
10. What does the WebUI show when running mock demos?

## Concrete SafeSWE-Lite Scope After Study

The reference study should converge on this scope:

```text
Main contribution:
  layered deterministic guardrails

Secondary contribution:
  validator-driven feedback loop

Minimum supporting mechanisms:
  JSON action protocol
  tool dispatcher
  mockable LLM abstraction
  memory store
  YAML config
  CLI
  WebUI mock demo
  GitHub Actions CI
  Docker deployment
```

## Notes for Academic Integrity

- Do not copy source code from reference projects.
- Cite reference projects in README and `REFLECTION.md`.
- If a design idea is strongly inspired by a project, say so explicitly.
- Keep reference repositories outside this project repository.
- The submitted harness core must be our own implementation.

