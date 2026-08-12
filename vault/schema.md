# Schema Specification: London Pubs Wiki (v1.0.0)

This schema governs the data format, structural rules, and indexing taxonomy for all markdown pages in the London Pubs Wiki repository. All automated LLM curation and manual edits must conform to these definitions.

---

## 1. Directory Architecture

```text
london-pubs-wiki/
├── raw/                         # Unstructured inputs and json files (menus, photos, text transcripts)
└── wiki/                        # Production wiki pages
    ├── index.md                 # Primary directory and master search index
    ├── log.md                   # Chronological ledger of LLM updates & edits
    ├── pubs/                    # Individual pub profile pages
    ├── locations/               # London boroughs and neighborhoods
    └── features/                # Beverages, Foods, Entertainment and Ambience

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
location: "[[location_holborn]]"
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
- [[feature_cosy]]
- [[feature_guinness]]

## Location 
[[location_holborn]]


```

### Type D: Index Page (`wiki/index.md`)
This page contains a list of all pubs, a list of all locations, a list of all features. 
Updates to this page must preserve the existing lists of pubs locations and features while just adding any new information to the lists. 

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

## Locations
- [[location_euston]]
- [[location_marylebone]]

## Features
- [[feature_cosy]]
- [[feature_guinness]]

```
### Type E: Log Page (`wiki/log.md`)
Chronological list of wiki updates.

```markdown
---
id: "log"
title: "London Pub Log"
type: "log"
---

# London Pub Log

## 1. Change Log
- **2026-07-28**: Ingested `raw/TheOldBankOfEngland.md` to create [[pub_the_old_bank_of_england]]. Updated wiki/index.md to include the pub in the 'Pubs' section.

```

### Type B: Location Page (`wiki/locations/[location-name].md`)
Identifies a location in London. Contains a list of pubs that are in that location. When updating the list of pubs the exisiting pubs must be reserved. 

```markdown
---
id: "location_soho"
title: "Soho"
type: "location"
---

# Soho


##  Summary
Characterized by high-footfall, historic corner pubs often featuring external vertical tiles and large gin selections. High concentration of theater-district patronage.

##  Pubs
- [[pub_the_french_house]]: Famous for serving beer only in half-pints.
- [[pub_the_coach_and_horses]]: Known for its historic journalist clientele and singalongs.

```

### Type C: Feature Page (`wiki/features/[feature-name].md`)
Defines a feature that a pub may have. Contains a list of all pubs that have this feature. When updating the list of pubs must be preserved.

```markdown
---
id: "feature_cosy"
title: "Cosy"
type: "feature"
---

# Cosy

##  Summary
Cosy pubs are a nice intimate place to meet with friends.

## Pubs
- [[pub_the_princess_louise]] (Holborn) features exceptional preserved Victorian booths.
- [[pub_the_antelope]] (Belgravia) contains a functional historic snug space.

```

---

## 3. Validation & Quality Rules

To maintain high data integrity, the LLM curation agent must run the following verification checks during every compilation loop:

1. **Bi-directional Linking Rule:** If a pub page links to a location (e.g., `[[location_holborn]]`), the corresponding location page *must* list that pub under its "Pubs" section. If a pub page links to a feature (e.g.,'[[feature_cosy]]'), the corresponding feature page *must* list that pub under it's "Pubs" section.
2. **Naming Convention:** All internal system IDs and markdown filenames must be entirely lowercase, using underscores instead of spaces (e.g., `pub_the_black_friar.md`).
3. **Sourcing Requirement:** A pub entry cannot be created without at least one underlying reference entry inside the `raw/` directory or an official heritage registry ID.
4. **Indexing Requirement:** The index page must contain links to all pubs to all features and to all locations. Updates to the index page must preserve existing pub, feature and location links. 


---

## 4. Repository Maintenance Rules

The wiki must always remain internally consistent. Any operation that creates, renames, deletes, or modifies a page must also update all affected index files. 
Do not copy example content from the schema into real pages. 

### 4.1 Mandatory Update Rule

Whenever any page is created, modified, renamed, or deleted, the LLM must determine whether any repository index pages require updating.

The following pages are mandatory maintenance targets:

- `wiki/index.md`
- `wiki/log.md`
- Any linked location pages
- Any linked feature pages

These updates are part of the same operation and must never be skipped.

---

### 4.2 Index Update Rules

Whenever a new pub page is created:

1. Add the pub to  the pubs section of the `wiki/index.md` preserving existing pubs in that list.
2. Add the pub to the pubs section of its location page preserving existing pubs in that list.
3. Add the pub to the features pages in the pubs section preserving the exisiting pubs links in that list.
4. Keep entries alphabetically sorted.

Whenever a pub is renamed:

- Update every `[[pub_*]]` reference.
- Rename the markdown filename.
- Update the index.
- Update every location page.

Whenever a pub is deleted:

- Remove it from every index.
- Remove all incoming links.
- Record the deletion in the log.

---

### 4.3 Log Update Rules

Every successful repository modification must append a new entry to `wiki/log.md`.

Each log entry must contain:

- Date
- Operation
- Pages modified
- Reason

Example:

- **2026-08-02**
  - Operation: Create Pub
  - Created: `wiki/pubs/the_black_friar.md`
  - Updated:
    - `wiki/index.md`
    - `wiki/locations/blackfriars.md`
    - `wiki/log.md`
  - Source: `raw/the_black_friar.txt`

---

### 4.4 Atomic Commit Rule

A repository update is considered incomplete unless every required maintenance page has also been updated.

Creating a pub page without updating:

- `wiki/index.md`
- `wiki/log.md`
- linked location pages

is considered a validation failure.

---

### 4.5 Validation

After every write operation the LLM must verify:

- [ ] New page exists.
- [ ] `wiki/index.md` contains the page.
- [ ] `wiki/log.md` contains a new entry.
- [ ] Every linked location references the page.
- [ ] Every internal wiki link resolves.
- [ ] No duplicate IDs exist.