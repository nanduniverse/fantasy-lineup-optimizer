# Weekly UI snapshot

`weekly-catalog.json` retains three Green Bay veterans from a local API response captured on 2026-09-10. Underlying sources are ESPN's current injury/depth feeds and nflverse's roster/statistics releases. It contains only catalog/projection fields, not news article content. The browser test intercepts the player endpoint with this snapshot to verify unavailable-player controls and expandable workload explanations deterministically. It is test data, not an application fallback.
