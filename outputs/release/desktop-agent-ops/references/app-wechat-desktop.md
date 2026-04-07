# WeChat Desktop

Use this reference when the task is specifically about WeChat Desktop on macOS or Windows.

## Core send decision rule

Treat sending as a decision ladder, not a hardcoded single action:

1. verify the correct conversation is open
2. verify the draft text is visible in the true composer
3. check whether a visible `发送` send button is available
4. if the send button is visible and verified, click the send button
5. if there is no verified send button, and the host is confirmed to be direct-Enter-to-send, run `desktop_ops.py press --key return`
6. if neither path is verified, do not send yet
7. if the target conversation is not visible in the sidebar, use the search box to search the exact conversation name first, then click the matching search result

This is the required WeChat workflow for this skill, and it should also be generalized to similar desktop chat apps.

## Message composition rule

- use `desktop_ops.py type --text` for ordinary text input
- use `desktop_ops.py insert-newline` for literal line breaks inside the draft
- do not use `type --text` with `\n` as a send surrogate
- keep literal line breaks and send actions as separate operations

## Platform guidance

### Windows WeChat

Windows WeChat commonly exposes a visible `发送` button.

- prefer the verified `发送` button as the primary send action
- only fall back to `press --key return` when no send button is available and Enter-to-send is already confirmed for the host

### macOS WeChat

macOS WeChat may rely more often on direct-Enter-to-send.

- if a verified `发送` button is available, it is still safe to prefer that explicit UI action
- if no verified send button is available, use `desktop_ops.py press --key return` only after the draft is visibly in the true composer and Enter-to-send is known for the host
- if WeChat is running but its chat window is minimized or hidden, `focus-app --name "WeChat"` should restore the main window before any OCR or accessibility lookup starts
- if `focus-app` succeeds but `front-window-bounds` still cannot read a usable window, stop and treat that as a window-restore failure instead of clicking blindly

## Recommended workflow

1. focus WeChat
2. verify the correct conversation is active
3. if the conversation is not already visible, use the sidebar search box to search it and click the matching result
4. click the true composer region
5. type message text with `desktop_ops.py type --text`
6. if the message needs a real line break, use `desktop_ops.py insert-newline`
7. verify the full draft is visible in the composer
8. look for a verified visible `发送` button
9. if found, click it
10. otherwise, if Enter-to-send is verified for this host, run `desktop_ops.py press --key return`
11. capture again and verify the outgoing message bubble appears

## Important caution

Do not guess the send action.

- visible send button beats inferred key behavior
- verified Enter-to-send beats unverified assumptions
- if neither path is verified, stop and recapture before sending

## Generalization rule

Apply the same reasoning to similar chat apps:

- first prefer the app's explicit visible send affordance
- if that affordance is absent, use the verified send key path for that host and app
- if the message needs multiple lines, use `insert-newline` and reserve the final send action for the verified send step
