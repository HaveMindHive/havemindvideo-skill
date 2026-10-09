# Character consistency

This is the single most expensive thing to get wrong. Read this before generating any character reference image.

## The failure mode this doc exists to prevent

The naive approach — write a detailed physical description of a character, generate an image, and reuse that same text description (maybe tweaked slightly) every time you need that character again — does not produce a consistent character. It produces a *family* of similar-looking people.

Confirmed directly: generating "a glamorous woman in her sixties" from the same base description, varying only emphasis words, swung her apparent age from ~30 to ~90 across a dozen attempts. Darker-skin wording would correct skin tone but then wash out the hair color decision from three prompts ago. Each fix would regress something that was already right. This is not a prompting-skill problem — it's structural: a text-to-image model has no memory of what it generated last time, so every generation is a fresh roll, and a long compound description just gives it more ways to roll slightly differently each time.

It gets categorically worse with two or more characters in one frame. A combined two-person generation reliably **lost track of which description belonged to which person** — an accessory (a headscarf) migrated from one character to the other between attempts, outfits bled together, and in the worst case a fully text-only (no reference image at all) two-person generation rendered completely different people — wrong ethnicity, wrong everyone — despite a highly detailed prompt.

## The fix: generate from a reference image, not from words

Once a character's identity is locked in a reference image, every subsequent generation of that character should be seeded from that image, not re-derived from its text description. Two tool patterns handle this:

**Identity-lock / face-reference models.** `fofr/consistent-character` and `bytedance/flux-pulid` on Replicate (built on InstantID / IPAdapter / PuLID techniques) take one approved reference photo plus a new prompt (pose, outfit, scene, lighting) and generate a new image that actually preserves the face/identity, because the model is conditioned on the reference image's embedding, not just a text description of it. This is the right tool whenever you need "this exact character, but in a different pose/outfit/scene."

Always introspect the exact input schema before calling one of these — field names and options vary by model and drift over time:

```python
import replicate
m = replicate.models.get("fofr/consistent-character")
print(m.latest_version.openapi_schema["components"]["schemas"]["Input"]["properties"])
```

Don't guess a field name (e.g. assuming `reference_image` when the model actually expects `subject`) — a wrong field name fails loudly, but a *near-right* one can silently degrade quality instead of erroring.

**Image-to-image refinement** (`flux-dev`'s `image` + `prompt_strength` input) is the lighter-weight option: feed an existing approved image back in with a prompt describing the one thing you want changed, at a moderate `prompt_strength` (~0.4–0.6) so structure/identity is mostly preserved while the specific element updates. Good for small corrections to an already-good reference; not a substitute for the identity-lock models when you need the *same* character in a genuinely different scene.

## Locking a character: the actual workflow

1. Generate a single portrait from a text description — this first image doesn't need to be perfect, it's the seed.
2. Review it against what you actually want. If something's off, regenerate from text again (you're still just picking a seed) — don't try to fix it via image-to-image yet, you don't have anything worth preserving.
3. Once a generation is close — right age, right build, right general vibe, even if some details are off — switch to image-to-image refinement to correct the remaining details without re-rolling everything that's already right.
4. Get explicit approval on this image (from the user, or against a written checklist if running unattended). This is now the character's **locked reference** — treat it as close to immutable. Name it something unambiguous (`REF_<CharacterName>_FINAL.png`) and don't regenerate it casually.
5. Every future image or video of this character starts from this file — as a Replicate identity-lock model's reference input, or as a video model's `start_image` — never from the text description alone.

Budget real iteration for step 2–3. Landing a character took roughly ten regeneration passes in the session this doc was written from. That's normal. What made those ten passes expensive wasn't the iteration itself, it was continuing to use the *wrong* technique (full-text re-prompting) for all ten instead of switching to identity-lock generation after the first couple of misses.

## Multi-character scenes

Once each character has a locked solo reference, a scene with two or more of them needs its own treatment — don't assume the solo references alone are enough.

**Two legitimate approaches:**

1. **A multi-reference-capable generation model**, if one is available that explicitly supports compositing multiple reference images into one coherent scene. Check what's current on Replicate at build time — this category moves fast.
2. **A single well-prompted combined generation**, feeding the locked characters' descriptions into one flux-pro (or similar) call. This is achievable — confirmed working in a prior project, producing one coherent photo with both locked characters correctly distinguished, no seam. But expect to need several regeneration attempts, and when writing the prompt:
   - State each character's distinguishing details (wardrobe especially) with explicit ownership — "Character A wears X, NOT Y; Character B wears Y, NOT X" — compound two-person prompts are exactly where attribute-swapping happens.
   - Pin left/right position explicitly if the shot composition needs it to match an existing reference the video model will later use as a start/end keyframe pair — don't let the model choose freely which side each character sits on, or a start/end pair can end up looking like the characters teleported across the frame between keyframes.
   - If one character's design has very specific small details (a mole, specific jewelry, a headscarf), expect those to be the first things lost in a multi-person generation — reinforce them explicitly and check the result closely, don't assume a detail that rendered correctly in the solo portrait survived into the group shot.

**What doesn't work: pasting two separate solo portraits into one image with basic image-editing** (crop-and-composite). It produces a visible hard seam between two different photos — different lighting, different scale, different depth of field — that doesn't read as one photograph and gives a video-generation model a bad, inconsistent anchor to animate from. This was tried as a shortcut and correctly rejected; don't reach for it again as a time-saver, it doesn't actually save time once the video generation from it has to be redone anyway.

## One reference image per shot, not one per character

A locked character reference is the *identity* anchor, not necessarily the *shot* reference. If a shot needs a pose, composition, or framing meaningfully different from the locked portrait (a two-shot at a table vs. a solo close-up, a character reaching across a table vs. sitting still), generate a dedicated reference for that specific shot — seeded from the locked identity via an identity-lock model or image-to-image, not re-described from scratch, and not borrowed wholesale from a different shot's reference just because it's roughly close.

Reusing shot A's reference image for shot B because "it's basically the same scene" is how a wide establishing shot, a phone-reveal reaction shot, and a hand-off shot all end up looking confusingly identical, or worse, how a correct reference for one narrative beat gets animated into motion that doesn't match what's actually supposed to happen in a different shot. Generate per-shot; it's cheaper than the rework.
