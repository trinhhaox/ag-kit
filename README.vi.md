# AG Kit — Bộ Toolkit AI Agent cho Lập Trình Viên

Biến Claude Code và Gemini CLI thành một **đội kỹ sư hoàn chỉnh**. 20 agent chuyên biệt, 46 skill, 16 workflow — cài một lần, dùng mọi project.

```
Suy nghĩ → Lập kế hoạch → Xây dựng → Review → Test → Ship
```

## Tại sao nên dùng AG Kit?

Thay vì AI trợ lý chung chung, AG Kit cung cấp **agent chuyên biệt theo từng lĩnh vực**. Security auditor suy nghĩ như một chuyên gia bảo mật. Frontend specialist hiểu sâu React patterns. QA engineer sẽ cố gắng phá code của bạn.

**Ba nguyên tắc cốt lõi:**

- **Progressive disclosure** — skill chỉ load khi cần, không phí context window
- **Intelligent routing** — tự động phân loại request và chọn agent phù hợp
- **Quality hooks** — tự động chặn file nhạy cảm, kiểm tra chất lượng code sau mỗi lần edit

---

## Cài Đặt

### Yêu cầu

| Công cụ | Bắt buộc | Ghi chú |
|---------|---------|---------|
| **Claude Code** hoặc **Gemini CLI** | Co | Nền tảng AI chính |
| **Python 3.8+** | Co | Chạy validation scripts |
| **Git** | Co | Cho parallel conductor |
| **Playwright** | Tùy chọn | Cho browser daemon |
| **Gemini CLI / Codex CLI** | Tùy chọn | Cho cross-AI review |

### Cách 1: Cài cho Claude Code (Khuyến nghị)

**Bước 1 — Clone repo về máy:**

```bash
git clone https://github.com/trinhhaox/ag-kit.git ~/.antigravity/kit
```

**Bước 2 — Liên kết vào project:**

```bash
cd /path/to/project-cua-ban
ln -s ~/.antigravity/kit .agent
```

Lệnh này tạo symlink `.agent/` trong project trỏ đến AG Kit. Mọi project đều dùng chung một bản AG Kit.

**Bước 3 — Cài slash commands toàn cục (tùy chọn):**

```bash
mkdir -p ~/.claude/commands
cp ~/.antigravity/kit/workflows/*.md ~/.claude/commands/
```

Sau bước này, bạn có thể gõ `/plan`, `/create`, `/debug`... trong bất kỳ project nào.

**Bước 4 — Cấu hình hooks (khuyến nghị):**

Tạo file `.claude/settings.json` trong project:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write|Bash|Glob",
        "hooks": [{
          "type": "command",
          "command": "bash .agent/scripts/privacy-guard.sh",
          "timeout": 5000
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "bash .agent/scripts/quality-gate.sh",
          "timeout": 30000
        }]
      }
    ]
  }
}
```

**Hooks làm gì:**
- `privacy-guard.sh` — chặn truy cập file nhạy cảm (`.env`, `.pem`, credentials) + scope lock
- `quality-gate.sh` — kiểm tra cú pháp TypeScript, JSON, Python, Prisma sau mỗi lần sửa code

### Cách 2: Cài cho Gemini CLI

```bash
# Clone
git clone https://github.com/trinhhaox/ag-kit.git ~/.antigravity/kit

# Liên kết vào project
cd /path/to/project-cua-ban
ln -s ~/.antigravity/kit .agent

# Copy MCP config (sửa API keys theo nhu cầu)
mkdir -p ~/.gemini/antigravity
cp ~/.antigravity/kit/mcp_config.json ~/.gemini/antigravity/mcp_config.json
```

### Cập nhật AG Kit

```bash
cd ~/.antigravity/kit
git pull origin main
```

Vì dùng symlink nên mọi project tự động nhận bản mới.

### Gỡ cài đặt

```bash
# Xóa symlink trong project
rm /path/to/project/.agent

# Xóa AG Kit (nếu muốn)
rm -rf ~/.antigravity/kit

# Xóa slash commands
rm ~/.claude/commands/{plan,create,debug,test,deploy,enhance,orchestrate,brainstorm,preview,status,ui-ux-pro-max,freeze,unfreeze,browse,review-cross,conduct}.md
```

---

## Nội Dung Bộ Toolkit

### 20 Agent Chuyên Biệt

Mỗi agent là một "chuyên gia" với tính cách, kiến thức và cách tiếp cận riêng.

| Agent | Vai trò | Khi nào dùng |
|-------|---------|-------------|
| `orchestrator` | Điều phối đa agent | Task phức tạp cần nhiều chuyên gia |
| `project-planner` | Lập kế hoạch | Phân tích yêu cầu, chia task, tạo plan |
| `frontend-specialist` | Giao diện web | React, Next.js, Tailwind, responsive |
| `backend-specialist` | Server & API | Node.js, Python, REST, serverless |
| `database-architect` | Cơ sở dữ liệu | Schema, migrations, tối ưu query |
| `mobile-developer` | Ứng dụng di động | React Native, Flutter, đa nền tảng |
| `game-developer` | Phát triển game | Unity, Godot, web/mobile/VR |
| `devops-engineer` | Hạ tầng & triển khai | CI/CD, Docker, deployment |
| `security-auditor` | Bảo mật | OWASP 2025, zero trust, audit |
| `penetration-tester` | Pentest | Red team, khai thác lỗ hổng |
| `test-engineer` | Viết test | TDD, Jest, Vitest, chiến lược test |
| `qa-automation-engineer` | QA tự động | Playwright, Cypress, E2E |
| `debugger` | Sửa lỗi | Root cause analysis, debug hệ thống |
| `performance-optimizer` | Tối ưu hiệu năng | Core Web Vitals, bundle size |
| `seo-specialist` | SEO & GEO | E-E-A-T, tối ưu cho AI search |
| `documentation-writer` | Viết tài liệu | API docs, hướng dẫn kỹ thuật |
| `product-manager` | Quản lý sản phẩm | User stories, yêu cầu chức năng |
| `product-owner` | Chủ sản phẩm | Tầm nhìn, roadmap, backlog |
| `code-archaeologist` | Code cũ | Refactor, hiện đại hóa legacy code |
| `explorer-agent` | Khám phá codebase | Phân tích kiến trúc, audit ban đầu |

### 46 Skill (Kỹ Năng)

Skills là module kiến thức chuyên sâu, chỉ load khi agent cần.

**Frontend & UI (6)**
| Skill | Mô tả |
|-------|-------|
| `nextjs-react-expert` | Tối ưu hiệu năng React/Next.js theo chuẩn Vercel |
| `web-design-guidelines` | Audit UI: accessibility, UX, hiệu năng (100+ rules) |
| `tailwind-patterns` | Tailwind CSS v4, container queries, patterns hiện đại |
| `frontend-design` | Design system, lý thuyết màu sắc, typography, UX psychology |
| `mobile-design` | Thiết kế iOS/Android, touch psychology |
| `game-development` | Game 2D/3D, multiplayer, VR/AR |

**Backend & API (4)**
| Skill | Mô tả |
|-------|-------|
| `api-patterns` | REST vs GraphQL vs tRPC, response formats, versioning |
| `nodejs-best-practices` | Async patterns, event loop, modules |
| `python-patterns` | FastAPI, async, type hints |
| `rust-pro` | Rust 1.75+, Tokio, axum |

**Database & Hạ tầng (5)**
| Skill | Mô tả |
|-------|-------|
| `database-design` | Schema, normalization, indexing, chọn ORM |
| `deployment-procedures` | CI/CD, deployment an toàn, rollback |
| `server-management` | Quản lý process, monitoring, scaling |
| `caching-strategies` | Browser, CDN, Redis, invalidation |
| `realtime-patterns` | WebSocket, SSE, pub/sub |

**Testing & Chất lượng (5)**
| Skill | Mô tả |
|-------|-------|
| `testing-patterns` | Unit test, integration test, mocking |
| `webapp-testing` | Playwright E2E, browser testing |
| `tdd-workflow` | Quy trình RED-GREEN-REFACTOR |
| `code-review-checklist` | Tiêu chuẩn code review |
| `lint-and-validate` | Linting, type checking, static analysis |

**Bảo mật (3)**
| Skill | Mô tả |
|-------|-------|
| `vulnerability-scanner` | OWASP 2025, bảo mật chuỗi cung ứng |
| `red-team-tactics` | MITRE ATT&CK, khai thác lỗ hổng |
| `authentication` | JWT, OAuth 2.0, passkeys, RBAC, MFA |

**Kiến trúc & Lập kế hoạch (4)**
| Skill | Mô tả |
|-------|-------|
| `architecture` | System design patterns, ADR |
| `app-builder` | Khung ứng dụng full-stack (13 templates) |
| `plan-writing` | Lập kế hoạch, chia task, dependency graph |
| `brainstorming` | Phương pháp Socratic, khám phá ý tưởng |

**AI & Context Engineering (4)**
| Skill | Mô tả |
|-------|-------|
| `ai-patterns` | Kiến trúc agent, prompt engineering |
| `context-engineering` | Tối ưu context window, RAG |
| `intelligent-routing` | Phân loại request, chọn agent |
| `mcp-builder` | Xây dựng MCP server |

**4 Tính Năng Mới (lấy cảm hứng từ gstack)**
| Skill | Mô tả |
|-------|-------|
| `scope-lock` | Giới hạn phạm vi edit (`/freeze` & `/unfreeze`) |
| `cross-ai-review` | Review code đa AI (Gemini + Codex) |
| `browser-automation` | Browser daemon với hệ thống ref |
| `parallel-conductor` | Chạy song song nhiều session trên git worktree |

**Khác (11):** `clean-code`, `behavioral-modes`, `parallel-agents`, `seo-fundamentals`, `geo-fundamentals`, `i18n-localization`, `documentation-templates`, `systematic-debugging`, `performance-profiling`, `bash-linux`, `powershell-windows`

### 16 Lệnh Slash

| Lệnh | Chức năng |
|------|----------|
| `/plan` | Tạo kế hoạch triển khai (không viết code) |
| `/create` | Xây ứng dụng mới từ đầu |
| `/enhance` | Thêm tính năng vào code có sẵn |
| `/debug` | Điều tra lỗi có hệ thống |
| `/test` | Tạo và chạy test |
| `/deploy` | Triển khai production với kiểm tra trước |
| `/orchestrate` | Phối hợp nhiều agent cho task phức tạp |
| `/brainstorm` | Khám phá ý tưởng trước khi code |
| `/preview` | Quản lý dev server local |
| `/status` | Bảng trạng thái project và agent |
| `/ui-ux-pro-max` | Thiết kế UI nâng cao với 50 styles |
| `/freeze` | Khóa phạm vi edit vào paths chỉ định |
| `/unfreeze` | Gỡ khóa phạm vi edit |
| `/browse` | Mở browser cho QA testing |
| `/review-cross` | Review code đa AI (Gemini + Codex) |
| `/conduct` | Chạy song song nhiều session |

---

## 4 Tính Năng Mới (Lấy cảm hứng từ gstack)

Bốn tính năng được xây dựng từ đầu dựa trên ý tưởng của [garrytan/gstack](https://github.com/garrytan/gstack).

### 1. Khóa Phạm Vi Edit (`/freeze` & `/unfreeze`)

Khi bạn đang sửa một phần cụ thể của dự án, `/freeze` đảm bảo AI chỉ edit trong phạm vi cho phép.

```
/freeze src/components/auth/     # Chỉ cho edit trong thư mục này
/freeze src/lib/ src/utils/      # Nhiều đường dẫn
/unfreeze                        # Gỡ bỏ giới hạn
```

**Cách hoạt động:**
1. Bạn gõ `/freeze src/components/`
2. File `.agent/.freeze-scope` được tạo với danh sách paths
3. Hook `privacy-guard.sh` đọc file này trước mỗi lần Edit/Write
4. Nếu file nằm ngoài scope → **TỰ ĐỘNG CHẶN**
5. Gõ `/unfreeze` để xóa giới hạn

### 2. Review Code Đa AI (`/review-cross`)

Lấy ý kiến độc lập từ nhiều AI khác nhau, giảm thiểu điểm mù của single-model.

```
/review-cross              # Dùng tất cả AI có sẵn
/review-cross --ai gemini  # Chỉ Gemini
/review-cross --ai codex   # Chỉ Codex
```

**Kết quả:**
- Mỗi finding được phân loại: `[AGREE]` / `[DISAGREE]` / `[NEW]`
- Tổng hợp: X issues đồng thuận, Y bất đồng, Z phát hiện mới
- Issues được sắp theo mức độ nghiêm trọng: critical > high > medium > low

**Yêu cầu:** Cài Gemini CLI (`gem install gemini-cli`) và/hoặc Codex CLI (`npm i -g @openai/codex`).

### 3. Browser Daemon (`/browse`)

Trình duyệt Playwright chạy liên tục, phản hồi dưới 200ms qua HTTP API.

```
/browse https://example.com   # Mở trang web
/browse --refs                # Liệt kê các phần tử tương tác
/browse --screenshot          # Chụp ảnh màn hình
/browse --stop                # Tắt browser
```

**Hệ thống Ref:**

Thay vì CSS selector dễ hỏng, các phần tử được đánh địa chỉ bằng ref:

```
@e1: button "Đăng nhập"
@e2: textbox "Email"
@e3: textbox "Mật khẩu"
@e4: link "Quên mật khẩu?"
```

Agent dùng ref để tương tác: `click @e1`, `type @e2 "user@example.com"`.

Ref được xây từ accessibility tree — hoạt động với Shadow DOM, CSP, framework hydration.

**Cài đặt:**
```bash
pip install playwright && playwright install chromium
```

### 4. Chạy Song Song (`/conduct`)

Tạo nhiều Claude Code session chạy đồng thời trên git worktree riêng biệt.

**Tạo file config:**
```yaml
# conductor.yaml
conductor:
  base_branch: main
  sessions:
    - name: api
      task: "Xây dựng REST API cho /users và /orders"
      branch: feat/api
    - name: ui
      task: "Tạo React components cho dashboard"
      branch: feat/ui
    - name: tests
      task: "Viết integration tests cho API"
      branch: feat/tests
      depends_on: api    # Chờ api xong mới bắt đầu
```

**Sử dụng:**
```
/conduct conductor.yaml   # Bắt đầu các session song song
/conduct --status         # Kiểm tra tiến độ
/conduct --cleanup        # Dọn dẹp worktrees và branches
```

**Cách hoạt động:**
1. Parse config → xác định tasks độc lập
2. Tạo git worktree riêng cho mỗi session (`/tmp/ag-wt-{name}`)
3. Spawn Claude Code session trong mỗi worktree
4. Poll tiến độ mỗi 60 giây
5. Khi xong → tổng hợp kết quả + merge

---

## Kiến Trúc

### Cấu trúc thư mục

```
.agent/
├── agents/          # 20 agent chuyên biệt (file .md với frontmatter)
├── skills/          # 46 skill domain (SKILL.md + scripts/ + references/)
├── workflows/       # 16 slash commands (file .md với $ARGUMENTS)
├── rules/           # 3 bộ quy tắc toàn cục
├── scripts/         # 8 scripts (hooks + validation + analytics)
└── mcp_config.json  # Cấu hình MCP server
```

### Luồng xử lý

```
Yêu cầu từ người dùng
    ↓
Phân loại request (ROUTING_RULES.md)
    ↓
Chọn agent phù hợp (intelligent-routing)
    ↓
Load skill theo nhu cầu (progressive disclosure)
    ↓
Thực thi + Hooks (privacy-guard → làm việc → quality-gate)
    ↓
Kiểm tra chất lượng (checklist.py / verify_all.py)
```

### Hệ thống 3 tầng

| Tầng | Load khi nào | Nội dung |
|------|-------------|---------|
| **Tầng 0** | Luôn luôn | Quy tắc toàn cục (clean-code, routing, checklist) |
| **Tầng 1** | Theo agent | Persona agent + skills trong frontmatter |
| **Tầng 2** | Theo yêu cầu | Phần cụ thể của skill liên quan đến task |

### Hooks (Tự động)

| Hook | Khi nào chạy | Làm gì |
|------|-------------|--------|
| `privacy-guard.sh` | Trước Read/Edit/Write/Bash | Chặn file nhạy cảm + scope lock |
| `quality-gate.sh` | Sau Edit/Write | Kiểm tra TypeScript, JSON, Python, Prisma |
| `analytics-hook.sh` | Sau mọi tool | Ghi metrics (chỉ local) |

### Scripts Kiểm Tra

```bash
# Kiểm tra nhanh (trong lúc dev)
python .agent/scripts/checklist.py .

# Kiểm tra toàn diện (trước deploy)
python .agent/scripts/verify_all.py . --url http://localhost:3000
```

Thứ tự ưu tiên: Bảo mật → Lint → Schema → Tests → UX → SEO → Lighthouse → E2E

---

## Tuỳ Chỉnh Cho Từng Project

Tạo override riêng cho project mà không ảnh hưởng AG Kit gốc:

```bash
# Tạo thư mục custom
mkdir -p .agent-custom/agents
mkdir -p .agent-custom/skills

# Thêm agent riêng cho project
cat > .agent-custom/agents/my-agent.md << 'EOF'
---
name: my-agent
description: Agent riêng cho project này
tools: Read, Write, Edit, Bash
skills: clean-code, api-patterns
---

# My Custom Agent

Hướng dẫn cụ thể cho project...
EOF
```

---

## Nền Tảng Hỗ Trợ

| Nền tảng | Mức hỗ trợ |
|----------|-----------|
| **Claude Code** | Đầy đủ (agents, skills, workflows, hooks) |
| **Gemini CLI** | Đầy đủ (qua GEMINI.md + MCP config) |
| **Cursor** | Một phần (skills làm context, không có hooks) |
| **AI IDE khác** | Skills đọc được như tài liệu markdown |

---

## Câu Hỏi Thường Gặp

**AG Kit có tốn thêm token không?**
Progressive disclosure chỉ load skill khi cần. Nếu bạn hỏi về React, chỉ frontend skill được load — không phải toàn bộ 46 skills.

**Tôi có thể dùng chung AG Kit cho nhiều project không?**
Có. Dùng symlink (`ln -s`) — tất cả project trỏ đến cùng một bản AG Kit. Cập nhật một lần, tất cả nhận bản mới.

**Hooks có bắt buộc không?**
Không. Hooks là tùy chọn nhưng được khuyến nghị. `privacy-guard.sh` bảo vệ file nhạy cảm, `quality-gate.sh` giúp phát hiện lỗi sớm.

**Tôi cần cài Playwright không?**
Chỉ nếu bạn dùng `/browse` (browser daemon). Các tính năng khác không cần.

**Cross-AI review cần gì?**
Cần ít nhất một trong: Gemini CLI hoặc Codex CLI. Script tự phát hiện tools có sẵn.

---

## Giấy phép

MIT — Miễn phí, mã nguồn mở.

## Ghi công

4 tính năng mới lấy cảm hứng từ [gstack](https://github.com/garrytan/gstack) của Garry Tan (CEO Y Combinator) — được xây dựng lại từ đầu cho kiến trúc AG Kit.
