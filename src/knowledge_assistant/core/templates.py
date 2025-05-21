"""Built-in note templates, ported verbatim from the original generator.
User-saved templates live in the `templates` table; these are the seed set."""

from __future__ import annotations

BUILTIN_TEMPLATES: dict[str, str] = {
    "basic": """# [Title]

## Table of Contents
- [Topic 1](#topic-1)
- [Key Points](#key-points)
- [Action Items](#action-items)

## Topic 1
[Content]

## Key Points
- [Item 1]
- [Item 2]
- [Item 3]

## Action Items
- [ ] [Action item 1]
- [ ] [Action item 2]
""",
    "meeting": """# Meeting: [Title]

**Date**: [YYYY-MM-DD]
**Time**: [HH:MM] - [HH:MM]
**Location**: [Location]

## Attendees
- [Name], [Role]
- [Name], [Role]

## Agenda
1. [Topic 1]
2. [Topic 2]

## Discussion
### [Topic 1]
- [Point 1]
- [Point 2]

### [Topic 2]
- [Point 1]
- [Point 2]

## Action Items
- [ ] [Action 1] (@[owner], Due: [date])
- [ ] [Action 2] (@[owner], Due: [date])

## Next Meeting
**Date**: [YYYY-MM-DD]
**Time**: [HH:MM]
""",
    "project": """# Project: [Title]

## Overview
[Project description]

## Objectives
1. [Objective 1]
2. [Objective 2]

## Timeline
- Start: [YYYY-MM-DD]
- End: [YYYY-MM-DD]

## Tasks
### Phase 1
- [ ] [Task 1]
- [ ] [Task 2]

### Phase 2
- [ ] [Task 1]
- [ ] [Task 2]

## Resources
- [Resource 1]
- [Resource 2]

## Notes
[Additional notes]
""",
    "research": """# Research: [Title]

## Overview
[Research description]

## Questions
1. [Question 1]
2. [Question 2]

## Sources
### [Source 1]
- Author: [Name]
- Date: [YYYY-MM-DD]
- Link: [URL]
- Key Points:
  - [Point 1]
  - [Point 2]

## Findings
1. [Finding 1]
2. [Finding 2]

## Conclusions
[Research conclusions]

## Next Steps
- [ ] [Step 1]
- [ ] [Step 2]
""",
    "study": """# [Title]

## Table of Contents
- [Topic 1](#topic-1)
  - [Subtopic 1.1](#subtopic-11)
  - [Subtopic 1.2](#subtopic-12)
- [Topic 2](#topic-2)
  - [Subtopic 2.1](#subtopic-21)
  - [Subtopic 2.2](#subtopic-22)

## Topic 1

### Subtopic 1.1
[Content]

### Subtopic 1.2
[Content]

## Topic 2

### Subtopic 2.1
[Content]

### Subtopic 2.2
[Content]

## Summary
- [Key point 1]
- [Key point 2]

## Questions for Review
1. [Question 1]
2. [Question 2]

## References
- [Reference 1]
- [Reference 2]
""",
}


def get_builtin(kind: str) -> str:
    return BUILTIN_TEMPLATES.get(kind, BUILTIN_TEMPLATES["basic"])
