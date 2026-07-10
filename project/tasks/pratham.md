# Pratham Task Board

## Current Assignment
Design and implement OpenTelemetry context propagation.

## Objectives
- [ ] Research tracing context patterns across multi-threaded Agent Fleet execution.
- [ ] Define observability tags for transaction logging.
- [ ] Draft requirements for enterprise metrics export format.

## Active Tasks
- [ ] Map span propagation from Manager Agent to child CDC/GB Agents.
- [ ] Design non-blocking tracing hooks inside connection acquisition loops.

## Completed Today
- [x] Initialized functional/non-functional requirements baseline in `project/REQUIREMENTS.md`.
- [x] Set up subsystem ownership matrix in `project/TEAM.md`.

## Waiting On
- [ ] Staging instance connectivity specifications from Aalok.

## Notes
* Context propagation must not introduce any execution overhead in high-throughput transfer channels.

## Next Task
Prototype child span instantiation inside `GBAgent`.
