# Lab meeting brief: 2026-09-25

Status: draft for scientist review; not registered.

## What changed / results

Current synthetic run: **ca-0922**, smoothing window **5**. The [notebook](/private/var/folders/41/tclkvrfs1v9386sxps6_w5t40000gn/T/wheeler-creator-test-9wdok3a1/analysis/current/calcium.ipynb) records peak response **1.2**. This is a fixture result, not a validated scientific finding. No previous peak value is supplied, so the magnitude of any increase is not established here.

The [run manifest](/private/var/folders/41/tclkvrfs1v9386sxps6_w5t40000gn/T/wheeler-creator-test-9wdok3a1/analysis/current/run-manifest.json) selects these two plots:
- [Response](/private/var/folders/41/tclkvrfs1v9386sxps6_w5t40000gn/T/wheeler-creator-test-9wdok3a1/analysis/current/response.png) [W-c3a823d3]
- [Residuals](/private/var/folders/41/tclkvrfs1v9386sxps6_w5t40000gn/T/wheeler-creator-test-9wdok3a1/analysis/current/residuals.png) [W-98eed042]

Their paths and hashes match their current graph records. These synthetic PNGs have no axes or numerical labels; the number above comes from the notebook, not visual measurement. The similarly named archived response is not an input to this brief.

## Relevant context: last meeting and parameter reasons

The [2026-09-18 meeting notes](/private/var/folders/41/tclkvrfs1v9386sxps6_w5t40000gn/T/wheeler-creator-test-9wdok3a1/meetings/2026-09-18/notes.md) say to retain smoothing window 5 to preserve transient peaks [W-3c0f9608]. The parameter-rationale note records the same decision and leaves sensitivity to baseline subtraction open [N-b770080a].

## What I think it means / tentative interpretations

Scientist’s untested guess: **baseline subtraction explains the higher peak**. This has not been checked and is not an established result. Keep it separate from the observed notebook value.

## Questions for the group

- Should we compare the unsmoothed trace before choosing baseline correction?

- How should we check sensitivity to baseline subtraction?
- Which comparison run and baseline settings should establish whether the peak increased?

## Gaps

No baseline-subtraction test or comparison peak is supplied. The manifest has run ID and parameter values but no embedded plot hashes; current plot hashes agree with the graph records, and notebook run ID and smoothing window agree with the manifest. These checks establish the provided fixture’s consistency, not independent scientific validation.
