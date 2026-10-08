# Experiment Lifecycle

Use this progression when the project needs it:

```text
engineering checks → smoke → frozen protocol → pilot → advancement decision
→ formal comparison → replication/ablation/stress/diagnostic → bounded conclusion
```

The protocol freezes the falsifiable hypothesis, comparator, one intended scientific delta, other frozen variables, metrics, inference unit, repetition policy, advancement/no-go rule, stopping rule, invalidation rule, artifacts, and claim ceiling.

A changed scientific variable receives a new experiment ID. A repeated execution of the same registered experiment receives a new run ID. Formal runs preserve the exact command, configuration identity, code identity, environment, randomness, raw metrics, and logs. A failed pilot stops expansion unless a separately registered method change and new experiment justify another test.

