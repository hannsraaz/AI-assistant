# 🏛️ FRIDAY V3 — Autonomous Computer Agent Architecture & Design Specification

---

## 1. System Overview & Evolution

FRIDAY V3 upgrades Friday from a tool-calling assistant into a **fully autonomous personal computer agent**.
The agent operates under a continuous cognitive loop:

$$\text{UNDERSTAND} \longrightarrow \text{PLAN} \longrightarrow \text{ACT} \longrightarrow \text{OBSERVE} \longrightarrow \text{VERIFY} \longrightarrow \text{RECOVER} \longrightarrow \text{REPORT}$$

```
                                  ┌────────────────────────┐
                                  │   Microphone / Text    │
                                  └───────────┬────────────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │   openWakeWord    │ ("Hey Jarvis", 16kHz ONNX)
                                    └─────────┬─────────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │  Faster-Whisper   │ (In-Memory float32, base.en)
                                    └─────────┬─────────┘
                                              │
                    ┌─────────────────────────▼─────────────────────────┐
                    │               FRIDAY V3 CORE COGNITION            │
                    │                                                   │
                    │  Intent Router       Unified Context Manager      │
                    │  Agentic Planner     Task & Background Manager    │
                    │  Memory 2.0 Engine   Response & Spoken Language   │
                    │  Telemetry Tracker   Proactive Monitor            │
                    └───────────┬───────────────────────────┬───────────┘
                                │                           │
          Fast-Path (<50ms)     │                           │ Complex / Multi-Step Goal
                                ▼                           ▼
                     ┌────────────────────┐      ┌────────────────────┐
                     │  Deterministic OS  │      │  Autonomous Agent  │
                     │   Direct Action    │      │   Execution Loop   │
                     └──────────┬─────────┘      └──────────┬─────────┘
                                │                           │
                                └─────────────┬─────────────┘
                                              ▼
                                 ┌─────────────────────────┐
                                 │      TOOL REGISTRY      │
                                 │ (Capability Discovery)  │
                                 └────────────┬────────────┘
                                              ▼
                                 ┌─────────────────────────┐
                                 │   SECURITY MODEL 2.0    │
                                 │  (Risk, Sandbox, Auth)  │
                                 └────────────┬────────────┘
                                              │
       ┌───────────────┬──────────────────────┼──────────────────────┬───────────────┐
       ▼               ▼                      ▼                      ▼               ▼
    WINDOWS          FILES                  VISION               DEVELOPER      AUTOMATION
       │               │                      │                      │               │
  ├── Apps        ├── Search             ├── Capture            ├── Terminal    ├── Scheduler
  ├── Windows     ├── List               ├── Describe           ├── Git / GH    ├── Workflows
  ├── System      ├── Read/Create        ├── Structured OCR     ├── Android     └── Proactive
  ├── Media       └── Sandbox Guard      └── UI Locator (XY)    └── Playwright
  └── Input
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                                 │    VERIFICATION &       │
                                 │    RECOVERY ENGINE      │
                                 └────────────┬────────────┘
                                              ▼
                                 ┌─────────────────────────┐
                                 │   STREAMING SPEECH &    │
                                 │      CONTROL HUD        │
                                 └────────────┬────────────┘
                                              │
                                              ▼
                                       🔊 Audio / 🖥️ GUI
```

---

## 2. Component Inventory & Audit (V2.1 Baseline)

| Subsystem | File Location | Core Class / Structure | V2.1 Role & Capabilities | V3 Target Evolution |
| :--- | :--- | :--- | :--- | :--- |
| **Assistant Core** | [`assistant_core.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/assistant_core.py) | `VoiceAssistant` | Coordinates voice capture, router, streaming speech, cancellation tokens. | Integrate `UnifiedContext`, state machine propagation, and background task handoffs. |
| **Intent Router** | [`intent_router.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/intent_router.py) | `IntentRouter` | Regex fast-path for volume, apps, system stats, timers (<1ms). | Route deterministic single actions instantly; hand multi-step tasks to `AgenticPlanner`. |
| **Agentic Planner** | [`core/agent/planner.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/agent/planner.py) | `AgenticPlanner` | Generates sequential JSON plans with `_execute_with_repair`. | Add formal step states (`PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `RETRYING`), explicit verification, and goal verification. |
| **Tool Registry** | [`core/tools/registry.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/tools/registry.py) | `ToolRegistry` | Central dispatcher, schema generation for LLM. | Expose tool capabilities, reversibility, side-effects, and smart capability-based selection. |
| **Permission Manager** | [`core/tools/permissions.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/tools/permissions.py) | `PermissionManager` | Token-based confirmation, 60s TTL, risk levels. | Enforce structured resource boundaries, non-cancellable flags, and irreversible action protections. |
| **Task Manager** | [`core/agent/task_manager.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/agent/task_manager.py) | `TaskManager` | Thread-safe task store and async worker execution. | Support `pause`, `resume`, structured step progress reporting, and live GUI event feeds. |
| **Memory Manager** | [`core/memory/memory_manager.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/memory/memory_manager.py) | `MemoryManager` | JSON-persisted facts, aliases, preferences, password filters. | Add Memory 2.0 metadata (`memory_id`, `type`, `created_at`, `source`, `confidence`) and selective retrieval. |
| **Response Engine** | [`core/response_engine.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/response_engine.py) | `ResponseEngine` | Formats raw data into concise, natural spoken voice responses. | Support intermediate progress updates and multi-step execution summaries. |
| **Vision System** | [`core/tools/vision/screen_vision.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/tools/vision/screen_vision.py) | `ScreenVisionService` | Multimodal Ollama queries (`llama3.2-vision`), screen captures. | Output structured bounding boxes `{"elements": [{"type": "button", "label": "...", "x": X, "y": Y}]}`. |
| **Browser System** | [`core/tools/browser/browser_ops.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/tools/browser/browser_ops.py) | `Browser*Tool` | Fast `requests` HTML fetching, search, open tab, download. | Add optional Playwright engine for JavaScript-heavy DOM interaction and tab management. |
| **Scheduler** | [`core/automation/scheduler.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/automation/scheduler.py) | `PersistentScheduler` | JSON-backed timer & reminder loop. | Retain robust JSON persistence and link with proactive agent events. |
| **HUD / GUI** | [`gui.py`](file:///c:/Users/razzk/Downloads/Friday%20mark%201/gui.py) | `AssistantWindow` | Glowing animated orb, transcript, chat box, quick pills. | Upgrade into full FRIDAY Control Center showing live task progress, active tool, step logs, and cancel buttons. |

---

## 3. End-to-End Execution Paths

### 3.1 Fast Deterministic Commands (< 50ms)
```
User: "Set volume to 50%"
 ├── 1. Audio In (Faster-Whisper base.en: ~250ms)
 ├── 2. IntentRouter regex match -> "volume.set(50)" (0.38ms)
 ├── 3. Native CoreAudio COM execution via pycaw (37.85ms)
 ├── 4. ResponseEngine formats text: "Volume set to 50%." (0.1ms)
 └── 5. Streaming TTS playback (Piper: ~280ms)
Total roundtrip: ~570ms (Fast path execution itself: ~38ms)
```

### 3.2 Conversational / Single-Step LLM Commands
```
User: "What is the capital of France and what is its famous tower?"
 ├── 1. IntentRouter unhandled -> Forward to LLM
 ├── 2. Ollama streaming token generation (Time to first token: ~36ms)
 ├── 3. Sentence streaming to XTTS / Piper
 └── 4. Concurrent audio playback while subsequent tokens stream
```

### 3.3 Multi-Step Agentic Tasks (Understand → Plan → Act → Observe → Verify → Report)
```
User: "Find the PDF invoice in Downloads and move it to Documents"
 ├── 1. Planner analyzes goal + unified context
 ├── 2. Step 1: files.search(query="*invoice*.pdf", directory="Downloads")
 │     └── Observe: Found "invoice_2026.pdf" -> Verify: File exists
 ├── 3. Step 2: files.move(source="Downloads/invoice_2026.pdf", destination="Documents/invoice_2026.pdf")
 │     └── Permission Check: CONFIRM -> If approved -> Execute
 ├── 4. Verification: Check files.exists("Documents/invoice_2026.pdf")
 └── 5. Report: "Moved invoice_2026.pdf to Documents successfully."
```

### 3.4 Long-Running Autonomous Background Tasks
```
User: "Build my Android project in the background and let me know when it's done"
 ├── 1. TaskManager creates TaskRecord(title="Android Project Build")
 ├── 2. VoiceAssistant immediately returns: "Starting Android build in the background. I'll alert you when it's done."
 ├── 3. Background Thread launches Planner.plan_and_execute(goal, task)
 ├── 4. Planner executes:
 │     ├── Step 1: android.build(project_path="...") -> Observe exit code
 │     ├── If Failed:
 │     │    ├── Diagnose: Parse gradle stacktrace
 │     │    ├── Repair: Modify missing config or clean cache
 │     │    └── Retry: Run gradle clean build
 │     └── Step 2: Verify build APK artifact exists
 └── 5. Trigger proactive voice notification: "Your Android build completed successfully."
```

### 3.5 Interrupted / Cancelled Tasks
```
User: "Friday, cancel that" / "Friday, stop"
 ├── 1. VoiceAssistant.cancel() triggered
 ├── 2. CancellationToken set
 ├── 3. TTS sounddevice audio halted immediately & buffer cleared
 ├── 4. LLM streaming loop interrupted
 ├── 5. Planner halts step execution before next tool
 ├── 6. Active background TaskRecord.stop_event set -> Status marked CANCELLED
 └── 7. State transitioned to IDLE with status "Task cancelled."
```

### 3.6 Failed Task Recovery Loop
```
Execution Step Fails (e.g. File locked or Command Error)
 ├── 1. Tool returns ToolResult(success=False, error=ToolError(code="...", message="..."))
 ├── 2. Planner observes failure code and stderr
 ├── 3. Planner calls _diagnose_and_repair(tool, args, error_message)
 ├── 4. LLM suggests adjusted arguments or fallback tool
 ├── 5. Planner retries execution (up to 3 attempts)
 ├── 6. If recovered: Mark step SUCCESS and continue
 └── 7. If unrecoverable: Mark task FAILED, log diagnostics, and explain root cause to user
```

---

## 4. Unified Context Schema (Phase 8)

```python
@dataclass
class UnifiedContext:
    conversation_history: list[dict[str, str]]
    current_goal: str | None
    current_task_id: str | None
    assistant_state: AssistantState
    active_application: str
    active_window_title: str
    recent_tool_results: list[ToolResult]
    relevant_memories: list[dict[str, Any]]
    screen_summary: str | None
    pending_permission: dict[str, Any] | None
```

---

## 5. Security Model 2.0 Matrix (Phase 13)

| Resource | Boundary / Safeguard | Confirmation Requirement | Reversibility |
| :--- | :--- | :--- | :--- |
| **Files** | Path resolution locked out of `C:\Windows`, `C:\Program Files`, symlink/junction breakout rejected. | `files.delete`, `files.move`, `files.create` require confirmation. | Delete is irreversible (unless recycle bin used). |
| **Terminal** | Prohibits `rmdir /s`, `del /f`, `format`, `diskpart`, `rm -rf`, `sudo`, `reg delete`. | Non-whitelisted modifying shell commands require user approval. | Command dependent. |
| **Git** | Full local status/diff/log is safe. | `git.push`, `git reset --hard`, `git clean` require confirmation. | Hard reset is irreversible. |
| **Browser** | Web reading and search are safe. | External side effects (form submit, payments, credential inputs) require confirmation. | External actions irreversible. |
| **Memory** | Filters passwords, tokens, and private keys. | `memory.forget` requires confirmation. | Irreversible. |

---

## 6. Execution Roadmap for V3 Implementation

1. **Phase 1**: Architecture Audit & Complete Execution Mapping (`FRIDAY_V3_ARCHITECTURE.md`).
2. **Phase 2**: Unified Agent Execution Loop (`core/agent/planner.py` with full step states & verification).
3. **Phase 3 & 4**: Background Autonomous Tasks & Real Progress Reporting (`core/agent/task_manager.py` with pause/resume and live events).
4. **Phase 5**: Structured Vision Agent (`core/tools/vision/screen_vision.py` with bounding box element locator).
5. **Phase 6**: Hybrid Browser Agent (`core/tools/browser/` with optional Playwright support).
6. **Phase 7 & 8**: True Interruption & Unified Context Manager (`core/agent/context.py`).
7. **Phase 9, 10, 11, 12**: Memory 2.0, Capability-Based Tool Discovery, Smart Selection & Verification Handlers.
8. **Phase 13, 14, 15**: Security Model 2.0, Realistic Failure Simulations & 10 End-to-End Scenarios.
9. **Phase 16, 17, 18**: Performance Benchmarking, HUD Control Center & Final Verified Documentation.
