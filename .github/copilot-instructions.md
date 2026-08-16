# Copilot Instructions — Embedded/Firmware Projects

Adapted from Claude Code skills: `embedded-systems`, and mattpocock-skills (`diagnosing-bugs`, `tdd`,
`code-review`, `codebase-design`, `domain-modeling`, `resolving-merge-conflicts`, `research`,
`prototype`). GitHub Copilot has no native skill-plugin system, so this file inlines the guidance
those skills would otherwise apply automatically.

**Portable file:** this file is written to be carried as-is into any embedded/firmware project's
`.github/copilot-instructions.md`. Only the `## Project context` section below is project-specific —
fill it in for each project; every other section is generic and needs no changes.

## Project context

- Target: *this project's MCU/board, core (e.g. Cortex-M4), and build system.*
  <!-- Example (STM32F4 LED_BLINK): STM32F411xE (Arm Cortex-M4), HAL driver + CMSIS, CMake build. -->
- Layering: *this project's actual module layering, if any.*
  <!-- Example (STM32F4 LED_BLINK): AUTOSAR-inspired — App/ (e.g. App/LedBlink) -> Rte/ (e.g.
  Rte_LedBlink.c) -> Bsw/ (Bsw/EcuAbstraction/LedDriver, Bsw/ServiceLayer/Os) -> Drivers/
  (ST HAL/CMSIS, vendor code - do not edit). App calls Rte, Rte calls Bsw, Bsw calls Drivers;
  never call upward, and never skip a layer. -->
- Vendor/HAL/CMSIS/generated code is read-only — patch or wrap at the application/abstraction
  layer instead of editing it directly.

## Embedded firmware rules (from `embedded-systems`)

**Must do**
- Use `volatile` for hardware registers and any variable shared with an ISR.
- Keep ISRs short: read hardware, set a flag/queue, exit — defer real work to a task or the main loop.
- Add/keep watchdog coverage; handle every error path (HAL return codes, register error flags).
- Document resource usage (flash/RAM) and timing assumptions when adding peripherals or tasks.
- Protect any resource shared between ISR and normal context with a critical section
  (`__disable_irq()`/`__enable_irq()` or the RTOS equivalent).

**Must not do**
- Block (delay loops, blocking HAL calls, mutex wait) inside an ISR.
- Allocate memory dynamically without a bounds check, or use floating-point without checking
  the target has hardware FPU support.
- Hardcode chip-specific magic numbers without a comment tying them to the datasheet/reference manual.
- Edit vendor/HAL/CMSIS/generated code directly — patch or wrap at the application/abstraction
  layer instead.

**Before calling a change done:** compiles clean with `-Wall -Werror`, register bit-fields checked
against the target's reference manual, and — where timing matters — verified against expected
behavior (logic analyzer/oscilloscope for hardware, or stack high-water mark for RTOS tasks).

## Debugging (`diagnosing-bugs`)

1. **Build a feedback loop before theorizing.** For firmware: a unit test at a module seam,
   a scripted flash-and-observe cycle, or a captured trace/log — something that reliably goes red on
   this bug and green once fixed. Don't start reading code to form a theory before this exists.
2. **Reproduce, then minimize** to the smallest input/config that still reproduces.
3. **Write 3–5 falsifiable hypotheses** ("if X is the cause, changing Y makes it disappear") before
   testing any of them. Rank them; a domain expert can often reorder instantly.
4. **Instrument one variable at a time.** Tag debug logs with a unique prefix (e.g. `[DEBUG-xxxx]`)
   so cleanup is a single search-and-remove.
5. **Fix, then add a regression test at a real seam** if one exists; if no correct seam exists, say so —
   that's itself a finding about the architecture.
6. Cleanup: remove all tagged debug instrumentation, confirm the original repro no longer fails.

## Tests (`tdd`)

- Test through a module's public interface, never through internals or private state.
- Agree the **seam** being tested before writing the test.
- Red → green → (refactor separately, not in the same step): write the failing test first, then the
  minimal code to pass it. One seam, one test, one minimal implementation per cycle.
- Avoid tautological tests (asserting a value computed the same way the code computes it) — use an
  independent expected value (datasheet timing, a known-good literal).

## Code review (`code-review`)

Review every non-trivial change on two separate axes, and don't let one mask the other:
- **Standards** — does it follow this repo's layering rules and the embedded must/must-not list above?
- **Spec** — does it do what was actually asked, no more (watch for speculative generality) and no less?

Baseline smells to flag: duplicated logic across layers, a module reaching into another layer's
internals (Feature Envy), the same register-config `switch` repeated in multiple places, and
magic numbers standing in for a named hardware constant (Primitive Obsession).

## Module design (`codebase-design`)

Aim for **deep modules**: small interface, real behavior behind it, placed at a clean seam
(e.g. a driver module's public functions hiding the register/GPIO details from its caller). Before
adding a new parameter or method, ask: can the complexity be hidden inside instead of exposed at the
interface? Don't add a seam (interface + swappable adapter) for only one implementation — introduce
it when a second one actually shows up.

## Domain terms (`domain-modeling`)

If this repo has (or grows) a `CONTEXT.md` or spec document defining domain terms, keep new code and
comments consistent with it. Flag it explicitly if new code uses a term in a way that conflicts with
that doc.

## Merge conflicts (`resolving-merge-conflicts`)

Read both sides' commit messages/intent before resolving a hunk. Preserve both intents where
possible; where incompatible, pick the one matching the merge's stated goal and note the trade-off.
Never invent new behavior to "solve" a conflict. Always resolve — never abort. After resolving,
rebuild (and re-flash, if hardware is available) before finishing.

## Research & prototyping

- For open questions about the target MCU/peripheral, check the vendor reference manual/datasheet/
  HAL source first — treat blog posts and forum answers as secondary, not primary, sources.
- For "does this state machine/logic feel right" questions, it's fine to write a small throwaway
  host-side (non-target) simulation to sanity-check the logic before implementing it against real
  registers — but mark it clearly as throwaway and delete it once the real implementation lands.
