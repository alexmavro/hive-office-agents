# skills/

Executable capabilities — custom tools created for this user.

## Structure

```
skills/
  _system/              # built-in skills shipped with every Queen instance
  _user/                # custom skills created for this specific user
  skills_registry.json  # metadata about all skills (name, purpose, confidence)
```

## skills_registry.json format

```json
{
  "skills": [
    {
      "name": "deploy_service",
      "description": "Deploy a Docker service to the VPS",
      "location": "_user/deploy_service/",
      "confidence": "HIGH",
      "created_at": "2026-02-18T10:00:00Z",
      "last_used": "2026-02-18T10:00:00Z",
      "use_count": 5
    }
  ]
}
```

## Rules

- `_system/` is read-only (never modified by the Queen)
- `_user/` grows as the Queen creates new skills
- Factory reset clears `_user/` and `skills_registry.json` (keeps `_system/`)
- **`_user/` is user data** — factory reset wipes it
