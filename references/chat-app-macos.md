# Chat App on macOS

Use this reference for desktop chat software on macOS, including but not limited to WeChat, QQ, Feishu desktop, Telegram Desktop, and Discord Desktop.

## Goal

Provide a reusable workflow for reading context, selecting the right conversation, composing text, sending, and verifying the result without relying on private APIs.

## Standard chat workflow

1. focus target app
2. wait briefly if the window was occluded
3. obtain front-window bounds
4. derive semantic regions relative to the window:
   - top search region
   - left conversation list region
   - title/header region
   - message transcript region
   - bottom composer region
5. select target conversation
6. validate active conversation before typing
7. read visible context
8. draft a reply compatible with that context
9. click true composer region
10. verify typed text appears in the composer
11. trigger send action
12. wait briefly for UI commit
13. verify sent result

## Required validation before send

Before sending a message, confirm all of these:
- the app is the intended app
- **the left sidebar conversation row has been clicked** (not just the search box)
- the active conversation title matches the intended target
- the visible transcript context matches the intended conversation
- the input text is visible in the true text composer

If any one of these is not confirmed, do not send. If title cannot be confirmed (no OCR/title read), recapture sidebar + header and request user confirmation.

## Region guidance

### Conversation list region
Use window-relative coordinates and click within the interior of the row.
Do not click borders or row separators.

### Title/header region
Use this region to confirm the active conversation after selecting a row.

### Composer region
Treat the toolbar/attachment row and the true text input area as separate targets.
Typing is valid only when the text is visible in the true text input area.

## Send verification

For chat apps, a send key event alone is not sufficient proof.
Always verify via a post-send capture.

Recommended timing:
- first verification capture after ~0.3-0.8 seconds
- second verification capture at about 1 second total if the first is ambiguous

## Public-safe examples

Safe neutral payloads:
- hello from desktop agent
- test message
- automation check

Do not hardcode private contacts, chat names, or sensitive messages into public skill references.
