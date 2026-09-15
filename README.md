# Autonomous Protocol Emulator

> **An open-source, agentic approach to hardware design and verification for the [Jane Street Protocol Emulator ASIC Competition](https://blog.janestreet.com/protocol-emulator-asic-competition/).**

## Phase 1 — Requirement Reference Model & Testbench

### Objective

Build an **architecture-independent requirement verification environment** for the Jane Street Protocol Emulator competition.

The goal of this phase is **not to design the chip**.

The goal is to answer:

> **What observable behavior does Jane Street require from a correct protocol emulator, and can we automatically verify that behavior?**

At the end of this phase, we should have:

```text
Jane Street Specification
        ↓
Requirement Specification (ReqSpec)
        ↓
Behavioral Reference Model
        ↓
Requirement-Level Testbench
        ↓
Requirement Coverage
```

This environment will later become the common verification layer used to evaluate multiple candidate architectures.

---

## 1. Core Principle

We must strictly separate:

```text
WHAT the chip must do
```

from:

```text
HOW we choose to implement it
```

The Phase 1 verification environment must therefore **not assume a particular architecture**.

---

## 2. Scope

Phase 1 covers only the requirements explicitly implied by the Jane Street competition specification.

The initial scope includes:

* protocol emulation
* UART
* SPI
* I2C
* GPIO/pin behavior
* programmable behavior
* timing behavior
* cycle-level behavior where externally observable
* input/output behavior
* reset/initialization behavior where specified
* physical constraints that can be expressed as verification constraints
* requirement traceability
* coverage

Phase 1 does **not** define:

* CPU architecture
* ISA
* register count
* instruction width
* memory architecture
* microarchitecture
* internal FSMs
* datapath implementation
* specific RTL structure

Those belong to later architecture/design phases.

---

## 3. Phase 1 Architecture

The verification infrastructure should have four primary components:

```text
                         Jane Street Spec
                               │
                               ▼
                    ┌────────────────────┐
                    │ Requirement Spec   │
                    │      ReqSpec       │
                    └─────────┬──────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
       Behavioral Reference          Verification Plan
             Model                          │
                │                           │
                └─────────────┬─────────────┘
                              ▼
                     Requirement Testbench
                              │
                              ▼
                          DUT / RTL
```

The important property is:

> The DUT can eventually be replaced by completely different architectures without changing the fundamental requirement model.

---

## 4. Step 1 — Requirement Extraction

First, extract the competition specification into a structured requirements database.

Every requirement receives a unique ID.

Example:

```yaml
id: REQ-SPI-001

category: SPI

priority: MUST

source:
  document: jane_street_spec
  location: <section/page>

statement: >
  The protocol emulator shall support SPI communication.

status: confirmed
```

Requirements should be categorized into:

```text
functional
protocol
timing
interface
programmability
physical
performance
optional/stretch
```

---

## 5. Step 2 — Classify Requirements

Every extracted statement should be classified as one of:

### MUST

Explicit competition requirement.

```text
The design MUST support X.
```

### SHOULD

Strongly desirable behavior.

```text
The design SHOULD support X.
```

### MAY

Optional/stretch behavior.

```text
The design MAY support X.
```

### DESIGN CHOICE

Not specified by Jane Street and therefore left to us.

```text
Number of registers
Instruction width
ISA encoding
CPU architecture
```

### AMBIGUOUS

The specification does not provide enough information to determine a unique interpretation.

```text
"Precise timing"
```

should not silently become an arbitrary numerical requirement.

Instead:

```yaml
id: REQ-TIMING-001

statement: precise timing

status: ambiguous

open_question:
  - What timing accuracy is required?
```

This prevents assumptions from accidentally becoming requirements.

---

## 6. Step 3 — Convert Requirements into Observable Contracts

Natural-language requirements are not sufficient for a testbench.

Each testable requirement should be converted into an **observable contract**.

For example:

```yaml
id: REQ-UART-TX-001

statement:
  UART transmission shall be supported.

inputs:
  - transmit data
  - clock
  - configuration

outputs:
  - TX pin

preconditions:
  - emulator initialized

behavior:
  - generate UART frame
  - generate start bit
  - transmit data bits
  - generate stop bit

observable_properties:
  - TX idle level is correct
  - bit ordering is correct
  - bit timing is correct
  - frame structure is correct

verification:
  checker: uart_checker
  reference_model: uart_reference_model
```

The objective is to answer:

> **What exact observations would convince us that this requirement has been satisfied?**

---

## 7. Step 4 — Define the Behavioral Reference Model

The reference model represents the **ideal externally observable behavior** of the protocol emulator.

It must not model a particular RTL architecture.

For protocol behavior:

```text
Protocol intent
      ↓
Reference Model
      ↓
Expected pin-level behavior
```

For example:

```text
SPI transaction
      ↓
SPI reference model
      ↓
Expected:
    CS waveform
    SCLK waveform
    MOSI waveform
    MISO sampling
    timing relationships
```

Similarly:

```text
UART transaction
      ↓
UART reference model
      ↓
Expected TX/RX behavior
```

and:

```text
I2C transaction
      ↓
I2C reference model
      ↓
Expected SDA/SCL behavior
```

---

## 8. Reference Model Design Principles

### 8.1 Architecture independence

The reference model must not depend on:

* instruction encoding
* CPU implementation
* register file
* internal FSM
* RTL hierarchy

### 8.2 Determinism

Given the same inputs and initial state:

```text
same input
    ↓
same reference behavior
```

### 8.3 Cycle/timing awareness

Where timing is part of the requirement, the reference model must represent time explicitly.

For example:

```text
cycle 0 → CS asserted
cycle 1 → SCLK transition
cycle 2 → data transition
...
```

The exact representation should be chosen based on the requirements.

### 8.4 Explicit uncertainty

If Jane Street's specification does not define something, the model must not invent a requirement.

Instead:

```text
UNSPECIFIED
```

or:

```text
CONFIGURABLE
```

should be represented explicitly.

---

## 9. Step 5 — Define the Requirement Testbench

The testbench should test the DUT against the behavioral reference model.

Conceptually:

```text
                   Test Input
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      Reference Model           DUT
             │                   │
             ▼                   ▼
      Expected behavior     Actual behavior
             │                   │
             └─────────┬─────────┘
                       ▼
                    Checker
                       │
                  PASS / FAIL
```

The testbench should contain:

```text
test generation
stimulus
drivers
monitors
reference models
checkers
assertions
coverage
logging
```

---

## 10. Test Categories

Each requirement should have one or more tests.

### 10.1 Basic functional tests

Verify that the required capability works under normal conditions.

Example:

```text
TEST-UART-TX-BASIC
```

---

### 10.2 Boundary tests

Test limits defined by the specification.

Examples:

```text
minimum supported timing
maximum supported timing
minimum data size
maximum data size
```

---

### 10.3 Corner cases

Examples:

```text
all-zero data
all-one data
alternating bits
long sequences of identical bits
back-to-back transactions
```

---

### 10.4 Protocol interaction tests

Where applicable:

```text
SPI transaction followed by I2C
UART while another operation is active
multiple protocol operations
```

---

### 10.5 Negative tests

Test invalid or unexpected inputs where the specification defines expected behavior.

Examples:

```text
invalid transaction
incorrect framing
unexpected signal transition
```

Do not invent expected behavior if Jane Street does not specify it.

---

## 11. Protocol-Specific Reference Models

The initial protocol models should be developed independently.

### UART

Model:

```text
TX
 ├── idle
 ├── start
 ├── data
 └── stop

RX
 ├── detect start
 ├── sample data
 └── validate frame
```

The model should generate expected waveforms and validate observed waveforms.

---

### SPI

Model:

```text
CS
SCLK
MOSI
MISO
```

The model should capture the relevant timing and data relationships specified by the competition.

Where the specification leaves SPI modes/configurations open, record them as explicit assumptions rather than silently selecting one.

---

### I2C

Model:

```text
SDA
SCL
```

including the required protocol behavior such as:

```text
START
address
ACK/NACK
data
STOP
```

Again, only behavior required or clearly implied by the specification should be treated as mandatory.

---

## 12. Requirement Traceability

Every requirement must map to verification artifacts.

The desired structure is:

```text
REQ
 │
 ├── TEST
 ├── ASSERTION
 ├── CHECKER
 └── COVERAGE
```

Example:

```text
REQ-SPI-001
    │
    ├── TEST-SPI-001
    ├── TEST-SPI-002
    ├── spi_protocol_checker
    └── SPI functional coverage
```

This enables automatic reporting:

```text
Total requirements:       57
Verified:                 54
Partially verified:        2
Unverified:                1
Ambiguous:                 3
```

---

## 13. Coverage

We should track coverage at the **requirement level**, not just RTL/code coverage.

Important metrics include:

### Requirement coverage

```text
verified requirements / total applicable requirements
```

### Scenario coverage

Have we exercised the meaningful behaviors associated with a requirement?

### Protocol coverage

For example:

```text
UART
 ├── frame types
 ├── data patterns
 ├── timing configurations
 └── boundary cases
```

### Assertion coverage

Which behavioral properties have been exercised?

### Functional coverage

Which protocol behaviors have actually occurred?

Code coverage can be collected later, but it should not be the primary definition of success in this phase.

---

## 14. Testbench API

The testbench should expose an architecture-neutral interface.

Conceptually:

```python
result = emulator.execute(
    program=<program>,
    inputs=<inputs>
)
```

and:

```python
expected = reference_model.execute(
    specification=<behavior>,
    inputs=<inputs>
)
```

Then:

```python
compare(
    expected,
    actual
)
```

The precise API will depend on the eventual DUT interface.

The key requirement is that **test intent should not depend on RTL implementation details**.

---

## 15. Architecture Adapter

Later, each architecture should provide an adapter to the common verification environment.

```text
              Generic Testbench
                     │
           ┌─────────┴─────────┐
           ▼                   ▼
   Architecture A Adapter   Architecture B Adapter
           │                   │
           ▼                   ▼
         RTL A               RTL B
```

This prevents the testbench from becoming tightly coupled to one implementation.

---

## 16. Handling Underspecified Requirements

This is a first-class feature.

Every requirement should have a status:

```text
CONFIRMED
ASSUMED
AMBIGUOUS
UNSUPPORTED
VERIFIED
```

For example:

```yaml
id: REQ-TIMING-002

statement: >
  The emulator shall provide precise timing.

status: ambiguous

verification:
  status: blocked

reason: >
  The specification does not define a numerical timing tolerance.
```

The agent should **flag the ambiguity rather than fabricate a requirement**.

This will also allow us to identify questions that need to be resolved before architecture selection.

---

## 17. What We Should NOT Build Yet

The following should explicitly be deferred:

```text
❌ CPU architecture
❌ ISA
❌ register file
❌ instruction encoding
❌ microarchitecture
❌ internal FSM
❌ RTL optimization
❌ PPA optimization
❌ architecture-specific assertions
```

We are building the **contract against which those future designs will be evaluated**.

---

## 18. Definition of Done

Phase 1 is complete when we have:

### Requirements

* [ ] Complete extraction of Jane Street requirements
* [ ] Unique requirement IDs
* [ ] Requirement categories
* [ ] MUST/SHOULD/MAY classification
* [ ] Explicit architectural/design choices
* [ ] Explicit ambiguities
* [ ] Source traceability

### Reference model

* [ ] Architecture-independent behavioral model
* [ ] UART model
* [ ] SPI model
* [ ] I2C model
* [ ] GPIO model
* [ ] Timing model
* [ ] Defined handling of unspecified behavior

### Testbench

* [ ] Requirement-driven test generation
* [ ] Protocol drivers
* [ ] Protocol monitors
* [ ] Reference-model integration
* [ ] Protocol checkers
* [ ] Assertions
* [ ] Functional coverage
* [ ] Requirement traceability
* [ ] Regression infrastructure

### Reporting

The system should automatically produce something similar to:

```text
Requirement Verification Report
================================

Requirements:
    Total:             57
    Verified:          52
    Partially verified: 2
    Unverified:         3

Protocols:
    UART:              PASS
    SPI:               PASS
    I2C:               PASS

Coverage:
    Requirement:       91%
    Functional:        XX%
    Assertions:        XX%

Ambiguities:
    4

Failures:
    0
```

---

## 19. Deliverable

The primary deliverable of Phase 1 is:

> **An executable, architecture-independent interpretation of the Jane Street specification that can determine whether a candidate protocol emulator satisfies the externally observable requirements.**

This becomes the foundation for the rest of the project.

The later architecture-search system should be able to take:

```text
Candidate Architecture
        ↓
Candidate RTL
        ↓
Phase 1 Requirement Testbench
        ↓
PASS / FAIL + Coverage
```

without modifying the underlying requirement contract.

---

## 20. End State

At the end of Phase 1:

```text
                    Jane Street Spec
                           │
                           ▼
                  ┌─────────────────┐
                  │     ReqSpec     │
                  └────────┬────────┘
                           │
                           ▼
                Behavioral Reference
                       Model
                           │
                           ▼
                 Requirement Tests
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              Architecture A  Architecture B
                    │             │
                    ▼             ▼
                  RTL A         RTL B
                    │             │
                    └──────┬──────┘
                           ▼
                  Common Requirement
                     Verification
```

The critical output is not simply a testbench.

It is a **stable behavioral contract** that allows us to subsequently explore many different architectures while maintaining a consistent definition of correctness.

---

## Next Step

The immediate next task is **not coding the testbench**.

First:

```text
1. Obtain the complete Jane Street specification
2. Extract every explicit requirement
3. Assign REQ-* IDs
4. Classify each requirement
5. Identify ambiguities
6. Define observable behavior
7. Map requirements to verification methods
```

Only after this **Requirements Matrix** is complete should we implement the reference models and testbench.
