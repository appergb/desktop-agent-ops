# WeChat on macOS

Use this reference when the task is specifically about WeChat on macOS.

## Scope

This file documents public-safe operational knowledge only.

Do not include:
- private contact names as built-in fixtures
- real chat content
- account-specific identifiers
- sensitive or political example payloads

## Confirmed host behavior

For the current development host, the user confirmed:
- WeChat is configured as Enter-to-send

This host-specific fact should be treated as a runtime observation, not as a universal assumption for every other machine.

## Reliable operational pattern

1. focus WeChat
2. wait briefly if the app was previously occluded
3. confirm front-window bounds
4. derive semantic regions from the window:
   - top_search
   - left_sidebar_top
   - bottom_input
5. prefer region-relative candidate points over global screen guesses
6. verify text is visibly inside the actual input field
7. press Enter to send
8. wait a short moment for commit
9. capture again to verify message bubble creation
10. if ambiguous, wait until about 1 second total and capture again once more

## Important WeChat-specific cautions

- the toolbar/attachment row above the composer can steal focus if clicked too high
- the window may be frontmost but still visually occluded if another app overlaps it before reactivation
- a successful input command is not enough; the text must be visibly in the composer before send
- a successful send key event is not enough; the outgoing bubble must be verified afterward

## Public-safe test payloads

Use neutral text only, for example:
- `hello from desktop agent`
- `test message`
- `automation check`

## Future upgrades

- add a dedicated macOS WeChat region preset tuned from verified window-relative geometry
- add popup-recovery patterns for permission and file dialogs
- add a two-stage send verification helper: fast capture + delayed fallback capture
