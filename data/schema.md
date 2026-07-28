# Schema Specification: London Pubs Wiki (v1.0.0)

This schema governs the data format, structural rules, and indexing taxonomy for all markdown pages in the London Pubs Wiki repository. All automated LLM curation and manual edits must conform to these definitions.

---

## 1. Directory Architecture

```text
london-pubs-wiki/
├── raw/                         # Unstructured inputs (menus, photos, text transcripts)
└── wiki/                        # Production wiki pages
    ├── index.md                 # Primary directory and master search index
    ├── log.md                   # Chronological ledger of LLM updates & edits
    ├── pubs/                    # Individual pub profile pages
    ├── areas/                   # London boroughs and neighborhoods
    └── features/                # Beverages, Foods, Entertainment and Ambience

---

## 2. Page Templates & Schemas

### Type A: Pub Profile Page (`wiki/pubs/[pub-name].md`)
Every pub profile must use this exact frontmatter block and structural layout. Missing keys must be explicitly marked as `null`.

```markdown
---
id: "pub_ye_olde_mitre"
title: "Ye Olde Mitre"
type: "pub"
area: "[[area_holborn]]"
borough: "London Borough of Camden"
established: 1546
listed_status: "Grade II*"
closest_station: "[[concept_tube_chancery_lane]]"
coordinates: "51.5183° N, 0.1084° W"
last_updated: 2026-07-28
---

# Ye Olde Mitre

## 1. Executive Summary
A hidden historic tavern located in Ely Place, famous for its Elizabethan origins and challenging hidden alleyway access. 

## 2. History & Lore
Originally built in 1546 for the servants of the Bishops of Ely. The pub features a preserved cherry tree trunk built into its structure, around which Queen Elizabeth I is historically rumored to have danced.

## 3. Architectural & Design Features
- **Layout:** Small front bar, separate back room, and an outdoor alleyway standing area.
- **Interior:** Wood-paneled walls, historical framing, and leaded glass windows.
- **Key Artifacts:** The cherry tree support beam in the corner of the main bar area.

## 4. Beverage & Food Program
- **Tied or Independent:** Independent (Managed by Fuller's).
- **Core Beer Offering:** Focus on traditional cask ales, specifically [[brewery_fullers_london_pride]] and rotating seasonal guests.
- **Food style:** Traditional bar snacks only; famous locally for its toasted sandwiches (toasties).

## 5. Logistics & Atmosphere
- **Vibe:** Quiet, historical, conversational (strictly no music or televisions).
- **Peak Times:** Extremely busy post-work on Thursday and Friday evenings with City professionals.
- **Accessibility Access:** Extremely tight doorways and step-down entryways; not easily wheelchair accessible.

## 6. References & Sources
- Data compiled from `raw/transcript_ely_place_tour.txt` (Section 3).
- Verification via Historic England list entry ID: 1113038.
```

### Type B: Area Profile Page (`wiki/areas/[area-name].md`)
Defines the spatial clustering of pubs to power geographic discovery loops.

```markdown
---
id: "area_soho"
title: "Soho"
type: "area"
borough: "City of Westminster"
underground_lines: ["Central", "Northern", "Bakerloo", "Elizabeth"]
---

# Soho

## 1. Context & Boundaries
Soho is bounded by Oxford Street to the north, Regent Street to the west, Charing Cross Road to the east, and Shaftesbury Avenue to the south. Historically the epicenter of London’s bohemian and nightlife culture.

## 2. Pub Density & Characteristics
Characterized by high-footfall, historic corner pubs often featuring external vertical tiles and large gin selections. High concentration of theater-district patronage.

## 3. Notable Indexed Pubs
- [[pub_the_french_house]]: Famous for serving beer only in half-pints.
- [[pub_the_coach_and_horses]]: Known for its historic journalist clientele and singalongs.

## 4. References & Sources
- Spatial data derived from `raw/london_borough_maps_2024.json`.
```

### Type C: Concept Page (`wiki/concepts/[concept-name].md`)
Defines architectural styles, historical terminology, beer types, and cultural quirks.

```markdown
---
id: "concept_snug"
title: "The Snug"
type: "concept"
historical_period: "Victorian"
---

# The Snug

## 1. Definition
A small, private room or screened area historically found in British pubs. 

## 2. Cultural & Architectural Function
Snugs were designed for patrons who preferred not to be seen in the public bar. They typically featured a higher price per pint, a private service hatch directly to the bar, and frosted glass. Historically favored by local politicians, lovers, or women during the Victorian era.

## 3. Remaining Examples in London
- [[pub_the_princess_louise]] (Holborn) features exceptional preserved Victorian booths.
- [[pub_the_antelope]] (Belgravia) contains a functional historic snug space.
```

---

## 3. Validation & Quality Rules

To maintain high data integrity, the LLM curation agent must run the following verification checks during every compilation loop:

1. **Bi-directional Linking Rule:** If a pub page links to an area (e.g., `[[area_holborn]]`), the corresponding area page *must* list that pub under its "Notable Indexed Pubs" section.
2. **Naming Convention:** All internal system IDs and markdown filenames must be entirely lowercase, using underscores instead of spaces (e.g., `pub_the_black_friar.md`).
3. **Sourcing Requirement:** A pub entry cannot be created without at least one underlying reference entry inside the `raw/` directory or an official heritage registry ID.

---