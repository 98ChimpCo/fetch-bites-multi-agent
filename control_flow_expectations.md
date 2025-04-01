# 📜 Control Flow Expectations: Instagram DM Agent

This document outlines the expected behavior of the AI-powered Instagram DM processing agent when scanning for unread messages and processing shared posts.

---

## 📭 Case 1: Zero New Messages (No Unread Threads)

- Claude analyzes the left sidebar for DM tiles.
- No blue-dot indicators (unread status) are found.
- **Expected Behavior:**
  - Log: `⚠️ No unread DM threads found.`
  - Agent exits gracefully.
  - Browser session closes.
  - No further Claude vision calls made.
  - Minimal token usage.

---

## 💬 Case 2: One or More Unread Threads

- Claude identifies all threads with a blue-dot (unread).
- Threads are sorted **bottom-to-top** to avoid reshuffling as they are marked read.
- **For each unread thread:**
  1. Click on the DM tile.
  2. Claude analyzes the DM content.
  3. If a shared post is present:
     - Click the post preview.
     - Claude analyzes the expanded post.
     - Extract caption and detect recipe.
     - Generate a PDF of the recipe.
     - Attach the PDF and reply via DM.
  4. Move on to the next unread thread.

- **Post Loop Behavior:**
  - All threads are processed.
  - Any skipped threads (e.g. no shared post) are logged.
  - Browser session closes on completion.

---

## ⏳ Future Enhancements

- Periodic re-scan loop (polling every X seconds).
- Persist which threads were replied to (avoid reprocessing).
- Label or annotate threads post-processing.