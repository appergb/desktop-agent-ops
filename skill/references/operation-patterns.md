# Operation Patterns

Use these as repeatable task templates.

## Pattern: Open an app and start from known state

1. check frontmost app
2. if needed, focus target app
3. capture state
4. verify the expected app is visible
5. continue with the task

## Pattern: Find a person or object in an app

When the UI has a search box, prefer search over manual scrolling.

Before clicking a candidate row, keep the target app frontmost and use move -> mouse-position -> click -> recapture instead of blind clicking.

1. capture current state
2. if target is visibly present, click it
3. otherwise locate the app search area
4. click search field
5. type target text
6. capture again
7. verify results appeared
8. click the intended result
9. capture again to verify the correct view opened

## Pattern: Send a message

1. confirm the correct conversation is open
2. if the app window can move, prefer window-relative region targeting instead of full-screen absolute points
3. derive the bottom input region from the front window when possible
4. generate 3-5 candidate points inside the input region and avoid the attachment/tool row above the text box
5. click one candidate, then recapture to verify the real text cursor landed in the text field
6. type message text
7. capture and verify the text is visible in the actual input field
8. use the app’s real send trigger
9. capture again and verify the message appears sent

For WeChat on this host, the user has confirmed the setting is Enter-to-send, so plain Enter should be treated as the expected send trigger after text is visibly inside the true input box.

For instant-messaging apps like WeChat, do not re-capture immediately after pressing Enter. The UI may need a short fraction of a second to commit the outgoing message bubble. Standard rule: wait briefly after send (for example ~0.3-0.8s), then capture; if still ambiguous, wait until about 1 second total and capture again before declaring failure.

## Pattern: File selection flow

1. ensure file picker is frontmost
2. use search if available
3. otherwise navigate carefully one step at a time
4. capture after every meaningful navigation change
5. confirm intended file is selected
6. click open/confirm
7. capture again to verify picker closed or target app updated

## Pattern: Region-first precise interaction

Use this when the target is small or the screen is visually dense.

1. capture full screen or target app state
2. narrow to a region capture around the area of interest
3. reason over the smaller region
4. execute one action
5. recapture the region or full state and verify

## Pattern: Recovery after a failed click

1. do not keep clicking blindly
2. capture current state again
3. verify frontmost app is still correct
4. refocus if needed
5. reduce scope to a region capture
6. retry one carefully chosen step
7. if still unstable, escalate or pause
