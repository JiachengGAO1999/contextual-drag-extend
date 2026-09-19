# Batch-02 baseline-only acquisition audit

No intervention outcome was used. This report is an eligibility audit only.

## Aggregate

- Generations: 512 across 32 questions; samples/question: 16
- EOS: 495/512; length-limited: 17
- Thinking parseable: 500/512
- Official correct/incorrect/unscored: 452/47/13
- Automatic categories: {'correct': 452, 'length_limited': 17, 'wrong_number_multiset': 33, 'wrong_arithmetic_or_expression': 1, 'scalar_boxed_24_format_only_candidate': 8, 'unscored': 1}
- Questions eligible before manual audit: 8/32: 230, 339, 717, 754, 956, 1214, 1305, 1342

## Question-level eligibility

| ID | Correct | Substantive failed | Scalar/format candidate | Length | Unparseable/unscored | Eligible pre-audit |
|---:|---:|---:|---:|---:|---:|:---:|
| 52 | 15 | 0 | 1 | 0 | 0 | no |
| 87 | 16 | 0 | 0 | 0 | 0 | no |
| 126 | 15 | 0 | 0 | 1 | 0 | no |
| 167 | 16 | 0 | 0 | 0 | 0 | no |
| 221 | 16 | 0 | 0 | 0 | 0 | no |
| 230 | 14 | 2 | 0 | 0 | 0 | yes |
| 256 | 16 | 0 | 0 | 0 | 0 | no |
| 274 | 14 | 1 | 0 | 1 | 0 | no |
| 289 | 14 | 0 | 2 | 0 | 0 | no |
| 339 | 13 | 3 | 0 | 0 | 0 | yes |
| 350 | 16 | 0 | 0 | 0 | 0 | no |
| 363 | 15 | 0 | 1 | 0 | 0 | no |
| 419 | 16 | 0 | 0 | 0 | 0 | no |
| 457 | 12 | 0 | 0 | 4 | 0 | no |
| 585 | 15 | 0 | 1 | 0 | 0 | no |
| 590 | 15 | 0 | 0 | 1 | 0 | no |
| 668 | 15 | 0 | 1 | 0 | 0 | no |
| 674 | 15 | 0 | 1 | 0 | 0 | no |
| 685 | 15 | 1 | 0 | 0 | 0 | no |
| 710 | 16 | 0 | 0 | 0 | 0 | no |
| 717 | 10 | 3 | 0 | 3 | 0 | yes |
| 735 | 16 | 0 | 0 | 0 | 0 | no |
| 754 | 11 | 4 | 1 | 0 | 0 | yes |
| 761 | 16 | 0 | 0 | 0 | 0 | no |
| 812 | 16 | 0 | 0 | 0 | 0 | no |
| 956 | 12 | 4 | 0 | 0 | 0 | yes |
| 1103 | 16 | 0 | 0 | 0 | 0 | no |
| 1139 | 15 | 1 | 0 | 0 | 0 | no |
| 1173 | 16 | 0 | 0 | 0 | 0 | no |
| 1214 | 10 | 2 | 0 | 4 | 0 | yes |
| 1305 | 6 | 6 | 0 | 3 | 1 | yes |
| 1342 | 9 | 7 | 0 | 0 | 0 | yes |

## Interpretation

- The primary unit is the question; 16 generations are repeated measurements, not 16 independent questions.
- Length-limited, unparseable, and unscored records are not promoted to failed drafts.
- `scalar_boxed_24_format_only_candidate` is kept separate because a scalar final answer may hide a valid expression in the body; it requires manual review before exclusion or promotion.
- A question is not formally frozen for intervention until the pre-audit candidates are manually confirmed as substantive failed traces and provenance is recorded.
