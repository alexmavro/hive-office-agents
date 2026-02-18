# skills/_user/

Custom skills created by or for this specific user.

These ARE user data — factory reset wipes this directory.

## Structure

Each skill gets its own subfolder:
```
_user/
  {skill-name}/
    SKILL.md      # documentation (what it does, when to use it, how to invoke)
    skill.py      # implementation (optional — can be inline in SKILL.md)
```

## Metadata

All skills (system + user) are registered in `skills_registry.json` one level up.
The registry tracks: name, description, confidence, usage count, last used.
