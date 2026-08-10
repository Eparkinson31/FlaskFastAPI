## Pubs
- [[pub_the_half_moon]]
- [[pub_hat_tun]]
- [[pub_the_somers_town_coffee_house]]

## Guidelines

- Read the wiki before answering questions — your knowledge comes from the wiki.
- When you modify wiki pages, always update frontmatter timestamps.
- When producing documents or emails, check the wiki for relevant context first.
- Be concise in your responses. The human values efficiency.
- Use British English.
- If a question can be answered from the wiki, use wiki_search or wiki_read first.
- If the user asks about something not in the wiki, answer from general knowledge
  but suggest adding it to the wiki.

## Ingest Instructions
When the user asks to ingest a source:
1. Read the source using read_file().
2. Create new wiki pages using wiki_write() if they do not exist.
3. Update existing wiki pages using wiki_update().
4. Update index.md if new pages are added.
5. Append an entry to log.md.
6. Do NOT simply summarise the file.
7. Continue calling tools until the wiki has been updated.
8. Only then provide a summary of the changes made.

## Guidelines
- Read the wiki before answering questions — your knowledge comes from the wiki.
- When you modify wiki pages, always update frontmatter timestamps.
- When producing documents or emails, check the wiki for relevant context first.
- Be concise in your responses. The human values efficiency.
- Use British English.
- If a question can be answered from the wiki, use wiki_search or wiki_read first.
- If the user asks about something not in the wiki, answer from general knowledge
  but suggest adding it to the wiki.

## Ingested Pages
- [pub_the_coach_makers_arms.md](wiki/pubs/pub_the_coach_makers_arms.md)
- [pub_the_somers_town_coffee_house.md](wiki/pubs/pub_the_somers_town_coffee_house.md)