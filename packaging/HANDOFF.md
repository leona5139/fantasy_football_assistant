# Fantasy Draft Assistant — Setup Guide

## 1. Before you download: check your Mac

This build requires an **Apple Silicon Mac** (a chip named M1, M2, M3, M4, or later — anything Apple has sold since late 2020).

Click the Apple menu (top-left corner) → **About This Mac**. If it says **"Chip: Apple M__"**, you're good — download `FantasyDraftAssistant-macos-arm64.zip`. If it says **"Processor: Intel..."**, this build won't run on your Mac — let me know and I'll put together an Intel build instead.

## 2. Install

1. Unzip the file you downloaded (double-click it).
2. You should now have a file called **`FantasyDraftAssistant.app`**. Move it wherever you like (e.g. your Applications folder or Desktop).

## 3. First launch (macOS security warning)

Because this app isn't from a registered Apple developer, macOS will refuse to open it the first time with a warning like *"cannot be opened because the developer cannot be verified."* This is expected — here's how to get past it:

1. **Right-click** (or Control-click) on `FantasyDraftAssistant.app` and choose **Open** from the menu.
2. A dialog will pop up with an **Open** button this time (not just Cancel) — click **Open**.

This only needs to be done once. After this, double-clicking normally will work.

**If that still refuses to open:** open the **Terminal** app (Spotlight search → "Terminal"), type the following, then press Enter (adjust the path if you moved the app somewhere other than Applications):

```
xattr -d com.apple.quarantine /Applications/FantasyDraftAssistant.app
```

Then try opening the app again.

## 4. Using the app

When it starts, a small window titled "Fantasy Draft Assistant" will appear saying it's running, and your default web browser will automatically open to the draft tool. That small window is just a status/quit control — leave it open in the background while you draft; closing it (via its **Quit** button) stops the app.

If you accidentally close the browser tab, just open a new tab and go to:

```
http://127.0.0.1:8765
```

## 5. On draft day

- Set up your league (team count, scoring, your draft slot) on the first screen.
- As each pick happens (yours or an opponent's), type the player's name in the search box, select them, and click **Draft this player** — the app tracks whose turn it is automatically.
- Use **Think Harder** for a deeper (slower, ~15 second) recommendation before a tough pick.
- If something goes wrong, **Undo Last Pick** reverses the most recent pick.
- If your internet drops mid-draft, the player list falls back to a saved snapshot automatically — the tool keeps working, it just won't reflect the very latest rankings.
