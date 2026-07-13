# Pratham Task Board

## Current Assignment
Design and implement OpenTelemetry context propagation.

## Tomorrow's Implementation Tasks
- [ ] Research tracing context patterns across multi-threaded Agent Fleet execution. (Priority: High)
- [ ] Map span propagation from Manager Agent to child CDC/GB Agents. (Priority: High)
- [ ] Design non-blocking tracing hooks inside connection acquisition loops. (Priority: Medium)
- [ ] Define observability tags for transaction logging. (Priority: Medium)
- [ ] Draft requirements for enterprise metrics export format. (Priority: Low)

## Testing Constraints
* **No Live Database Testing**: Pratham is not assigned any live database testing because the database staging and production-like environments reside exclusively on Aalok's local machine.
* **Mocks / Stubs**: Pratham should use mocks and stubs for database connections and adapters to verify trace propagation locally.

## Completed Today (2026-07-12)
- [x] Initialized functional/non-functional requirements baseline in `project/REQUIREMENTS.md`.
- [x] Set up subsystem ownership matrix in `project/TEAM.md`.

## Waiting On
- [ ] Staging instance connectivity specifications from Aalok.

## Notes
* **Implementation Certification**: Implementation is complete only after Aalok integrates and certifies it in the live database environment.
* Context propagation must not introduce any execution overhead in high-throughput transfer channels.

## Next Task
Prototype child span instantiation inside `GBAgent`.

