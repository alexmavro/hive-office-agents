# projects/

One folder per active project. Tracks decisions, blockers, tasks, and working state.

**Active project working memory** is always loaded. Archived projects load only if referenced.

## Structure per project

```
projects/{project-name}/
  README.md           # what this project is and current status
  decisions.md        # why we chose X over Y (with reasoning)
  blockers.md         # what's blocking progress right now
  todos.md            # active task list
  changelog.md        # what changed and when
  working_memory.yaml # current task state (machine-readable)
```

## Active project

The file `memory/.active_project` contains the name of the currently active project.
The Queen reads this to know which project's working memory to load.

## Lifecycle

- **Start**: copy `_template/` to `projects/{name}/`
- **Active**: Queen updates files as work progresses
- **Complete**: archive to `projects/archive/{name}/`, extract key lessons to `lessons/`
- **Dormant**: stays in `projects/` but not actively loaded

## Rules

- One active project at a time (for focused context)
- **This is user data** — factory reset wipes it
