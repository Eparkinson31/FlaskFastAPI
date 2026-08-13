# Schema Specification: London Pubs Wiki (v2.0.0)

This schema governs the data format, structural rules, and indexing taxonomy for all markdown pages in the London Pubs Wiki repository. All automated LLM curation and manual edits must conform to these definitions.

---

## 1. Directory Architecture

```text

├── raw/                         # Unstructured inputs and json files (menus, photos, text transcripts)
└── wiki/                        # Production wiki pages
    ├── index.md                 # Primary directory and master search index
    └── pubs/                    # Individual pub profile pages
    

---
```
## 2. Page Templates & Schemas

### Type A: Pub Profile Page (`wiki/pubs/[pub-name].md`)
Every pub profile must use this exact frontmatter block and structural layout. Missing keys must be explicitly marked as `null`.

```markdown
---
id: "pub_ye_olde_mitre"
title: "Ye Olde Mitre"
type: "pub"
location: "Holborn"
established: 1546
listed_status: "Grade II*"
longitude: -0.108129
latitude: 51.521754
last_updated: 2026-07-28 11:00:00
---

# Ye Olde Mitre

## Summary
A hidden historic tavern located in Ely Place, famous for its Elizabethan origins and challenging hidden alleyway access. 

## Features
- Cosy
- Guinness

## Location 
Holborn


```

### Type B: Index Page (`wiki/index.md`)
This page contains a list of all pubs. 
Updates to this page must preserve the existing lists of pubs. 

```markdown
---
id: "index"
title: "London Pub Index"
type: "index"
---

# London Pub Index

## Pubs 
- [[pub_the_french_house]]: Famous for serving beer only in half-pints.
- [[pub_the_coach_and_horses]]: Known for its historic journalist clientele and singalongs.

```

---

## 3. Validation & Quality Rules

To maintain high data integrity, the LLM curation agent must run the following verification checks during every compilation loop:

1. **Naming Convention:** All internal system IDs and markdown filenames must be entirely lowercase, using underscores instead of spaces (e.g., `pub_the_black_friar.md`).
2. **Indexing Requirement:** The index page must contain links to all pubs. Updates to the index page must preserve existing pubs. 


---

## 4. Repository Maintenance Rules

The wiki must always remain internally consistent. Any operation that creates, renames, deletes, or modifies a page must also update all affected index files. 
Do not copy example content from the schema into real pages. 

### 4.1 Mandatory Update Rule

Whenever any source is ingested, modified, renamed, or deleted, the LLM must determine whether any repository index pages require updating.

The following pages are mandatory maintenance targets:

- `wiki/index.md`

These updates are part of the same operation and must never be skipped.

---