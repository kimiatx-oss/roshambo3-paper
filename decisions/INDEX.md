# Standing decisions

Decisions that outlive any one ticket. **Read these before starting work** -- they constrain scope in ways an individual ticket may not mention, and they record *why*, so a settled question is not relitigated or quietly assumed the other way.

This repository ships 12 of the project's 33 decisions; see the top-level README.

| id | status | title |
|---|---|---|
| [D007](D007-clock-control-and-operating-points.md) | active, permanent | Clock control: profilers seize the clock, and numbers from different clocks must not be mixed |
| [D009](D009-bottleneck-attribution-method.md) | active, permanent | How to claim a GPU bottleneck |
| [D011](D011-long-running-job-protocol.md) | active, permanent | How to wait for a long-running job |
| [D013](D013-acceptance-is-recall-not-bit-identity.md) | active — **supersedes the operative use of bit-identity as an acceptance gate** | The acceptance criterion is recall and top-end ranking, not bit-identity |
| [D015](D015-a-probe-is-not-a-kernel.md) | active, permanent | A probe is not a kernel: validate the harness before trusting its ranking |
| [D022](D022-ruled-out-with-reasons.md) | active | Approaches ruled out, with the reason, so they do not come back |
| [D023](D023-measurement-regimes.md) | active | Two measurement regimes: calibration, and headline |
| [D029](D029-the-cpu-scoring-path.md) | accepted 2026-09-02 by the author | The CPU scoring path: the frame, the oracle, and what may be compared |
| [D030](D030-the-cpu-field-paths-default-configuration.md) | accepted 2026-09-07 by the author (right-for-now default) | The CPU field path's default configuration |
| [D031](D031-cpu-color-static-hybrid.md) | active implementation direction, authorized by the author; production thresholds remain uncalibrated | CPU color starts with a static, cache-aware hybrid |
| [D033](D033-self-overlaps-must-describe-the-scored-coordinates.md) | accepted by the author; Amendment 1 (two-tier margin) accepted by the author 2026-10-16, **not yet active** (see its activation conditions) | Self-overlaps must describe the scored coordinates; a row that shows otherwise is refused |
| [D034](D034-corpus-format-3.md) | accepted (the author, 2026-10-18) | Corpus format 3: one hard break before release, at 2^-8 A, bit-packed, self-describing |
