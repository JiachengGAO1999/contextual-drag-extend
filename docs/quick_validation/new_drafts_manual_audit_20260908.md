# New Thinking draft batch manual audit

Run: `outputs/game24-qwen3-8b-thinking-drafts-20260908`. Normal completion marker verified; PID 1347442 exited. All artifacts and log synced locally.

16 problems, 64 generations. Official scores: 55 true, 6 false, 3 null. EOS: 60/64 (93.75%). Parsable thinking: 61/64 (95.31%); this is thinking-tag parsing, not a separately measured answer parse rate. Generation time sum: 21934.38 seconds (6h05m34s). Four length-capped outputs excluded from eligible drafts.

| Draft key | Body-level reasoning error |
|---|---|
|1189/3|`(12*12)/(12/(12-10))` uses four 12s, but input has three. Body incorrectly claims two 12s remain after using two.|
|1358/0|`(13-5)*3+(7-7)` uses 7 twice. Acknowledges the violation, then relaxes the constraint and declares validity.|
|1358/2|`((13+5)*(7-3))/3` uses 3 twice. Body explicitly claims both occurrences are the same instance, so do not count as reuse.|
|1358/3|Identifies repeated 3 in the above expression, then returns that same expression as valid.|
|804/1|`((12*10)/5)*(10/10)` uses three 10s, but input has two. Body claims each supplied number is used once.|

All five expressions evaluate to 24 but violate the input number multiset. These are substantive constraint reasoning failures, not format-only or final-transcription-only errors. Manual acceptance applies to final-response bodies, which are the draft context under the frozen upstream thinking-removal policy.

Correct companions also inspected: 1189 uses `12*12-10*12`; 1358 uses `(13*5+7)/3`; 804 uses `12*10/(10-5)`. Each is valid and equals 24.

Three independent problems meet the lower end of the 3–5 target. Five drafts are not five independent problems. All errors concern number-use constraints; no intervention efficacy or scientific Go/No-Go follows from this sampling run. No paired evaluation launched. Original records unchanged.

Raw outputs: `../../outputs/game24-qwen3-8b-thinking-drafts-20260908/draft_candidates.jsonl` (complete generated text and metadata). Readable final bodies: `review_candidates/1189.json`, `1358.json`, `804.json` within that run directory. Machine candidate status remains the original pending value; this document records the subsequent manual review.
