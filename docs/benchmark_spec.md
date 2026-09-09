# DiagBench v0.2 Specification

## Purpose and status

DiagBench provides bounded, fully synthetic troubleshooting incident families
for studying privacy/utility trade-offs. Version 0.2 develops one family: a
repeated logical payment operation following a caller-visible timeout.

DiagBench v0.2 is designed to reduce answer leakage and support experimental
validity. It has not yet been validated with human diagnosticians or LLMs, and it
does not establish that its evidence is representative of production incidents.

## Oracle and model-visible boundary

DiagBench distinguishes benchmark oracle information from model-visible
evidence.

An `Incident` is the complete research definition. It contains internal labels,
structured ground truth, sensitive-field classifications, diagnostic invariants,
expected evidence, difficulty, and generation metadata in addition to the
evidence itself. It must never be serialized directly into an evaluation prompt.

`Incident.model_view()` constructs the complete model-visible representation.
A `ModelView` contains only:

- the user-like troubleshooting question;
- structured evidence; and
- log evidence.

The model view excludes the incident ID, title, category, description, ground
truth, expected evidence, invariants, sensitive-field policies and rationales,
difficulty, and metadata. Future evaluation code must consume `ModelView`, not
`Incident`.

## Structured ground truth

Oracle ground truth records separately:

- observed outcome;
- initiating trigger;
- failure mechanism;
- affected component;
- whether one logical operation was repeated; and
- an optional human-readable explanation.

This representation is intended to support future component-level scoring. No
scoring implementation is included in v0.2.

## Evidence references and diagnostic invariants

An `EvidenceReference` identifies a source, an exact selector, and an optional
field. Every structured row and log has a neutral, non-sensitive `evidence_id`
used only as stable provenance; references select by that value rather than by a
field that a future privacy transformation may change. Every reference must
resolve to exactly one element in its incident instance.

A diagnostic invariant contains a relation, specifically selected operands, an
expected property, a necessity classification, and an oracle-only description.
The representation supports positive relations such as equality and ordering as
well as negative relations such as inequality and all-distinctness. Negative
relations are required because a transformation may be harmful either by
destroying a real relationship or by creating a false one.

Necessity has three levels:

- `essential`: required for the intended evidence-based diagnosis or for avoiding
  a competing interpretation;
- `supportive`: corroborating but not required; and
- `discardable`: deliberately unnecessary literal or exact information.

The schema describes these relationships but does not yet transform evidence.

## Incident-family guarantees

Every Incident 001 instance has the same structured root cause. Its generator
varies bounded nuisance properties including population size, neutral IDs,
fictional identities, amounts, time origin, response/re-arrival timing, number
and placement of unrelated payments, service aliases, log wording, and unrelated
warnings.

Each instance guarantees:

- exactly two successful payment records for the target logical request;
- exactly one request associated with more than one payment record;
- a first request receipt and write, a caller-visible timeout, a second receipt
  for the same request, and a second write;
- distinct transport and payment identifiers for the two arrivals;
- several unrelated successful operations with distinct request identifiers;
- one benign timeout-and-rearrival sequence that produces only one payment;
- no diagnosis-bearing labels in model-visible identifiers or messages;
- fictional identity conventions; and
- deterministic generation for a fixed seed.

These construction guarantees do not demonstrate diagnostic realism or model
performance.

## Development, validation, and evaluation seeds

Seed ranges are separated to reduce direct tuning against evaluation instances:

| Split | Inclusive seed range | Intended use |
|---|---:|---|
| Development | 1000–1999 | Generator development and transformation debugging |
| Validation | 2000–2999 | Protocol and parameter selection |
| Retired | 10000–10999 | Never use for final evaluation; mechanically audited before any LLM run |
| Held-out evaluation | 20000–20999 | Final evaluation after protocol decisions are frozen |

The checked-in canonical example uses development seed `1001`. Seeds 10000–10999
were retired before any LLM evaluation because instances from that range had
been mechanically generated during construction auditing. Retired seeds cannot
be invoked by the evaluation runner. Seeds outside all ranges are marked
`unassigned`.

New held-out seed values and generated model views must not be inspected while
tuning prompts, evaluation code, or future transformations. The ranges are a
partitioning convention, not evidence that instances are statistically
independent.

## Serialization and versioning

Incident definitions and model views serialize to ordinary JSON. Oracle evidence
references contain instance-specific neutral selectors and remain stable for a
fixed seed. The canonical JSON fixture must equal generator output for its seed.

Schema and benchmark versions are recorded separately in oracle metadata. Any
change to generation distributions, model-visible evidence, invariant semantics,
or split policy requires review and a version update.
