# 06. Evidence: what proposals, asks and results must show

The user decides from evidence they can see or hear in a few seconds. Text alone is not enough.
Why: the user judges by eye (or ear) at normal size. A change that moves the numbers but not the picture reads as
"no change" and costs a round.

The project decides what evidence means for it at deployment (`12_deploy_new_project.md`): pictures, short clips,
audio, a diff, a metric table. The rules below are written for pictures; apply the same idea to the project's medium.

## Proposals: show the problem

`visual:` is mandatory. A proposal picture shows:
- the current state, at the spot, marked (circle, arrow, box);
- the reference, when there is one (a photo, a spec, a design, a recording), at the same spot;
- a cheap mock or a quick lab A/B, if there is one.

One sheet with tiles side by side is better than three files. Label each tile.

## Asks: show the choice

Every ask carries a picture, without exception. The picture shows each option the ask offers, side by side, with the
same labels as `--options`. Put your own pick first and say why in one line.

## Aim before you work

When a card is not pinned to an exact spot (a picture sent in a session, "these patches", a vague area), post one marked
picture first: "this is what I'll change". It is cheap, needs no shared resource, and catches a misread before hours are
spent. If the user's notes carry hit data (object, material, position), use it.

## Results: A/B the way the user experiences it

A result is an A/B sheet: reference | before | after (or before | A | B | C for variants).
- **Same view.** Every column shows the same camera, framing, crop, time and settings. Only the change differs.
- **As experienced.** Capture the way the user will meet the change: the shipped product's own settings (automatic
  exposure, the real mix, the real device), not a frozen debug view. If there is a shared capture helper, use it.
- **Check the lab first.** Before making any A/B, compare the lab's "before" with the shipped product at the same view.
  If they differ beyond a small tolerance (set per project: brightness, colour, loudness, layout), fix the lab first.
  Why: a lab that doesn't match the product produces A/Bs that lie; several rounds can be lost to that.
- **Settled state.** Some things change with time or use (caches warming, textures streaming in, adaptive settings).
  Capture after they settle, the way the user sees them after a while, and say so on the sheet.
- **Never correct by hand.** Don't adjust exposure, volume or crop on one side to make the pair look fairer. If the
  pair isn't comparable, fix the capture.
- **Lead with the detail.** Put the same 1:1 crop of the spot first in every column, then the full frames, then the
  numbers.

## Strengths you can see

Offer strengths that span to a clearly visible end. The strongest option should reach the reference (or clearly
overshoot it), not only take a safe small step. When the user says "I can't see a difference", the next round goes
much further, and the sheet shows the crop at full size.

## Numbers

Numbers support pictures; they don't replace them. When there are numbers, give before / after / reference and the
tolerance. Say which direction is better. For performance work: the median and the worst case, at named spots, on the
shipped product.

## Side effects

If the fix is a rule (it changes every instance of something), show two or three other places it touches, or say
"nothing else changes" and how that was checked.

## Judge the shipped thing

A check on a development copy does not count as shipped. Every gate, capture and audit after a build looks at the
built product. Why: a build step can silently ship a stale copy (a level, a config, an asset) while the development copy
looks right.

## The reference is a guide

When a reference exists (a photo, a recording, a design), it guides the judgement; it is not a 1:1 target.
The user judges by eye. A studio does not chase a number the user didn't ask for, and does not override a look the
user chose because a measurement disagrees.

## Spend the scarce resource last

- Diagnose from data first: logs, masks, hit data, a debug view that shows every layer at once. Then confirm with one
  capture, not ten.
- Do the CPU setup before taking the shared resource; release it straight after the capture.
- Batch variants into one job. Diagnosis needs one or two views.
- Skip warm-up work when only parameters changed.

## Evidence checklist

| Item | Proposal | Ask | Result |
|---|---|---|---|
| picture of the spot, marked | required | required | required |
| reference at the same spot | if one exists | if relevant | if one exists |
| options side by side, labelled as `--options` | - | required | for variants |
| same view in every column | - | - | required |
| captured as the user experiences it, lab checked | - | - | required |
| strongest option clearly visible | - | - | required |
| side effects or "nothing else changes" | if a rule | - | required |
| numbers with tolerance | if useful | - | if useful |
| file in `studios/<key>/cards/`, named after the card | required | required | required |
