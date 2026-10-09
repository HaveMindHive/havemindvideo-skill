# Replicate Video Generation Reference

Assumes `REPLICATE_API_TOKEN` is set and you're using the `replicate` Python SDK (`pip install replicate`).

## Model IDs drift — always verify before trusting a hardcoded one

Replicate model IDs and their "latest version" change over time. Before relying on an id you found in a doc (including this one), check it's current:

```python
import replicate
m = replicate.models.get("kwaivgi/kling-v2.5-turbo-pro")
print(m.latest_version.id)
```

If a call 404s, that's usually why — don't assume something else is broken.

## kling (`kwaivgi/kling-v2.5-turbo-pro`)

Current id as of 2026-10-09. Supports image-to-video with a **start + end keyframe pair**, which gives much better control over motion and identity than a single start frame alone.

Introspect the live schema before guessing field names — exact inputs vary by model and change over time:

```python
import json
v = replicate.models.get("kwaivgi/kling-v2.5-turbo-pro").latest_version
print(json.dumps(v.openapi_schema["components"]["schemas"]["Input"]["properties"], indent=2))
```

Key gotchas, all hit in production:

- **`duration` must be an `int`, not a string.** Passing `"5"` instead of `5` causes a 422 validation error from the API. Easy to get wrong if you're building the input dict from string-typed CLI args.
- **`aspect_ratio` is silently ignored whenever `start_image` is set.** Kling infers the aspect ratio from the reference image itself. If you're doing **text-to-video with no reference image**, you must explicitly set `aspect_ratio` (e.g. `"9:16"`) yourself — otherwise it silently defaults to `16:9` landscape. This is easy to miss because there's no error, just the wrong output dimensions on shots you expected to be vertical.
- **Pass images as open file handles, not base64 data-URIs.** `input={"start_image": open(path, "rb"), "end_image": open(path2, "rb")}` — the SDK uploads the file and substitutes a URL. Embedding two images as base64 `data:` URIs in the request body bloated the payload past a client-side read timeout and caused repeated silent failures (`requests.exceptions.ReadTimeout` or similar, several retries, no useful error from Replicate's side since the request never really landed). File-handle uploads fixed it immediately and are the documented-normal way to pass media to Replicate anyway.

### Text-to-video with no reference image is unreliable for named/recurring characters

Confirmed in production: a two-person dialogue scene generated with **no reference image**, driven purely by a detailed text description of both characters, rendered completely wrong people — different ethnicity, wrong hair, wrong everyone, despite a prompt that named every physical detail. This gets *worse*, not better, as you add more people to the frame. The model has nothing to anchor identity to and will invent faces from the text alone.

**Always generate and pass a reference image** (see `replicate-image.md` for how to get a character-consistent one) rather than relying on text-only generation for anyone who needs to look the same shot to shot.

### End-to-end example: 5s clip from a start+end keyframe pair

```python
import replicate, requests

model = replicate.models.get("kwaivgi/kling-v2.5-turbo-pro")

with open("start_frame.png", "rb") as start, open("end_frame.png", "rb") as end:
    output = replicate.run(
        model,
        input={
            "prompt": "Two people sit at a small table, candlelight, slow natural movement. No on-screen text, no watermark.",
            "start_image": start,
            "end_image": end,
            "duration": 5,          # int, not "5"
            # aspect_ratio intentionally omitted — inferred from start_image
        },
    )

url = str(output[0]) if isinstance(output, list) else str(output)
video_bytes = requests.get(url).content
with open("shot.mp4", "wb") as f:
    f.write(video_bytes)
```

For text-to-video (no reference image), the only change is dropping `start_image`/`end_image` and adding `aspect_ratio` explicitly:

```python
output = replicate.run(model, input={
    "prompt": "...",
    "duration": 5,
    "aspect_ratio": "9:16",   # required here — no image to infer it from
})
```

## Other video models worth knowing

- **`minimax`** — set `prompt_optimizer: True` in the input to let the model rewrite/improve your prompt before generating.
- **`luma-ray` family** (various Luma AI models on Replicate) — different motion characteristics than kling, worth a look for b-roll/establishing shots that don't need tight character control.
- **`runwayml/gen4-turbo`** — another image-to-video option; check current schema the same way as above before using.

## Verify what you actually got

Don't trust a clip just because the API call returned 200. At minimum, `ffprobe` the result before using it downstream:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of default=noprint_wrappers=1 shot.mp4
```

Check the resolution/aspect ratio matches what you expected (especially after a text-to-video call where `aspect_ratio` had to be set manually) and the duration is sane.

## Alternative provider (not evaluated in depth)

**Google's Veo** (video) and **Nano Banana** (image) are reachable via an MCP server (`molkex/mcp-flow-google`) running on your own Google account, as an alternative to Replicate's hosted models. Not tested against this pipeline's specific needs (character identity locking, start/end keyframes) — worth investigating if Replicate access/cost is a constraint, but no specific guidance here beyond that it exists.
