# Step 1: Connect to Frontend

<step-meta>
number: 1
name: connect
gate: false
</step-meta>

<purpose>
Detect what type of frontend is running (web server or Electron app), establish a Playwright MCP connection, and verify the connection works.
</purpose>

<instructions>
1. READ the complete step file before taking any action
2. Determine app type (Web vs Electron) using process detection
3. If Web: verify server is running or start it
4. If Electron: check CDP is enabled and get internal server URL
5. Establish Playwright MCP connection
6. Verify connection with snapshot
7. Confirm app type, URL, and CDP port to user
</instructions>

<output>
Report back:
- App Type: {Web|Electron}
- Connected to: {actual_url}
- CDP Port: {port if Electron, "N/A" if Web}
- Playwright MCP: Verified
- Snapshot: [display snapshot or screenshot]
- Ready to explore the UI
</output>

## Purpose

Detect what type of frontend is running (web server or Electron app), establish a Playwright MCP connection, and verify the connection works.

## Mandatory Execution Rules

- READ the complete step file before taking any action
- NEVER skip app type detection
- VERIFY Playwright MCP connection before proceeding

## App Type Detection

**First, determine what we're connecting to:**

### Check for Running Processes

```bash
# Check for web server on expected port
lsof -ti:{dev_port} 2>/dev/null

# Check for Electron processes (app name varies by project)
ps aux | grep -i electron | grep -v grep
```

### Detection Logic

| Signal | App Type |
|--------|----------|
| Web server on port, no Electron process | **Web** |
| Electron process running | **Electron** |
| Both detected | Ask user which to connect to |
| Neither detected | Offer to start one |

---

## Web Mode Connection

For standard web servers (React, Vue, Next.js, Express, etc.):

### If Server IS Running

Present to user:

> I detected a web server running on port {dev_port}.
> - **[N] New** - Kill it and start fresh with `{dev_command}`
> - **[U] URL** - Specify a different URL to connect to

### If Server is NOT Running

Present to user:

> No web server detected on port {dev_port}.
> - **[U] URL** - Specify a different URL (server running elsewhere)
> - **[M] Manual** - I'll start the server myself, then continue

**If user chooses Start:**
- Run `{dev_command}` in background
- Wait for server to be ready (poll {dev_url} with curl)
- Confirm server is up before proceeding

### Web Mode Playwright Connection

Simply navigate to the URL:

```
Use mcp__playwright__browser_navigate to {dev_url}
```

---

## Electron Mode Connection

Electron apps require **Chrome DevTools Protocol (CDP)** for Playwright to connect.

### Check if CDP is Enabled

```bash
# Look for Electron process with remote-debugging-port
ps aux | grep -i electron | grep "remote-debugging-port"

# Check if CDP port (typically 9222) is listening
lsof -i :9222 | grep LISTEN
```

### If CDP IS Enabled

The Electron app was started with `--remote-debugging-port=9222`.

**Connect via CDP:**

```bash
# Get the CDP endpoint
curl -s http://localhost:9222/json/version
```

Then use Playwright to connect to `http://localhost:9222`.

### If CDP is NOT Enabled

Present to user:

> I detected an Electron app running, but CDP (Chrome DevTools Protocol) is not enabled.
> Playwright needs CDP to connect to Electron apps.
>
> **To enable CDP, restart the Electron app with the `--remote-debugging-port` flag:**
>
> Option 1: If using a justfile with `cdp` flag:
> ```bash
> # Kill current instance
> pkill -f "electron"
>
> # Restart with CDP enabled
> just {app_name} cdp
> ```
>
> Option 2: Direct electron command:
> ```bash
> electron --remote-debugging-port=9222 dist/main.js
> ```
>
> Option 3: Add to package.json scripts:
> ```json
> "dev:cdp": "electron --remote-debugging-port=9222 dist/main.js"
> ```
> - **[W] Web Mode** - Switch to web mode instead (if available)
> - **[M] Manual** - I'll configure CDP myself, then continue

**STOP and wait for user to enable CDP before proceeding.**

### Electron Mode Playwright Connection

**Important:** Playwright MCP starts its own Chromium browser - it does NOT connect directly to
existing CDP endpoints. The workaround is to connect to the Electron app's internal web server.

Once CDP is confirmed:

1. **Get the internal server URL from CDP:**
   ```bash
   curl -s http://localhost:9222/json/list
   ```

   Look for the `url` field in the response:
   ```json
   [{
     "title": "Your App",
     "url": "http://localhost:60178/",
     "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/..."
   }]
   ```

2. **Connect Playwright to the internal URL** (NOT the CDP port):
   ```
   Use mcp__playwright__browser_navigate to http://localhost:60178/
   ```

   The port varies each launch - always check `/json/list` first.

3. **Verify connection** with `mcp__playwright__browser_snapshot`

**Why this works:** Electron apps run an internal Express server for the renderer. CDP exposes
the page list which includes this internal URL. Playwright connects to this URL and sees the
same content as the Electron renderer.

**Common mistake:** Navigating to `http://localhost:9222` shows the CDP index page, not your app.

---

## Playwright MCP Verification

**After establishing connection (either mode), verify Playwright MCP:**

1. Use the Playwright MCP tool to navigate to the target URL
2. Take a snapshot to confirm connection works

**If Playwright MCP is not available:**

> Playwright MCP is not configured. This workflow requires browser automation.
>
> Please add the Playwright MCP server to your Claude settings and restart.
>
> Example configuration (claude_desktop_config.json):
> ```json
> {
>   "mcpServers": {
>     "playwright": {
>       "command": "npx",
>       "args": ["@anthropic-ai/mcp-playwright"]
>     }
>   }
> }
> ```

**STOP workflow if Playwright MCP unavailable.**

---

## Output

Confirm to user:

```
App Type: {Web|Electron}
Connected to: {actual_url}
CDP Port: {port if Electron, "N/A" if Web}
Playwright MCP: Verified
Snapshot: [display snapshot or screenshot]

Ready to explore the UI.
```

<switch tool="AskUserQuestion">
  <case value="connect" next="step-02-explore">
    Connect — Use the existing server at {dev_url}
  </case>
  <case value="new" next="LOOP">
    New — Kill it and start fresh with `{dev_command}`
  </case>
  <case value="url" next="LOOP">
    URL — Specify a different URL to connect to
  </case>
  <case value="start" next="LOOP">
    Start — Launch with `{dev_command}`
  </case>
  <case value="manual" next="LOOP">
    Manual — I'll start the server myself, then continue
  </case>
  <case value="retry" next="LOOP">
    Retry — Check again after restarting
  </case>
  <case value="web-mode" next="LOOP">
    Web Mode — Switch to web mode instead (if available)
  </case>
  <case value="toggle-mode" next="LOOP">
    Toggle Mode — Switch between Electron/Web if both available
  </case>
</switch>

## Next Step

After user confirms connection, proceed to UI exploration.
