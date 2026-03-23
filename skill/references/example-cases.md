# Example Cases

Use this reference for public-safe, repeatable desktop operation examples.

## Rule

All examples here must be:
- public-safe
- generic
- reproducible
- free of private identities, secrets, or sensitive content

Each case should be read as a reusable pattern, not a one-off script.

## Case format

Each example includes:
1. goal
2. target app type
3. preconditions
4. workflow
5. validation points
6. failure recovery

---

## Case 1: Focus an app and confirm the correct window

### Goal
Bring a target app to the foreground and confirm the active window is correct.

### Target app type
Any desktop app.

### Preconditions
- app is installed
- the app can be activated normally

### Workflow
1. focus target app
2. obtain front-window bounds
3. capture current screen
4. confirm the frontmost app matches expectation
5. confirm the visible window matches expectation

### Validation points
- app is frontmost
- window bounds are available
- screenshot matches the intended app
- when precision matters, the report should include window bounds, region bounds, candidate points, and live mouse coordinates

### Failure recovery
- refocus app
- recapture
- if still ambiguous, resize/reposition window and try again

---

## Case 2: Select a conversation in a chat app and verify target correctness

### Goal
Switch into the intended conversation before typing or sending.

### Target app type
Chat app on desktop.

### Preconditions
- target app is frontmost
- left conversation list is visible

### Workflow
1. obtain front-window bounds
2. derive the conversation list region
3. click the intended conversation row
4. capture again
5. confirm conversation title/header matches the intended target
6. confirm visible transcript context is compatible with the intended target

### Validation points
- title/header is correct
- transcript context is correct
- selected state appears consistent with the chosen conversation

### Failure recovery
- do not send anything
- recapture and retry selection
- use search instead of manual list scanning if available

---

## Case 3: Type into the true input field instead of the toolbar

### Goal
Ensure text goes into the actual composer or input field.

### Target app type
Chat app, editor, browser form, or search UI.

### Preconditions
- active window has been verified
- input region can be derived from the window

### Workflow
1. derive the input region relative to the window
2. generate candidate points in the region
3. click candidate point
4. type sample text
5. capture again
6. confirm the text is in the true input field

### Validation points
- typed text is visible where expected
- no attachment, toolbar, or popup UI was triggered accidentally

### Failure recovery
- clear misfocused UI if needed
- derive input region again
- click a lower or more central candidate point and retry

---

## Case 4: Send a safe test message in a chat app

### Goal
Send a public-safe test message only after the correct conversation and input field are verified.

### Target app type
Desktop chat app.

### Preconditions
- correct conversation already verified
- typed text is visible in the true composer
- send behavior is known for the host app

### Workflow
1. type neutral safe text
2. verify text is visible in the composer
3. trigger the app’s real send action
4. wait briefly for UI commit
5. capture again
6. if needed, capture once more after about 1 second total
7. confirm the outgoing message bubble appears

### Validation points
- typed text existed before send
- outgoing bubble appears after send
- message appears in the correct conversation

### Failure recovery
- do not assume success from keypress return values alone
- recapture and verify active conversation again
- confirm send backend and retry only if the target remains verified

---

## Case 5: Search inside an app instead of manually scanning

### Goal
Use in-app search to reduce random clicks and unstable scrolling.

### Target app type
Any app with a search UI.

### Preconditions
- app is focused
- search region is visible or reachable

### Workflow
1. derive top search region
2. click inside the search field
3. verify text cursor or active field state
4. type query
5. capture again
6. confirm search results changed
7. select intended result and verify target correctness

### Validation points
- search field accepted input
- result list changed as expected
- selected result matches intended target

### Failure recovery
- clear the field and retry once
- if search UI is ambiguous, recapture only the top region

---

## Case 6: Open a file in a file manager

### Goal
Find and open a target file using visible GUI state.

### Target app type
Finder or other file manager.

### Preconditions
- file manager window is active
- search field or list view is visible

### Workflow
1. focus file manager
2. verify front window
3. use search if available
4. verify result row or filename
5. double-click or open the file
6. capture again
7. verify the expected file or app opened

### Validation points
- selected row matches file name expectation
- resulting window or app matches intended file open action

### Failure recovery
- return to the file manager
- narrow search scope
- verify file row again before opening

---

## Case 7: Handle a popup or permission dialog safely

### Goal
Recover from unexpected dialogs without causing side effects.

### Target app type
Any desktop app.

### Preconditions
- a popup or dialog is visible

### Workflow
1. capture the dialog
2. identify whether it is expected or unexpected
3. derive the dialog button region
4. choose the safest valid action
5. click once
6. capture again
7. verify the dialog closed or the intended next state appeared

### Validation points
- dialog type understood well enough
- chosen button matches the intended recovery action
- post-dialog state is correct

### Failure recovery
- prefer cancel, close, or deny when intent is unclear
- stop rather than guessing on destructive dialogs

---

## Case 8: Browser-like navigation with verification

### Goal
Operate a browser or browser-like desktop app via visible GUI patterns.

### Target app type
Desktop browser or embedded browser shell.

### Preconditions
- browser window active
- page content visible

### Workflow
1. verify app and window
2. validate page title or visible page context
3. derive action region
4. click link/button/input
5. capture again
6. confirm intended page or state transition occurred

### Validation points
- visible page context is correct before action
- visible page context changed correctly after action

### Failure recovery
- avoid repeated blind clicks
- refresh the visible context by recapturing before retrying

---

## Case 9: Closed software with no usable API

### Goal
Operate software entirely through visible GUI state.

### Target app type
Closed desktop app with no integration path.

### Preconditions
- app can be focused
- window bounds can be obtained

### Workflow
1. focus app
2. obtain window bounds
3. derive region from visible layout
4. move and verify pointer position
5. click or type one step
6. capture again
7. validate outcome
8. continue one step at a time

### Validation points
- each action is locally verified
- no blind global-coordinate sequences are used

### Failure recovery
- rebuild the region from the window
- reduce scope to smaller captures
- do not chain unverified actions

---

## Case 10: End-to-end chat reply with context compatibility

### Goal
Read visible context from a chat, compose a compatible reply, and send only after full validation.

### Target app type
Desktop chat app.

### Preconditions
- app focused
- target conversation verified
- visible transcript readable enough for context

### Workflow
1. select and verify conversation
2. read recent visible context
3. draft a compatible public-safe reply
4. click verified composer region
5. type reply
6. verify text in composer
7. send
8. wait briefly
9. capture again
10. verify outgoing bubble in the same conversation

### Validation points
- reply is context-compatible
- conversation remained correct throughout
- outgoing message appears in the verified conversation

### Failure recovery
- if conversation correctness is lost, stop and revalidate before retrying
- if send verification is ambiguous, use delayed second capture

---

## Case 11: Launch a desktop controller app and batch-start all tasks

### Goal
Open a launcher/controller app, verify the correct window, and start all listed tasks or tunnels.

### Target app type
Desktop launcher, controller, proxy manager, tunnel manager, or similar utility app.

### Preconditions
- the app is installed and launchable
- the app window can be focused
- the task list or tunnel list is visible after opening

### Workflow
1. focus or launch the target app
2. obtain front-window bounds
3. verify the active window title matches the intended app
4. derive the list region and the primary action region relative to the window
5. inspect whether tasks are already running or stopped
6. locate the global start-all action if present; otherwise iterate over visible stopped items one by one
7. after each start action, wait briefly and capture again
8. verify status indicators changed to running/active
9. if scrolling is needed, scroll the list and continue with validation at each step

### Validation points
- active app and window are correct
- the list belongs to the intended launcher/controller app
- each started task shows a running/active state
- no unexpected error dialog remains open

### Failure recovery
- if the wrong utility window is active, refocus and revalidate before any click
- if start-all is not obvious, prefer verified per-item start over guessing a toolbar button
- if an error dialog appears, capture it and choose the safest recovery path before continuing
