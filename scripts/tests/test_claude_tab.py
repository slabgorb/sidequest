"""Story 21-3: Dashboard Claude tab — tool timeline, token breakdown, cost accumulator.

RED phase — tests for the Claude tab in the playtest dashboard.
The Claude tab consumes claude_otel events (tool_result, token_usage, span)
already broadcast by the OTLP receiver (story 21-2) and renders:
  1. Tool call timeline with duration bars
  2. Token breakdown (input/output/cache_read/cache_creation per turn)
  3. Running cost accumulator
  4. Tool failure indicators
  5. Turn correlation via timestamp
  6. Tab badge with tool invocation count

ACs tested:
  AC-1: Tab 8 (Claude) appears in dashboard tab bar
  AC-2: Tool call timeline renders with duration bars per tool invocation
  AC-3: Token breakdown shows input/output/cache read/cache creation per turn
  AC-4: Running cost accumulator displays total spend
  AC-5: Tool failures highlighted with error indicator
  AC-6: Events correlate to game turns via timestamp
  AC-7: Tab badge shows count of tool invocations

Rule enforcement (Python lang-review):
  #1 — no silent exception swallowing
  #6 — meaningful assertions (self-checked)
  #9 — async/await pitfalls

Rule enforcement (JavaScript lang-review):
  #1 — no silent error swallowing in claude_otel dispatch
  #4 — strict equality in new JS code
  #5 — DOM security (innerHTML with user input)
"""

import re
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_dashboard_html() -> str:
    """Import playtest_dashboard and return DASHBOARD_HTML."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    if "playtest_dashboard" in sys.modules:
        del sys.modules["playtest_dashboard"]
    import importlib
    mod = importlib.import_module("playtest_dashboard")
    return mod.DASHBOARD_HTML


def _get_dashboard_js() -> str:
    """Extract the JavaScript from DASHBOARD_HTML (between <script> tags)."""
    html = _get_dashboard_html()
    match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert match, "DASHBOARD_HTML must contain a <script> block"
    return match.group(1)


def _find_claude_functions(js: str) -> list[str]:
    """Extract all Claude-related function blocks from dashboard JS."""
    return re.findall(
        r"function\s+\w*[Cc]laude\w*\(.*?\n\}",
        js, re.DOTALL
    )


# ============================================================================
# AC-1: Tab 8 (Claude) appears in dashboard tab bar
# ============================================================================

class TestClaudeTabExists:
    """The dashboard must have an 8th tab labeled Claude."""

    def test_tab_bar_has_claude_entry(self):
        """Tab bar must contain a Claude tab (tab index 7)."""
        html = _get_dashboard_html()
        # Tab bar should have switchTab(7) for the 8th tab (0-indexed)
        assert "switchTab(7)" in html, (
            "Dashboard tab bar must include switchTab(7) for the Claude tab"
        )

    def test_claude_tab_label(self):
        """Claude tab must be labeled with ⑧ Claude or similar."""
        html = _get_dashboard_html()
        # The tab should mention "Claude" in its label
        assert re.search(r"Claude", html), (
            "Dashboard tab bar must include 'Claude' label"
        )

    def test_claude_tab_content_div_exists(self):
        """Tab content div for Claude (tc7) must exist."""
        html = _get_dashboard_html()
        assert 'id="tc7"' in html, (
            "Dashboard must have a tab-content div with id='tc7' for Claude tab"
        )

    def test_claude_tab_has_badge(self):
        """Claude tab must have a badge element for tool invocation count."""
        html = _get_dashboard_html()
        assert 'id="tab7-badge"' in html, (
            "Claude tab must have a badge element with id='tab7-badge'"
        )


# ============================================================================
# AC-2: Tool call timeline renders with duration bars per tool invocation
# ============================================================================

class TestToolTimeline:
    """Claude tab must render tool calls as a timeline with duration bars."""

    def test_tool_timeline_container_exists(self):
        """A container for the tool timeline must exist in tc7."""
        html = _get_dashboard_html()
        # Should have a container for tool timeline within the Claude tab
        assert re.search(r'id="claude-tool-timeline"', html), (
            "Claude tab must have a container with id='claude-tool-timeline'"
        )

    def test_render_claude_timeline_function_exists(self):
        """JavaScript must define a renderClaudeTimeline function."""
        js = _get_dashboard_js()
        assert "renderClaudeTimeline" in js or "renderClaudeTools" in js, (
            "Dashboard JS must define a function to render the Claude tool timeline"
        )

    def test_tool_timeline_shows_tool_name(self):
        """Tool timeline rendering must include the tool name from OTEL span events."""
        js = _get_dashboard_js()
        claude_fns = _find_claude_functions(js)
        assert claude_fns, (
            "Dashboard JS must have Claude-specific render functions that display tool names"
        )
        has_tool_ref = any("tool_name" in fn or "name" in fn for fn in claude_fns)
        assert has_tool_ref, (
            "Claude render function must reference tool_name from OTEL events"
        )

    def test_tool_timeline_shows_duration(self):
        """Tool timeline must display duration_ms for each tool invocation."""
        js = _get_dashboard_js()
        claude_fns = _find_claude_functions(js)
        assert claude_fns, (
            "Dashboard JS must have Claude-specific render functions that show duration"
        )
        has_dur_ref = any("duration_ms" in fn for fn in claude_fns)
        assert has_dur_ref, (
            "Claude render function must use duration_ms from OTEL events"
        )


# ============================================================================
# AC-3: Token breakdown shows input/output/cache read/cache creation per turn
# ============================================================================

class TestTokenBreakdown:
    """Claude tab must show token usage broken down by type."""

    def test_token_breakdown_container_exists(self):
        """A container for token breakdown must exist in tc7."""
        html = _get_dashboard_html()
        assert re.search(r'id="claude-token-breakdown"', html), (
            "Claude tab must have a container with id='claude-token-breakdown'"
        )

    def test_token_types_tracked(self):
        """JS state must track input, output, cache_read, and cache_creation tokens."""
        js = _get_dashboard_js()
        for token_type in ["input", "output", "cache_read", "cache_creation"]:
            assert token_type in js, (
                f"Dashboard JS must reference '{token_type}' token type "
                f"for the token breakdown display"
            )

    def test_render_token_breakdown_function_exists(self):
        """JavaScript must define a function to render token breakdown."""
        js = _get_dashboard_js()
        assert re.search(r"renderClaudeTokens|renderTokenBreakdown", js), (
            "Dashboard JS must define a function to render token breakdown"
        )


# ============================================================================
# AC-4: Running cost accumulator displays total spend
# ============================================================================

class TestCostAccumulator:
    """Claude tab must show a running cost accumulator."""

    def test_cost_display_container_exists(self):
        """A container for cost accumulator must exist in tc7."""
        html = _get_dashboard_html()
        assert re.search(r'id="claude-cost"', html), (
            "Claude tab must have a container with id='claude-cost'"
        )

    def test_cost_calculation_in_js(self):
        """JS must implement cost calculation logic."""
        js = _get_dashboard_js()
        # Cost calculation should reference pricing or cost computation
        assert re.search(r"cost|price|spend", js, re.IGNORECASE), (
            "Dashboard JS must implement cost calculation for the accumulator"
        )

    def test_cost_uses_token_counts(self):
        """Cost calculation must use token counts (input and output have different rates)."""
        js = _get_dashboard_js()
        # Should have separate pricing for input vs output tokens
        assert re.search(r"(input.*output|output.*input).*(\$|cost|price|rate)", js, re.DOTALL | re.IGNORECASE), (
            "Cost calculation must differentiate between input and output token pricing"
        )


# ============================================================================
# AC-5: Tool failures highlighted with error indicator
# ============================================================================

class TestToolFailureIndicator:
    """Tool failures must be visually highlighted in the Claude tab."""

    def test_error_detection_in_tool_events(self):
        """JS must check for tool failure/error status in OTEL events."""
        js = _get_dashboard_js()
        # Should check for error/failure status on tool events
        assert re.search(r"(error|fail|status).*tool|tool.*(error|fail|status)", js, re.IGNORECASE), (
            "Dashboard JS must detect tool failures/errors in OTEL events"
        )

    def test_error_visual_indicator(self):
        """Failed tools must have a visual error indicator (color, icon, class)."""
        html = _get_dashboard_html()
        # CSS should have error styling for Claude tab or use existing --red var
        # or JS should apply error class/style
        js = _get_dashboard_js()
        assert re.search(r"(err|error|fail).*claude|claude.*(err|error|fail)", js + html, re.IGNORECASE), (
            "Claude tab must have visual indicators for tool failures"
        )


# ============================================================================
# AC-6: Events correlate to game turns via timestamp
# ============================================================================

class TestTurnCorrelation:
    """Claude OTEL events must be correlated to game turns via timestamp."""

    def test_timestamp_field_used(self):
        """JS must reference timestamp fields from OTEL events for correlation."""
        js = _get_dashboard_js()
        assert re.search(r"timestamp_ns|start_ns|timeUnixNano", js), (
            "Dashboard JS must use timestamp fields from OTEL events for turn correlation"
        )

    def test_turn_correlation_logic(self):
        """JS must have logic to associate OTEL events with game turns."""
        js = _get_dashboard_js()
        # Should correlate claude events with turns (by timestamp proximity or turn boundaries)
        assert re.search(r"turn.*claude|claude.*turn|correlat|associat", js, re.IGNORECASE), (
            "Dashboard JS must correlate Claude OTEL events with game turns"
        )


# ============================================================================
# AC-7: Tab badge shows count of tool invocations
# ============================================================================

class TestTabBadge:
    """Claude tab badge must show the count of tool invocations."""

    def test_badge_updated_on_claude_events(self):
        """JS must update tab7-badge when claude_otel events arrive."""
        js = _get_dashboard_js()
        assert "tab7-badge" in js, (
            "Dashboard JS must update the tab7-badge element on claude_otel events"
        )

    def test_badge_shows_count(self):
        """Badge content must reflect the number of tool invocations."""
        js = _get_dashboard_js()
        # Should set badge textContent or innerHTML to a count
        assert re.search(r"tab7-badge.*textContent|tab7-badge.*innerHTML", js, re.DOTALL), (
            "tab7-badge must be updated with tool invocation count"
        )


# ============================================================================
# Wiring: claude_otel events routed to Claude tab
# ============================================================================

class TestClaudeOtelEventRouting:
    """The dispatch() function must route claude_otel events to the Claude tab."""

    def test_dispatch_handles_claude_otel_source(self):
        """dispatch() must check for source === 'claude_otel' and route accordingly."""
        js = _get_dashboard_js()
        assert re.search(r"source.*===.*['\"]claude_otel['\"]|['\"]claude_otel['\"].*===.*source", js), (
            "dispatch() must check for source === 'claude_otel' to route OTEL events to Claude tab"
        )

    def test_dispatch_routes_tool_result_events(self):
        """dispatch() must handle tool_result type events from claude_otel."""
        js = _get_dashboard_js()
        assert re.search(r"tool_result", js), (
            "dispatch() must handle 'tool_result' type events for Claude tab"
        )

    def test_dispatch_routes_token_usage_events(self):
        """dispatch() must handle token_usage type events from claude_otel."""
        js = _get_dashboard_js()
        assert re.search(r"token_usage", js), (
            "dispatch() must handle 'token_usage' type events for Claude tab"
        )

    def test_dispatch_routes_span_events(self):
        """dispatch() must handle span type events from claude_otel."""
        js = _get_dashboard_js()
        # Need to be careful — "span" appears in HTML too, check for it in event routing
        assert re.search(r"type.*===.*['\"]span['\"]|['\"]span['\"].*===", js), (
            "dispatch() must handle 'span' type events for Claude tab"
        )


# ============================================================================
# State management: Claude OTEL data structures
# ============================================================================

class TestClaudeStateManagement:
    """JS state must have data structures for Claude tab."""

    def test_claude_events_array_in_state(self):
        """S (state object) must have an array for Claude OTEL events."""
        js = _get_dashboard_js()
        # State should track claude events separately
        assert re.search(r"claudeEvents|claude_events|claudeTools|claudeSpans", js), (
            "State object S must have an array for storing Claude OTEL events"
        )

    def test_claude_token_totals_in_state(self):
        """S must track token totals for the cost accumulator."""
        js = _get_dashboard_js()
        assert re.search(r"claudeTokens|claude_tokens|tokenTotals|token_totals", js), (
            "State object S must track token totals for cost accumulation"
        )


# ============================================================================
# switchTab must render Claude tab
# ============================================================================

class TestSwitchTabIntegration:
    """switchTab() must call Claude tab render when tab 7 is selected."""

    def test_switch_tab_handles_index_7(self):
        """switchTab() must call Claude render functions when i===7."""
        js = _get_dashboard_js()
        assert re.search(r"i\s*===?\s*7|activeTab\s*===?\s*7", js), (
            "switchTab() must handle tab index 7 for Claude tab rendering"
        )


# ============================================================================
# updateAll must include Claude tab
# ============================================================================

class TestUpdateAllIntegration:
    """updateAll() must include Claude tab rendering."""

    def test_update_all_renders_claude(self):
        """updateAll() must call Claude rendering when activeTab is 7."""
        js = _get_dashboard_js()
        # Check that updateAll references tab 7 or Claude render function
        update_all_match = re.search(r"function updateAll\(\).*?\}", js, re.DOTALL)
        if update_all_match:
            update_fn = update_all_match.group(0)
            assert re.search(r"7|claude|Claude", update_fn, re.IGNORECASE), (
                "updateAll() must include Claude tab rendering for activeTab===7"
            )
        else:
            pytest.fail("updateAll() function not found in dashboard JS")


# ============================================================================
# Rule #1 (JS): No silent error swallowing in new claude_otel dispatch
# ============================================================================

class TestNoSilentErrorSwallowing:
    """New JavaScript for Claude tab must not silently swallow errors."""

    def test_no_empty_catch_in_claude_handlers(self):
        """Claude-related JS functions must not have empty catch blocks."""
        js = _get_dashboard_js()
        claude_blocks = _find_claude_functions(js)
        assert claude_blocks, (
            "No Claude handler functions found — must exist before checking rule compliance"
        )
        for block in claude_blocks:
            assert not re.search(r"catch\s*\(\w*\)\s*\{\s*\}", block), (
                f"Empty catch block found in Claude handler: {block[:100]}..."
            )


# ============================================================================
# Rule #4 (JS): Strict equality in new JS code
# ============================================================================

class TestStrictEquality:
    """New Claude tab JS must use === not == for comparisons."""

    def test_claude_otel_check_uses_strict_equality(self):
        """Source check for 'claude_otel' must use === not ==."""
        js = _get_dashboard_js()
        # First verify that the claude_otel check exists at all
        assert re.search(r"claude_otel", js), (
            "Dashboard JS must reference 'claude_otel' for event routing"
        )
        # Then verify it uses strict equality
        assert not re.search(r"[^=]==\s*['\"]claude_otel['\"](?!=)", js), (
            "claude_otel source check must use === (strict equality), not =="
        )


# ============================================================================
# Rule #5 (JS): DOM security — innerHTML with user input
# ============================================================================

class TestDomSecurity:
    """Claude tab must escape user-controlled data in innerHTML."""

    def test_tool_names_escaped_in_timeline(self):
        """Tool names from OTEL events must be escaped before insertion into HTML."""
        js = _get_dashboard_js()
        claude_render_fns = _find_claude_functions(js)
        assert claude_render_fns, (
            "No Claude render functions found — must exist before checking esc() usage"
        )
        for fn in claude_render_fns:
            if "innerHTML" in fn:
                assert "esc(" in fn, (
                    f"Claude render function uses innerHTML but does not call esc() "
                    f"for escaping: {fn[:100]}..."
                )
