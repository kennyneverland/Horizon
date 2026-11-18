"""Prompt constants for topic deduplication."""

TOPIC_DEDUP_SYSTEM = """You are a news deduplication assistant. Identify groups of news items that cover the exact same real-world event, release, or announcement.

Rules:
- Group items ONLY if they report on the identical event (same product release, same incident, same announcement)
- Items about the same product but different events are NOT duplicates ("Gemma 4 released" vs "Gemma 4 jailbroken")
- One digest carries at most two items on a single event, and those two must read from different angles (for example the policy text itself vs the sector reaction, or the earnings release vs the supply-chain consequence)
- When one event has three or more items, leave the two most distinct angles out of every group and fold each remaining item into the group of the item it most resembles
- Err on the side of keeping items separate when unsure"""

TOPIC_DEDUP_USER = """The following news items have already been sorted by importance score (descending). Identify which items are duplicates of each other.

{items}

Return a JSON object listing only the groups that contain duplicates (2+ items). Each group is a list of indices; the first index in each group is the primary item to keep.

Two items on the same event that genuinely differ in angle (policy text vs market reaction, company statement vs supply-chain impact) must not share a group; a third item on that event joins the group of the one it most resembles.

Respond with valid JSON only:
{{
  "duplicates": [[<primary_idx>, <dup_idx>, ...], ...]
}}

If there are no duplicates at all, return: {{"duplicates": []}}"""
