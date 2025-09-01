# Метод BMad - руководство пользователя

Это руководство поможет вам понять и эффективно использовать метод BMad для гибкого планирования и разработки на основе ИИ.

## Рабочий процесс BMad Plan and Execute

Во-первых, здесь представлен полный стандартный рабочий процесс планирования и реализации Greenfield. Brownfield очень похож, но рекомендуется сначала разобраться с greenfield, пусть даже на простом проекте, прежде чем браться за brownfield. Метод BMad необходимо установить в корень папки нового проекта. Для фазы планирования можно использовать мощные веб-агенты, что потенциально приведет к получению результатов более высокого качества за меньшую стоимость, чем если бы вы предоставили свой собственный API-ключ или кредиты в некоторых инструментах Agentic. Для планирования наилучшие результаты дают мощные модели мышления и более широкий контекст, а также работа с агентами в качестве партнера.

Если вы собираетесь использовать метод BMad в проекте Brownfield (существующий проект), изучите**[Working in the Brownfield](./working-in-the-brownfield.md)**.

Если диаграммы ниже не отображаются, установите Markdown All in One вместе с плагинами Markdown Preview Mermaid Support в VSCode (или один из форкнутых клонов). С этими плагинами, если вы щелкните правой кнопкой мыши на открытой вкладке, должна появиться опция Open Preview, или проверьте документацию IDE.
### Рабочий процесс планирования (веб-интерфейс или мощные агенты IDE)

Перед началом разработки BMad следует структурированному процессу планирования, который в идеале выполняется в веб-интерфейсе для экономичности:

```mermaid
graph TD
    A["Start: Project Idea"] --> B{"Optional: Analyst Research"}
    B -->|Yes| C["Analyst: Brainstorming (Optional)"]
    B -->|No| G{"Project Brief Available?"}
    C --> C2["Analyst: Market Research (Optional)"]
    C2 --> C3["Analyst: Competitor Analysis (Optional)"]
    C3 --> D["Analyst: Create Project Brief"]
    D --> G
    G -->|Yes| E["PM: Create PRD from Brief (Fast Track)"]
    G -->|No| E2["PM: Interactive PRD Creation (More Questions)"]
    E --> F["PRD Created with FRs, NFRs, Epics & Stories"]
    E2 --> F
    F --> F2{"UX Required?"}
    F2 -->|Yes| F3["UX Expert: Create Front End Spec"]
    F2 -->|No| H["Architect: Create Architecture from PRD"]
    F3 --> F4["UX Expert: Generate UI Prompt for Lovable/V0 (Optional)"]
    F4 --> H2["Architect: Create Architecture from PRD + UX Spec"]
    H --> Q{"Early Test Strategy? (Optional)"}
    H2 --> Q
    Q -->|Yes| R["QA: Early Test Architecture Input on High-Risk Areas"]
    Q -->|No| I
    R --> I["PO: Run Master Checklist"]
    I --> J{"Documents Aligned?"}
    J -->|Yes| K["Planning Complete"]
    J -->|No| L["PO: Update Epics & Stories"]
    L --> M["Update PRD/Architecture as needed"]
    M --> I
    K --> N["📁 Switch to IDE (If in a Web Agent Platform)"]
    N --> O["PO: Shard Documents"]
    O --> P["Ready for SM/Dev Cycle"]

    style A fill:#f5f5f5,color:#000
    style B fill:#e3f2fd,color:#000
    style C fill:#e8f5e9,color:#000
    style C2 fill:#e8f5e9,color:#000
    style C3 fill:#e8f5e9,color:#000
    style D fill:#e8f5e9,color:#000
    style E fill:#fff3e0,color:#000
    style E2 fill:#fff3e0,color:#000
    style F fill:#fff3e0,color:#000
    style F2 fill:#e3f2fd,color:#000
    style F3 fill:#e1f5fe,color:#000
    style F4 fill:#e1f5fe,color:#000
    style G fill:#e3f2fd,color:#000
    style H fill:#f3e5f5,color:#000
    style H2 fill:#f3e5f5,color:#000
    style Q fill:#e3f2fd,color:#000
    style R fill:#ffd54f,color:#000
    style I fill:#f9ab00,color:#fff
    style J fill:#e3f2fd,color:#000
    style K fill:#34a853,color:#fff
    style L fill:#f9ab00,color:#fff
    style M fill:#fff3e0,color:#000
    style N fill:#1a73e8,color:#fff
    style O fill:#f9ab00,color:#fff
    style P fill:#34a853,color:#fff
```

#### Переход от веб-интерфейса к IDE

**Критическая точка перехода**: Как только PO подтвердит согласование документов, вы должны переключиться с веб-интерфейса на IDE, чтобы начать рабочий процесс разработки:

1. **Копирование документов в проект**: Убедитесь, что `docs/prd.md` и `docs/architecture.md` находятся в папке docs вашего проекта (или в другом месте, которое вы можете указать во время установки).
2. **Переключитесь на IDE**: Откройте проект в выбранной вами IDE Agentic.
3. **Разделение документов**: С помощью агента PO разделите PRD, а затем архитектуру.
4. **Начать разработку**: Запустите основной цикл разработки, который следует за

#### Артефакты планирования (стандартные пути)
```text
PRD              → docs/prd.md
Architecture     → docs/architecture.md
Sharded Epics    → docs/epics/
Sharded Stories  → docs/stories/
QA Assessments   → docs/qa/assessments/
QA Gates         → docs/qa/gates/
```

### Основной цикл разработки (IDE)

После завершения планирования и разделения документов BMad следует структурированному рабочему процессу разработки:

```mermaid
graph TD
    A["Начало фазы разработки"] --> B["SM: Рецензии предыдущих этапов,  Dev/QA Заметки"]
    B --> B2["SM: Черновик следующей истории из «Sharded Этап + Architecture»"]
    B2 --> S{"High-Risk Story? (Optional)"}
    S -->|Yes| T["QA: *risk + *design on Draft Story"]
    S -->|No| B3
    T --> U["Test Strategy & Risk Profile Created"]
    U --> B3{"PO: Проверить черновик этапа (необязательно)"}
    B3 -->|Validation Requested| B4["PO: Проверка этапа по артефактам"]
    B3 -->|Skip Validation| C{"Согласие пользователя"}
    B4 --> C
    C -->|Approved| D["Dev: Последовательное выполнение задач"]
    C -->|Needs Changes| B2
    D --> E["Dev: Реализация задач + тесты"]
    E --> V{"Проверка QA в середине разработки? (Необязательно)"}
    V -->|Yes| W["QA: *trace или *nfr для ранней проверки"]
    V -->|No| F
    W --> X["Dev: Устранение пробелов в Coverage/NFR"]
    X --> F["Dev: Выполнить все проверки"]
    F --> G["Dev: Пометить как готовое к проверке + добавить примечания"]
    G --> H{"Проверка пользователем"}
    H -->|Request QA Review| I["QA: Test Architect Review + Quality Gate"]
    H -->|Approve Without QA| M["ВАЖНО: Убедитесь, что все регрессионные тесты и линтинг пройдены"]
    I --> J["QA: Test Architecture Analysis + Active Refactoring"]
    J --> L{"QA Решение"}
    L -->|Needs Dev Work| D
    L -->|Approved| M
    H -->|Needs Fixes| D
    M --> N["ВАЖНО: СОХРАНИТЕ ИЗМЕНЕНИЯ ПЕРЕД ПРОДОЛЖЕНИЕМ!"]
    N --> Y{" Требуется обновление Gate?"}
    Y -->|Yes| Z["QA: *gate обновить статус"]
    Y -->|No| K
    Z --> K["Пометить историю как законченную"]
    K --> B

    style A fill:#f5f5f5,color:#000
    style B fill:#e8f5e9,color:#000
    style B2 fill:#e8f5e9,color:#000
    style S fill:#e3f2fd,color:#000
    style T fill:#ffd54f,color:#000
    style U fill:#ffd54f,color:#000
    style B3 fill:#e3f2fd,color:#000
    style B4 fill:#fce4ec,color:#000
    style C fill:#e3f2fd,color:#000
    style D fill:#e3f2fd,color:#000
    style E fill:#e3f2fd,color:#000
    style V fill:#e3f2fd,color:#000
    style W fill:#ffd54f,color:#000
    style X fill:#e3f2fd,color:#000
    style F fill:#e3f2fd,color:#000
    style G fill:#e3f2fd,color:#000
    style H fill:#e3f2fd,color:#000
    style I fill:#f9ab00,color:#fff
    style J fill:#ffd54f,color:#000
    style K fill:#34a853,color:#fff
    style L fill:#e3f2fd,color:#000
    style M fill:#ff5722,color:#fff
    style N fill:#d32f2f,color:#fff
    style Y fill:#e3f2fd,color:#000
    style Z fill:#ffd54f,color:#000
```

## Предварительные условия

Перед установкой BMad Method убедитесь, что у вас есть:

- **Node.js** ≥ 18, **npm** ≥ 9
- **Git** установлен и настроен
- **(Optional)** VS Code with "Markdown All in One" + "Markdown Preview Mermaid Support" extensions

## Installation

### Optional

If you want to do the planning on the web with Claude (Sonnet 4 or Opus), Gemini Gem (2.5 Pro), or Custom GPTs:

1. Navigate to `dist/teams/`
2. Copy `team-fullstack.txt`
3. Create new Gemini Gem or CustomGPT
4. Upload file with instructions: "Your critical operating instructions are attached, do not break character as directed"
5. Type `/help` to see available commands

### IDE Project Setup

```bash
# Interactive installation (recommended)
npx bmad-method install
```

## Special Agents

There are two BMad agents — in the future they'll be consolidated into a single BMad-Master.

### BMad-Master

This agent can do any task or command that all other agents can do, aside from actual story implementation. Additionally, this agent can help explain the BMad Method when on the web by accessing the knowledge base and explaining anything to you about the process.

If you don't want to bother switching between different agents aside from the dev, this is the agent for you. Just remember that as the context grows, the performance of the agent degrades, therefore it is important to instruct the agent to compact the conversation and start a new conversation with the compacted conversation as the initial message. Do this often, preferably after each story is implemented.

### BMad-Orchestrator

This agent should NOT be used within the IDE, it is a heavyweight, special-purpose agent that utilizes a lot of context and can morph into any other agent. This exists solely to facilitate the teams within the web bundles. If you use a web bundle you will be greeted by the BMad Orchestrator.

### How Agents Work

#### Dependencies System

Each agent has a YAML section that defines its dependencies:

```yaml
dependencies:
  templates:
    - prd-template.md
    - user-story-template.md
  tasks:
    - create-doc.md
    - shard-doc.md
  data:
    - bmad-kb.md
```

**Key Points:**

- Agents only load resources they need (lean context)
- Dependencies are automatically resolved during bundling
- Resources are shared across agents to maintain consistency

#### Agent Interaction

**In IDE:**

```bash
# Some IDEs, like Cursor or Windsurf for example, utilize manual rules so interaction is done with the '@' symbol
@pm Create a PRD for a task management app
@architect Design the system architecture
@dev Implement the user authentication

# Some IDEs, like Claude Code, use slash commands instead
/pm Create user stories
/dev Fix the login bug
```

#### Interactive Modes

- **Incremental Mode**: Step-by-step with user input
- **YOLO Mode**: Rapid generation with minimal interaction

## IDE Integration

### IDE Best Practices

- **Context Management**: Keep relevant files only in context, keep files as lean and focused as necessary
- **Agent Selection**: Use appropriate agent for task
- **Iterative Development**: Work in small, focused tasks
- **File Organization**: Maintain clean project structure
- **Commit Regularly**: Save your work frequently

## The Test Architect (QA Agent)

### Overview

The QA agent in BMad is not just a "senior developer reviewer" - it's a **Test Architect** with deep expertise in test strategy, quality gates, and risk-based testing. Named Quinn, this agent provides advisory authority on quality matters while actively improving code when safe to do so.

#### Quick Start (Essential Commands)

```bash
@qa *risk {story}       # Assess risks before development
@qa *design {story}     # Create test strategy
@qa *trace {story}      # Verify test coverage during dev
@qa *nfr {story}        # Check quality attributes
@qa *review {story}     # Full assessment → writes gate
```

#### Command Aliases (Test Architect)

The documentation uses short forms for convenience. Both styles are valid:

```text
*risk    → *risk-profile
*design  → *test-design
*nfr     → *nfr-assess
*trace   → *trace-requirements (or just *trace)
*review  → *review
*gate    → *gate
```

### Core Capabilities

#### 1. Risk Profiling (`*risk`)

**When:** After story draft, before development begins (earliest intervention point)

Identifies and assesses implementation risks:

- **Categories**: Technical, Security, Performance, Data, Business, Operational
- **Scoring**: Probability × Impact analysis (1-9 scale)
- **Mitigation**: Specific strategies for each identified risk
- **Gate Impact**: Risks ≥9 trigger FAIL, ≥6 trigger CONCERNS (see `tasks/risk-profile.md` for authoritative rules)

#### 2. Test Design (`*design`)

**When:** After story draft, before development begins (guides what tests to write)

Creates comprehensive test strategies including:

- Test scenarios for each acceptance criterion
- Appropriate test level recommendations (unit vs integration vs E2E)
- Risk-based prioritization (P0/P1/P2)
- Test data requirements and mock strategies
- Execution strategies for CI/CD integration

**Example output:**

```yaml
test_summary:
  total: 24
  by_level:
    unit: 15
    integration: 7
    e2e: 2
  by_priority:
    P0: 8 # Must have - linked to critical risks
    P1: 10 # Should have - medium risks
    P2: 6 # Nice to have - low risks
```

#### 3. Requirements Tracing (`*trace`)

**When:** During development (mid-implementation checkpoint)

Maps requirements to test coverage:

- Documents which tests validate each acceptance criterion
- Uses Given-When-Then for clarity (documentation only, not BDD code)
- Identifies coverage gaps with severity ratings
- Creates traceability matrix for audit purposes

#### 4. NFR Assessment (`*nfr`)

**When:** During development or early review (validate quality attributes)

Validates non-functional requirements:

- **Core Four**: Security, Performance, Reliability, Maintainability
- **Evidence-Based**: Looks for actual implementation proof
- **Gate Integration**: NFR failures directly impact quality gates

#### 5. Comprehensive Test Architecture Review (`*review`)

**When:** After development complete, story marked "Ready for Review"

When you run `@qa *review {story}`, Quinn performs:

- **Requirements Traceability**: Maps every acceptance criterion to its validating tests
- **Test Level Analysis**: Ensures appropriate testing at unit, integration, and E2E levels
- **Coverage Assessment**: Identifies gaps and redundant test coverage
- **Active Refactoring**: Improves code quality directly when safe
- **Quality Gate Decision**: Issues PASS/CONCERNS/FAIL status based on findings

#### 6. Quality Gates (`*gate`)

**When:** After review fixes or when gate status needs updating

Manages quality gate decisions:

- **Deterministic Rules**: Clear criteria for PASS/CONCERNS/FAIL
- **Parallel Authority**: QA owns gate files in `docs/qa/gates/`
- **Advisory Nature**: Provides recommendations, not blocks
- **Waiver Support**: Documents accepted risks when needed

**Note:** Gates are advisory; teams choose their quality bar. WAIVED requires reason, approver, and expiry date. See `templates/qa-gate-tmpl.yaml` for schema and `tasks/review-story.md` (gate rules) and `tasks/risk-profile.md` for scoring.

### Working with the Test Architect

#### Integration with BMad Workflow

The Test Architect provides value throughout the entire development lifecycle. Here's when and how to leverage each capability:

| **Stage**          | **Command** | **When to Use**         | **Value**                  | **Output**                                                     |
| ------------------ | ----------- | ----------------------- | -------------------------- | -------------------------------------------------------------- |
| **Story Drafting** | `*risk`     | After SM drafts story   | Identify pitfalls early    | `docs/qa/assessments/{epic}.{story}-risk-{YYYYMMDD}.md`        |
|                    | `*design`   | After risk assessment   | Guide dev on test strategy | `docs/qa/assessments/{epic}.{story}-test-design-{YYYYMMDD}.md` |
| **Development**    | `*trace`    | Mid-implementation      | Verify test coverage       | `docs/qa/assessments/{epic}.{story}-trace-{YYYYMMDD}.md`       |
|                    | `*nfr`      | While building features | Catch quality issues early | `docs/qa/assessments/{epic}.{story}-nfr-{YYYYMMDD}.md`         |
| **Review**         | `*review`   | Story marked complete   | Full quality assessment    | QA Results in story + gate file                                |
| **Post-Review**    | `*gate`     | After fixing issues     | Update quality decision    | Updated `docs/qa/gates/{epic}.{story}-{slug}.yml`              |

#### Example Commands

```bash
# Planning Stage - Run these BEFORE development starts
@qa *risk {draft-story}     # What could go wrong?
@qa *design {draft-story}   # What tests should we write?

# Development Stage - Run these DURING coding
@qa *trace {story}          # Are we testing everything?
@qa *nfr {story}            # Are we meeting quality standards?

# Review Stage - Run when development complete
@qa *review {story}         # Comprehensive assessment + refactoring

# Post-Review - Run after addressing issues
@qa *gate {story}           # Update gate status
```

### Quality Standards Enforced

Quinn enforces these test quality principles:

- **No Flaky Tests**: Ensures reliability through proper async handling
- **No Hard Waits**: Dynamic waiting strategies only
- **Stateless & Parallel-Safe**: Tests run independently
- **Self-Cleaning**: Tests manage their own test data
- **Appropriate Test Levels**: Unit for logic, integration for interactions, E2E for journeys
- **Explicit Assertions**: Keep assertions in tests, not helpers

### Gate Status Meanings

- **PASS**: All critical requirements met, no blocking issues
- **CONCERNS**: Non-critical issues found, team should review
- **FAIL**: Critical issues that should be addressed (security risks, missing P0 tests)
- **WAIVED**: Issues acknowledged but explicitly accepted by team

### Special Situations

**High-Risk Stories:**

- Always run `*risk` and `*design` before development starts
- Consider mid-development `*trace` and `*nfr` checkpoints

**Complex Integrations:**

- Run `*trace` during development to ensure all integration points tested
- Follow up with `*nfr` to validate performance across integrations

**Performance-Critical:**

- Run `*nfr` early and often during development
- Don't wait until review to discover performance issues

**Brownfield/Legacy Code:**

- Start with `*risk` to identify regression dangers
- Use `*review` with extra focus on backward compatibility

### Best Practices

- **Early Engagement**: Run `*design` and `*risk` during story drafting
- **Risk-Based Focus**: Let risk scores drive test prioritization
- **Iterative Improvement**: Use QA feedback to improve future stories
- **Gate Transparency**: Share gate decisions with the team
- **Continuous Learning**: QA documents patterns for team knowledge sharing
- **Brownfield Care**: Pay extra attention to regression risks in existing systems

### Output Paths Reference

Quick reference for where Test Architect outputs are stored:

```text
*risk-profile  → docs/qa/assessments/{epic}.{story}-risk-{YYYYMMDD}.md
*test-design   → docs/qa/assessments/{epic}.{story}-test-design-{YYYYMMDD}.md
*trace         → docs/qa/assessments/{epic}.{story}-trace-{YYYYMMDD}.md
*nfr-assess    → docs/qa/assessments/{epic}.{story}-nfr-{YYYYMMDD}.md
*review        → QA Results section in story + gate file reference
*gate          → docs/qa/gates/{epic}.{story}-{slug}.yml
```

## Technical Preferences System

BMad includes a personalization system through the `technical-preferences.md` file located in `.bmad-core/data/` - this can help bias the PM and Architect to recommend your preferences for design patterns, technology selection, or anything else you would like to put in here.

### Using with Web Bundles

When creating custom web bundles or uploading to AI platforms, include your `technical-preferences.md` content to ensure agents have your preferences from the start of any conversation.

## Core Configuration

The `bmad-core/core-config.yaml` file is a critical config that enables BMad to work seamlessly with differing project structures, more options will be made available in the future. Currently the most important is the devLoadAlwaysFiles list section in the yaml.

### Developer Context Files

Define which files the dev agent should always load:

```yaml
devLoadAlwaysFiles:
  - docs/architecture/coding-standards.md
  - docs/architecture/tech-stack.md
  - docs/architecture/project-structure.md
```

You will want to verify from sharding your architecture that these documents exist, that they are as lean as possible, and contain exactly the information you want your dev agent to ALWAYS load into its context. These are the rules the agent will follow.

As your project grows and the code starts to build consistent patterns, coding standards should be reduced to include only the standards the agent still needs enforced. The agent will look at surrounding code in files to infer the coding standards that are relevant to the current task.

## Getting Help

- **Discord Community**: [Join Discord](https://discord.gg/gk8jAdXWmj)
- **GitHub Issues**: [Report bugs](https://github.com/bmadcode/bmad-method/issues)
- **Documentation**: [Browse docs](https://github.com/bmadcode/bmad-method/docs)
- **YouTube**: [BMadCode Channel](https://www.youtube.com/@BMadCode)

## Conclusion

Remember: BMad is designed to enhance your development process, not replace your expertise. Use it as a powerful tool to accelerate your projects while maintaining control over design decisions and implementation details.
