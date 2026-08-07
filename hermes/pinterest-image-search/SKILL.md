# Pinterest Image Search

Use ClipSearch whenever the user asks for visual reference images, photos, real-world image examples, aesthetic references, people, locations, objects, scenes, backgrounds, thumbnail reference material, or similar imagery.

## Search

Run:
```bash
clipsearch pinterest search "<descriptive query>" --limit 10 --json
```

Read the returned JSON before deciding which image to download. Prefer descriptive searches rather than vague one-word queries.

Example:
- Instead of: `"Tokyo"`
- Use: `"Tokyo Shibuya neon street night photography"`

## Download one result

Run:
```bash
clipsearch pinterest download \
  --query "<same query>" \
  --index <result number> \
  --output <working directory> \
  --json
```

## Download several candidates

Run:
```bash
clipsearch pinterest fetch \
  "<descriptive query>" \
  --limit 5 \
  --output <working directory> \
  --json
```

## Rules

- Preserve `pin_url` as the source.
- Do not claim Pinterest images are copyright-free.
- Do not claim ownership of downloaded images.
- Prefer higher-resolution images where available.
- Search several candidates when quality matters.
- Refine the query if results are weak.
- Do not repeatedly download the same image unnecessarily.
- When presenting an image to a user, retain its source metadata when possible.
