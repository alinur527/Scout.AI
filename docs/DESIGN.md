# ScoutAI interface direction

Audience: a football player reviewing a match and a scout comparing saved player reports.

Tokens: night `#080d19`, navy `#101a2d`, surface `#17233a`, violet `#a99aff`, cyan `#62e6eb`, ink `#eef4ff`. Muted text `#aab8cf` remains readable. Segoe UI / system sans for controls and content; Bahnschrift condensed headings for a match programme feel, no external font request.

Layout: persistent compact navigation on the left; wide content with a match pitch as the main report visual. On mobile navigation becomes a wrapping header. Align data and headings left; reserve a quiet right column for report provenance.

```
navigation | page title / primary action
           | player identity + analysis history
           | pitch movement map | observed metrics
           | report notes / source / tracking quality
```

Review against brief: generic metric cards alone would resemble any SaaS dashboard. Revised the visual centre to a football pitch, player shirt marker, movement paths and a coordinate-aware heatmap. Use pitch markings only for calibrated field coordinates; uncalibrated movement uses an image grid so it cannot imply metre accuracy. Violet controls and cyan observations distinguish actions from measured data. No unsupported claims or fabricated ranking.

Build/critique: inspect screenshots at 1440, 768 and 390 px. Check keyboard focus, labels, wrapped navigation, long filenames, failed jobs, empty scout search, unavailable metrics and persistent demo labels.
