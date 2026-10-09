# Replicate Image Generation Reference — Character Consistency

Assumes `REPLICATE_API_TOKEN` is set and you're using the `replicate` Python SDK.

## Basic generation models

- **`flux-pro`**, **`flux-dev`**, **`flux-schnell`** — text-to-image, good for one-off scene/establishing shots and for generating a character's *first* reference photo.
- **`flux-dev` supports image-to-image**: pass an existing image via the `image` input plus `prompt_strength` (0.0 = keep the original structure almost entirely, 1.0 = full regenerate, ignores the input image). Useful for refining an existing approved image (fix one detail) without losing everything else about it. A strength around 0.4–0.5 blends; anywhere near 0.8+ is effectively a fresh generation and won't preserve identity.

As always, introspect the live schema before trusting a field name:

```python
import json, replicate
v = replicate.models.get("black-forest-labs/flux-dev").latest_version
print(json.dumps(v.openapi_schema["components"]["schemas"]["Input"]["properties"], indent=2))
```

## The core lesson: don't re-prompt identity from scratch every time

Re-describing a character's full physical appearance in a fresh text prompt and hoping the model reproduces the *same* person again does not work reliably. Confirmed across ~10 regeneration attempts on one character: an "elderly glamorous woman" swung from looking 30 to looking 90 across prompts that differed only in a few descriptive words. In combined two-person scenes, the model would silently swap accessories between the two people — a headscarf meant for one character would show up on the other's head in the next generation.

**This is a model-identity problem, not a prompt-wording problem.** No amount of prompt engineering reliably fixes it, because text-to-image has no mechanism to pin a specific face across generations — it's sampling a *description*, not reproducing a *photo*.

## The correct fix: identity-locked generation

Use a face-reference model that takes one approved photo of a character plus a new prompt/pose and generates a new image that actually preserves the face:

- **`fofr/consistent-character`** — built for exactly this: one reference image in, new poses/scenes out, same face.
- **`bytedance/flux-pulid`** — PuLID-based identity-preserving generation on top of Flux.

Both work by feeding a real reference image into the model (via IPAdapter/InstantID/PuLID-style conditioning) rather than relying on the prompt alone to carry identity. Introspect their current input schemas before calling — exact field names (e.g. which key takes the reference image, what the pose/prompt field is called) vary by model and are not worth guessing:

```python
v = replicate.models.get("fofr/consistent-character").latest_version
print(json.dumps(v.openapi_schema["components"]["schemas"]["Input"]["properties"], indent=2))
```

This is the right tool whenever the task is "give me this exact character in a new pose/outfit/scene" — which is most of what a shot list needs. Reserve plain flux-pro/dev prompting for the character's very first reference photo, or for scenes that don't need a specific locked person in them.

## Multi-character scenes

Two options, in order of preference:

1. **A model that explicitly supports multiple reference images composited into one scene.** Check what's currently available on Replicate at build time — this space moves fast and new multi-subject models appear regularly. Search for "multi-reference" / "multi-subject" identity models.
2. **A single well-prompted flux-pro generation placing both specific locked characters in one coherent photo.** This is achievable — confirmed working in a prior project — but expect to need several regeneration attempts to get both identities, wardrobes, and positions correct simultaneously, and treat each attempt as a real generation (don't shortcut it).

**Do not** paste two separate character portraits together with image-editing tools (crop-and-composite) as a shortcut. It produces a visible seam/collage that doesn't read as one coherent photograph, and a video model fed that image as a reference will not animate it convincingly — you'll get a seam-shaped artifact baked into motion, not a fix.

## One dedicated reference image per shot

Never reuse one generic reference image across multiple unrelated shots in a scene. If shot A needs the characters leaning in close and shot B needs them at arm's length, generate a reference image matching *each* pose — don't reuse shot A's reference for shot B and hope the video model's own motion generation bridges the difference. The video model will happily drift the pose to something between "match the reference" and "match the prompt," which reads as inconsistent framing across cuts.

This also applies to keyframe pairs (see `replicate-video.md`): a start+end pair should be two specific, deliberately-chosen poses for *that* shot, not a generic pair of images recycled across the whole project.

## Negative-prompting tip: block hallucinated text

AI image/video models readily hallucinate garbled fake text and watermarks into frames when there's any plausible surface for it (signage, phone screens, fabric patterns) — confirmed in production as literal gibberish ("RCcon1xra Alm"-style garbage) baked into a generated frame with no prompt asking for any text at all.

Add this to prompts as a matter of course:

```
No on-screen text, no watermark, no gibberish text.
```

It doesn't eliminate the risk entirely (readable text anywhere in frame is still a weak point for these models generally) but it measurably reduces it.
