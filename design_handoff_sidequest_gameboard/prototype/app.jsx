/* global React, Portrait, Bar, NarrationTurnCards, NarrationScroll, NarrationFocus,
   CharacterCard, MapSvg, Inventory, Knowledge, CombatDrawer, DiceOverlay, InputBar, MOCK */
const { useState, useEffect, useMemo } = React;

// ═══════════════════════════════════════════════════════════════
// CONNECT SCREEN
// ═══════════════════════════════════════════════════════════════
function ConnectScreen({ onEnter }) {
  const [name, setName] = useState("Theodora Millwright");
  const [genre, setGenre] = useState("victoria");
  const [world, setWorld] = useState("Ashgate Terrace");
  const g = MOCK.genres.find(x => x.slug === genre) || MOCK.genres[0];

  return (
    <div style={{
      minHeight: "100vh", position: "relative", zIndex: 2,
      display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0,
    }}>
      {/* Left — invocation */}
      <div style={{ padding: "4rem 4rem 4rem", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <div>
          <div className="smallcaps" style={{ marginBottom: "1.2rem" }}>An Entertainment in the Gothic Manner</div>
          <h1 className="display" style={{ fontSize: "4.2rem", lineHeight: 0.95, letterSpacing: "0.02em" }}>
            SideQuest
          </h1>
          <div className="hand" style={{ fontStyle: "italic", fontSize: "1.3rem",
            color: "var(--accent-ink)", marginTop: "0.6rem" }}>
            — a narrator who never tires —
          </div>
          <hr className="rule-thick" style={{ maxWidth: 240, marginTop: "2rem", marginLeft: 0 }} />

          <p style={{ marginTop: "2rem", maxWidth: 440, color: "var(--ink-soft)",
            fontSize: "1.05rem", lineHeight: 1.7 }}>
            You are about to enter a story told in turn with an attentive, unseen Narrator.
            Bring your wits, your nerve, and such companions as you can persuade. The Narrator
            will supply the rest — weather, consequence, and the occasional falsehood.
          </p>
        </div>

        <div style={{ display: "flex", gap: "1.2rem", marginTop: "2rem" }}>
          <div>
            <div className="smallcaps">Current Sessions</div>
            {MOCK.sessions.map((s, i) => (
              <div key={i} style={{ marginTop: 6, fontSize: "0.88rem" }}>
                <span style={{ color: "var(--accent-ink)" }}>{s.host}</span>
                <span style={{ color: "var(--ink-mute)" }}> · {s.world} · {s.players} present · turn {s.turn}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right — connection card */}
      <div style={{ padding: "4rem 4rem", borderLeft: "1px solid var(--paper-edge)",
        background: "linear-gradient(to right, rgba(120,80,40,0.06), transparent 30%)" }}>
        <div className="panel" style={{ maxWidth: 500 }}>
          <div className="panel-heading">
            <h3>The Invocation</h3>
            <span className="smallcaps">No. VII</span>
          </div>

          <div style={{ marginBottom: "1.2rem" }}>
            <div className="smallcaps" style={{ marginBottom: 6 }}>How shall we call you?</div>
            <input className="ink-input" value={name} onChange={e => setName(e.target.value)} />
          </div>

          <div style={{ marginBottom: "1.2rem" }}>
            <div className="smallcaps" style={{ marginBottom: 6 }}>Genre</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
              {MOCK.genres.map(gg => (
                <button key={gg.slug}
                  className={`tweak-chip ${genre === gg.slug ? "active" : ""}`}
                  onClick={() => { setGenre(gg.slug); setWorld(gg.worlds[0]); }}>
                  {gg.name}
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: "1.5rem" }}>
            <div className="smallcaps" style={{ marginBottom: 6 }}>World</div>
            {g.worlds.map(w => (
              <label key={w} style={{
                display: "flex", alignItems: "center", gap: 8, padding: "0.35rem 0",
                cursor: "pointer", fontFamily: "var(--font-serif)",
                color: world === w ? "var(--accent-ink)" : "var(--ink)",
              }}
                onClick={() => setWorld(w)}>
                <span style={{
                  width: 10, height: 10, borderRadius: "50%",
                  border: "1px solid var(--ink-soft)",
                  background: world === w ? "var(--accent)" : "transparent",
                }} />
                {w}
              </label>
            ))}
          </div>

          <div style={{ marginBottom: "1.5rem", padding: "0.8rem 1rem",
            background: "rgba(122,31,34,0.05)", borderLeft: "2px solid var(--accent)" }}>
            <div className="hand" style={{ fontSize: "0.9rem", fontStyle: "italic", color: "var(--ink-soft)" }}>
              <strong style={{ color: "var(--accent-ink)" }}>{world}</strong> — a neighbourhood of Bloomsbury
              where the fog catches in the eaves and the lamps are said, by certain cant-speaking
              witnesses, to listen.
            </div>
          </div>

          <button className="btn btn-primary" style={{ width: "100%", padding: "0.7rem" }}
            onClick={() => onEnter({ name, genre, world })}>
            ❦ Turn the page
          </button>
        </div>

        <div style={{ marginTop: "1.5rem", textAlign: "center" }}>
          <span className="smallcaps" style={{ color: "var(--ink-faint)" }}>
            v. 0.4.11 · connected to hearthstone.local · WebSocket nominal
          </span>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// CHARACTER CREATION — AI-driven dialogue
// ═══════════════════════════════════════════════════════════════
function ChargenScreen({ onDone }) {
  const [step, setStep] = useState(4);
  const [reply, setReply] = useState("");
  const visible = MOCK.chargenDialogue.slice(0, step);

  const submit = () => {
    if (!reply.trim()) return;
    MOCK.chargenDialogue.push({ from: "player", body: reply });
    MOCK.chargenDialogue.push({ from: "gm", body: "Excellent. The page turns. We may now begin." });
    setReply("");
    setStep(MOCK.chargenDialogue.length);
    setTimeout(onDone, 1200);
  };

  return (
    <div style={{ position: "relative", zIndex: 2, maxWidth: 900, margin: "0 auto",
      padding: "3rem 2rem 6rem", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <div className="flex justify-between items-baseline" style={{ marginBottom: "1.2rem" }}>
        <div>
          <div className="smallcaps">Chapter I — The Taking of Particulars</div>
          <h1 className="display" style={{ fontSize: "2.4rem", marginTop: 4 }}>
            A Traveller Arrives
          </h1>
        </div>
        <div className="smallcaps" style={{ color: "var(--ink-faint)" }}>
          step {step - 3} of 6
        </div>
      </div>
      <hr className="rule-thick" style={{ maxWidth: 200, marginLeft: 0 }} />

      <div style={{ flex: 1, padding: "1.5rem 0" }}>
        {visible.map((d, i) => (
          <div key={i} className="anim-fade-in" style={{ marginBottom: "1.4rem" }}>
            {d.from === "gm" ? (
              <div className="narration" style={{ maxWidth: "100%" }}>
                <div className="smallcaps" style={{ color: "var(--accent-soft)", marginBottom: 4 }}>
                  The Narrator
                </div>
                <p style={{ margin: 0 }}>{d.body}</p>
              </div>
            ) : (
              <div style={{ paddingLeft: "1.2rem" }}>
                <div className="smallcaps" style={{ color: "var(--brass)", marginBottom: 4 }}>
                  You
                </div>
                <div className="hand" style={{ fontStyle: "italic", color: "var(--accent-ink)",
                  fontSize: "1.05rem", borderLeft: "2px solid var(--accent)", paddingLeft: "0.9rem" }}>
                  {d.body}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="panel" style={{ marginTop: "1rem" }}>
        <div className="smallcaps" style={{ marginBottom: 8 }}>Your Reply</div>
        <textarea className="ink-input-box" rows="2" value={reply}
          placeholder="&quot;Lithe and deft, inspector — but she favours her left…&quot;"
          onChange={e => setReply(e.target.value)} />
        <div className="flex justify-between items-center" style={{ marginTop: "0.7rem" }}>
          <div className="smallcaps" style={{ color: "var(--ink-faint)" }}>
            or choose: <span style={{ color: "var(--ink)", textDecoration: "underline dotted" }}>Spare & watchful</span> ·
            <span style={{ color: "var(--ink)", textDecoration: "underline dotted", marginLeft: 6 }}>Sturdy & slow</span> ·
            <span style={{ color: "var(--ink)", textDecoration: "underline dotted", marginLeft: 6 }}>Lithe & deft</span>
          </div>
          <button className="btn btn-primary btn-sm" onClick={submit}>Reply ↵</button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// RIGHT RAIL — tabbed panel (shared by Codex/Folio layouts)
// ═══════════════════════════════════════════════════════════════
function RightRail({ messages }) {
  const [tab, setTab] = useState("party");
  return (
    <div className="rail">
      <div className="rail-tabs">
        {["party","sheet","inventory","map","knowledge"].map(t => (
          <button key={t}
            className={`rail-tab ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>

      {tab === "party" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
          {MOCK.party.map(p => <CharacterCard key={p.id} ch={p} />)}
        </div>
      )}

      {tab === "sheet" && (
        <div>
          <div className="flex gap-3" style={{ marginBottom: "1rem" }}>
            <Portrait size={72} monogram="TM" />
            <div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "1.2rem" }}>
                {MOCK.player.name}
              </div>
              <div className="smallcaps" style={{ marginTop: 2 }}>
                Level {MOCK.player.level} {MOCK.player.class}
              </div>
              <div className="hand" style={{ fontStyle: "italic", color: "var(--ink-mute)", fontSize: "0.85rem", marginTop: 4 }}>
                {MOCK.player.location}
              </div>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, marginBottom: "1rem" }}>
            {Object.entries(MOCK.player.stats).map(([k, v]) => (
              <div key={k} className="flex justify-between" style={{
                padding: "0.3rem 0.5rem",
                background: "rgba(255,250,235,0.5)",
                border: "1px solid var(--paper-edge)",
              }}>
                <span className="smallcaps">{k.slice(0, 3)}</span>
                <span className="mono">{v}</span>
              </div>
            ))}
          </div>
          <div className="smallcaps" style={{ marginBottom: 6 }}>Resources</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: "1rem" }}>
            {Object.entries(MOCK.player.resources).map(([k, v]) => (
              <Bar key={k} label={k} cur={v.current} max={v.max}
                tone={k === "Vigor" ? "vigor" : k === "Sanity" ? "sanity" : "hp"}
                flat={v.flat} />
            ))}
          </div>
          <div className="smallcaps" style={{ marginBottom: 6 }}>Abilities</div>
          {MOCK.player.abilities.map(a => (
            <div key={a.name} style={{ marginBottom: 8 }}>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "0.95rem" }}>{a.name}</div>
              <div style={{ fontSize: "0.8rem", color: "var(--ink-mute)", fontStyle: "italic" }}>
                {a.desc}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "inventory" && <Inventory data={MOCK.inventory} />}
      {tab === "map" && <MapSvg data={MOCK.map} compact />}
      {tab === "knowledge" && <Knowledge entries={MOCK.knowledge} />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// LAYOUT: CODEX — center narration, right rail (default)
// ═══════════════════════════════════════════════════════════════
function CodexLayout({ messages, narrationMode, onOpenCombat }) {
  const Renderer = narrationMode === "scroll" ? NarrationScroll
    : narrationMode === "focus" ? NarrationFocus : NarrationTurnCards;
  return (
    <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
      <div className="flex-1 overflow-y-auto" style={{ position: "relative" }}>
        <Renderer messages={messages} />
      </div>
      <RightRail messages={messages} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// LAYOUT: FOLIO — two-page book spread w/ scene image + marginalia
// ═══════════════════════════════════════════════════════════════
function FolioLayout({ messages, narrationMode }) {
  const Renderer = narrationMode === "scroll" ? NarrationScroll
    : narrationMode === "focus" ? NarrationFocus : NarrationTurnCards;
  return (
    <div style={{ display: "flex", flex: 1, minHeight: 0, background:
      "linear-gradient(to right, transparent 49%, rgba(60,38,18,0.18) 50%, transparent 51%)" }}>
      {/* Left page */}
      <div className="flex-1 overflow-y-auto" style={{ padding: "0 0.5rem 0 1rem" }}>
        <Renderer messages={messages} />
      </div>
      {/* Right page */}
      <div className="flex-1 overflow-y-auto" style={{ padding: "2rem 2rem 6rem" }}>
        <div style={{ maxWidth: 520, margin: "0 auto" }}>
          <div className="scene-image">
            <div className="scene-placeholder">
              <div>— plate I —</div>
              <div style={{ marginTop: 4 }}>The Study at Ashgate</div>
            </div>
          </div>
          <div className="hand" style={{ fontStyle: "italic", textAlign: "center",
            marginTop: "0.5rem", color: "var(--ink-mute)", fontSize: "0.85rem" }}>
            "there is no blood, and no window open to the cold"
          </div>

          <div className="ornament" style={{ margin: "1.8rem 0 1rem" }}>❦</div>

          <div className="smallcaps" style={{ marginBottom: 8 }}>In the margin</div>
          <div className="marginalia" style={{ marginBottom: "1rem" }}>
            The candle has burned, by the wax, not more than two hours — <br/>
            yet Whitcombe has been dead since yesterday evening.<br/>
            <em>Someone has been here since.</em>
          </div>

          <div className="smallcaps" style={{ marginBottom: 6 }}>Present</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {MOCK.party.map(p => (
              <div key={p.id} className="flex items-center gap-2">
                <Portrait size={32} monogram={p.name.split(" ").map(w=>w[0]).slice(0,2).join("")} />
                <div style={{ fontSize: "0.88rem" }}>
                  <div>{p.name}</div>
                  <div className="smallcaps" style={{ marginTop: 0 }}>{p.role}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="ornament" style={{ margin: "1.6rem 0 0.8rem" }}>❦</div>
          <div className="smallcaps" style={{ marginBottom: 6 }}>The plan of the house</div>
          <MapSvg data={MOCK.map} compact />
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// LAYOUT: SCRIPTORIUM — scene band on top, narration below
// ═══════════════════════════════════════════════════════════════
function ScriptoriumLayout({ messages, narrationMode }) {
  const Renderer = narrationMode === "scroll" ? NarrationScroll
    : narrationMode === "focus" ? NarrationFocus : NarrationTurnCards;
  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      {/* Scene band */}
      <div style={{ padding: "1rem 2rem 0", maxWidth: 1000, margin: "0 auto", width: "100%" }}>
        <div className="scene-image" style={{ aspectRatio: "21/9" }}>
          <div className="scene-placeholder">
            <div>plate I · the study at ashgate</div>
          </div>
        </div>
        <div className="flex justify-between" style={{ marginTop: "0.5rem" }}>
          <div className="hand" style={{ fontStyle: "italic", color: "var(--ink-mute)", fontSize: "0.85rem" }}>
            — candle burning; body at desk; no blood —
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            {MOCK.party.map(p => (
              <div key={p.id} title={p.name}>
                <Portrait size={28} monogram={p.name.split(" ").map(w=>w[0]).slice(0,2).join("")} />
              </div>
            ))}
          </div>
        </div>
      </div>
      <hr className="rule-thick" style={{ maxWidth: 800, margin: "1rem auto 0" }} />
      <div className="flex" style={{ flex: 1, minHeight: 0 }}>
        <div className="flex-1 overflow-y-auto">
          <Renderer messages={messages} />
        </div>
        <RightRail messages={messages} />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// LAYOUT: MARGINS — icon rails, full-bleed narration, overlays
// ═══════════════════════════════════════════════════════════════
function MarginsLayout({ messages, narrationMode }) {
  const [overlay, setOverlay] = useState(null);
  const Renderer = narrationMode === "scroll" ? NarrationScroll
    : narrationMode === "focus" ? NarrationFocus : NarrationTurnCards;

  const items = [
    { id: "party", letter: "P" },
    { id: "sheet", letter: "C" },
    { id: "inv", letter: "I" },
    { id: "map", letter: "M" },
    { id: "know", letter: "K" },
  ];

  return (
    <div style={{ display: "flex", flex: 1, minHeight: 0, position: "relative" }}>
      <div className="icon-rail">
        {items.map(it => (
          <button key={it.id}
            className={overlay === it.id ? "active" : ""}
            onClick={() => setOverlay(overlay === it.id ? null : it.id)}>
            {it.letter}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto" style={{ position: "relative" }}>
        <Renderer messages={messages} />
      </div>

      {overlay && (
        <div className="overlay-card anim-fade-in" style={{
          top: 40, right: 40, width: 380, maxHeight: "calc(100% - 80px)",
          overflowY: "auto", padding: "1rem 1.2rem",
        }}>
          <div className="panel-heading">
            <h3 style={{ textTransform: "capitalize" }}>
              {overlay === "inv" ? "Inventory"
                : overlay === "know" ? "Knowledge"
                : overlay === "sheet" ? "Character Sheet"
                : overlay}
            </h3>
            <button className="btn btn-sm btn-ghost" onClick={() => setOverlay(null)}>✕</button>
          </div>
          {overlay === "party" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {MOCK.party.map(p => <CharacterCard key={p.id} ch={p} />)}
            </div>
          )}
          {overlay === "sheet" && (
            <div>
              <div className="flex gap-3" style={{ marginBottom: "0.8rem" }}>
                <Portrait size={56} monogram="TM" />
                <div>
                  <div style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem" }}>{MOCK.player.name}</div>
                  <div className="smallcaps">Lv {MOCK.player.level} {MOCK.player.class}</div>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
                {Object.entries(MOCK.player.stats).map(([k, v]) => (
                  <div key={k} className="flex justify-between" style={{
                    padding: "0.3rem 0.5rem", background: "rgba(255,250,235,0.5)",
                    border: "1px solid var(--paper-edge)",
                  }}>
                    <span className="smallcaps">{k.slice(0,3)}</span>
                    <span className="mono">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {overlay === "inv" && <Inventory data={MOCK.inventory} />}
          {overlay === "map" && <MapSvg data={MOCK.map} compact />}
          {overlay === "know" && <Knowledge entries={MOCK.knowledge} />}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// LAYOUT: DM SCREEN — 3 column dossier / narration / world + rail
// ═══════════════════════════════════════════════════════════════
function DMScreenLayout({ messages, narrationMode }) {
  const [tab, setTab] = useState("map");
  const [seen, setSeen] = useState({ knowledge: false, npcs: false });

  // Focus mode for middle column
  const Renderer = narrationMode === "scroll" ? NarrationScroll
    : narrationMode === "focus" ? NarrationFocus : NarrationTurnCards;

  const player = MOCK.player;
  const hpPct = (player.resources.Vigor.current / player.resources.Vigor.max) * 100;
  const sanPct = (player.resources.Sanity.current / player.resources.Sanity.max) * 100;

  const markSeen = (k) => setSeen(s => ({ ...s, [k]: true }));

  return (
    <div className="dm-screen">
      {/* DOSSIER */}
      <aside className="dm-dossier">
        <div style={{ marginBottom: "0.8rem" }}>
          <div className="portrait-frame" style={{ width: "100%", aspectRatio: "1" }}>
            <Portrait size={256} monogram="TM" label="inspector" />
          </div>
        </div>
        <div style={{ fontFamily: "var(--font-display)", fontSize: "1.25rem",
          color: "var(--accent-ink)", letterSpacing: "0.04em" }}>
          {player.name}
        </div>
        <div className="smallcaps" style={{ marginTop: 2 }}>
          Level {player.level} · {player.class}
        </div>
        <div className="hand" style={{ fontStyle: "italic", color: "var(--ink-mute)",
          fontSize: "0.82rem", marginTop: 4 }}>
          {player.location}
        </div>

        <div style={{ marginTop: "1rem" }}>
          <div className="dm-bar-row">
            <div className="dm-bar-label">
              <span>Vigor</span>
              <span className="mono">{player.resources.Vigor.current} / {player.resources.Vigor.max}</span>
            </div>
            <div className="resbar resbar-hp"><div className="resbar-fill" style={{ width: hpPct + "%" }} /></div>
          </div>
          <div className="dm-bar-row">
            <div className="dm-bar-label">
              <span>Sanity</span>
              <span className="mono">{player.resources.Sanity.current} / {player.resources.Sanity.max}</span>
            </div>
            <div className="resbar resbar-sanity"><div className="resbar-fill" style={{ width: sanPct + "%" }} /></div>
          </div>
        </div>

        <div className="dm-section">Afflictions</div>
        <span className="dm-status">alert, pulse quickened</span>
        <span className="dm-status">laudanum — last dose 3 hrs past</span>

        <div className="dm-section">Purse</div>
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          <li style={{ display: "flex", justifyContent: "space-between",
            padding: "3px 0", borderBottom: "1px dashed var(--ink-ghost)", fontSize: "0.9rem" }}>
            <span>Shillings</span><span className="mono">{player.resources.Shillings.current}</span>
          </li>
          <li style={{ display: "flex", justifyContent: "space-between",
            padding: "3px 0", borderBottom: "1px dashed var(--ink-ghost)", fontSize: "0.9rem" }}>
            <span>Warrant card</span><span className="mono">held</span>
          </li>
          <li style={{ display: "flex", justifyContent: "space-between",
            padding: "3px 0", borderBottom: "1px dashed var(--ink-ghost)", fontSize: "0.9rem" }}>
            <span>Laudanum</span><span className="mono">×2</span>
          </li>
        </ul>

        <button className="btn btn-sm" style={{ width: "100%", marginTop: "0.8rem" }}>
          ▸ Full Sheet
        </button>

        <div className="dm-section">Companions</div>
        {MOCK.party.filter(p => !p.active).map(p => (
          <div key={p.id} style={{ display: "flex", alignItems: "center", gap: 8,
            padding: "4px 0", borderBottom: "1px dashed var(--ink-ghost)", fontSize: "0.86rem" }}>
            <Portrait size={28} monogram={p.name.split(" ").map(w=>w[0]).slice(0,2).join("")} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div>{p.name}</div>
              <div className="smallcaps" style={{ fontSize: "0.55rem" }}>{p.role}</div>
            </div>
            <span className="mono" style={{ fontSize: "0.72rem", color: "var(--ink-mute)" }}>
              {p.hp.current}/{p.hp.max}
            </span>
          </div>
        ))}
      </aside>

      {/* NARRATION */}
      <section className="dm-narr">
        <header className="dm-narr-head">
          <div>
            <h1>Chapter II · The Study at Ashgate</h1>
            <div className="smallcaps" style={{ marginTop: 4, color: "var(--ink-faint)" }}>
              Act I · Scene 3 · half past ten, a cold evening
            </div>
          </div>
        </header>
        <div className="dm-narr-body">
          <Renderer messages={messages} />
        </div>
      </section>

      {/* WORLD */}
      <aside className="dm-world">
        <div className="dm-world-tabs" role="tablist">
          {[
            { id: "map", label: "Map" },
            { id: "knowledge", label: "Know", pip: !seen.knowledge },
            { id: "inventory", label: "Gear" },
            { id: "npcs", label: "NPCs", pip: !seen.npcs },
            { id: "log", label: "Log" },
          ].map(t => (
            <button key={t.id}
              aria-pressed={tab === t.id ? "true" : "false"}
              onClick={() => { setTab(t.id); if (t.id === "knowledge") markSeen("knowledge"); if (t.id === "npcs") markSeen("npcs"); }}>
              {t.label}
              {t.pip && <span className="pip" />}
            </button>
          ))}
        </div>
        <div className="dm-world-body">
          {tab === "map" && (
            <>
              <div className="smallcaps" style={{ marginBottom: 6, color: "var(--accent)" }}>
                Ashgate Terrace, No. 7
              </div>
              <MapSvg data={MOCK.map} compact />
              <div className="hand" style={{ fontStyle: "italic", color: "var(--ink-mute)",
                fontSize: "0.85rem", marginTop: "0.5rem" }}>
                3 exits known · 1 unexplored · body in study
              </div>
            </>
          )}

          {tab === "knowledge" && <Knowledge entries={MOCK.knowledge} />}

          {tab === "inventory" && <Inventory data={MOCK.inventory} />}

          {tab === "npcs" && (
            <>
              <div className="smallcaps" style={{ marginBottom: 8, color: "var(--accent)" }}>
                Present Persons
              </div>
              {MOCK.confrontation.actors.map((a, i) => (
                <div key={i} className="dm-fact">
                  <span className="new-badge">new</span>
                  <strong>{a.name}</strong>
                  <small>{a.role} · first seen this scene</small>
                </div>
              ))}
              <div className="dm-fact">
                <strong>Sergeant Finch</strong>
                <small>Constable · waiting on the step · Ch. II</small>
              </div>
              <div className="dm-fact">
                <strong>Mrs. Ives</strong>
                <small>Housekeeper · under brandy · Ch. II</small>
              </div>
            </>
          )}

          {tab === "log" && (
            <>
              <div className="smallcaps" style={{ marginBottom: 8, color: "var(--accent)" }}>
                Facts Gathered
              </div>
              <div className="dm-fact">
                The door to the study was oiled recently.
                <small>observed · Ch. II · this scene</small>
              </div>
              <div className="dm-fact">
                The candle burns, at most, two hours old.
                <small>inferred · Ch. II · wax measurement</small>
              </div>
              <div className="dm-fact">
                Journal page reads: "the lamps have been listening."
                <small>observed · Ch. II · this scene</small>
              </div>
              <div className="dm-fact">
                Whitcombe was an expert in sympathetic resonance.
                <small>known · Ch. I · Home Office briefing</small>
              </div>
            </>
          )}
        </div>
      </aside>

      {/* BOTTOM RAIL */}
      <footer className="dm-bottom">
        <span className="pip-ok">Narrator · nominal</span>
        <span className="pip-ok">Audio · low strings</span>
        <span className="pip-warn">Watcher · 2 flags</span>
        <div className="spacer" />
        <button>Save</button>
        <button>Recap</button>
        <button>Scroll back</button>
      </footer>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// GAMEBOARD — orchestrates layout + combat drawer + dice
// ═══════════════════════════════════════════════════════════════
function GameBoard({ layout, narrationMode, onLeave }) {
  const [messages, setMessages] = useState(MOCK.narration);
  const [combatOpen, setCombatOpen] = useState(false);
  const [diceOpen, setDiceOpen] = useState(false);

  const handleSend = (text, aside) => {
    setMessages(m => [
      ...m,
      { id: "p"+Date.now(), kind: "player", speaker: aside ? "Theodora (aside)" : "Theodora", body: text },
      { id: "g"+Date.now(), kind: "gm", body: "The Narrator considers your words. The fog presses against the windows. Somewhere below, a clock strikes three-quarters of the hour.\n\n" + (aside ? "*I note it, Inspector. It shall not leave this page.*" : "You kneel to examine the journal. The ink of the underscore is still tacky — whoever wrote it did so very recently, and by this candle.") }
    ]);
  };

  const Layouts = {
    codex: CodexLayout,
    folio: FolioLayout,
    scriptorium: ScriptoriumLayout,
    margins: MarginsLayout,
    dmscreen: DMScreenLayout,
  };
  const L = Layouts[layout] || CodexLayout;

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column",
      position: "relative", zIndex: 2 }}>
      {/* Running header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between",
        padding: "0.7rem 1.4rem", borderBottom: "1px solid var(--paper-edge)",
        background: "linear-gradient(to bottom, rgba(232,220,190,0.5), transparent)" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "1.2rem" }}>
          <span className="display" style={{ fontSize: "1.1rem", fontStyle: "italic" }}>
            Ashgate Terrace
          </span>
          <span className="smallcaps" style={{ color: "var(--ink-faint)" }}>
            Chapter II · Turn 14 · Evening, half past ten
          </span>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button className="btn btn-sm btn-ghost" onClick={() => setCombatOpen(true)}>
            ⚔ Enter Confrontation
          </button>
          <button className="btn btn-sm btn-ghost" onClick={onLeave}>
            ⟵ Leave
          </button>
        </div>
      </div>

      <L messages={messages} narrationMode={narrationMode}
        onOpenCombat={() => setCombatOpen(true)} />

      <InputBar onSend={handleSend} />

      <CombatDrawer
        open={combatOpen}
        data={MOCK.confrontation}
        onClose={() => setCombatOpen(false)}
        onBeat={() => setDiceOpen(true)}
        onRoll={() => setDiceOpen(true)}
      />

      <DiceOverlay open={diceOpen} onDone={() => setDiceOpen(false)} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// TWEAKS PANEL — Layout / Narration / Font / Density / Combat style
// ═══════════════════════════════════════════════════════════════
function TweaksPanel({ state, setState, active, onClose }) {
  if (!active) return null;
  const layouts = [
    { id: "codex", label: "Codex" },
    { id: "folio", label: "Folio" },
    { id: "scriptorium", label: "Scriptorium" },
    { id: "margins", label: "Margins" },
    { id: "dmscreen", label: "DM Screen" },
  ];
  return (
    <div className="tweaks">
      <div className="tweaks-head">
        <span className="smallcaps" style={{ color: "var(--paper)" }}>Tweaks</span>
        <button className="btn-ghost" style={{ background:"none", border:"none", color:"var(--paper)", cursor:"pointer" }}
          onClick={onClose}>✕</button>
      </div>
      <div className="tweaks-body">
        <div className="tweak-row">
          <label>Layout</label>
          <div className="tweak-options">
            {layouts.map(l => (
              <button key={l.id}
                className={`tweak-chip ${state.layout === l.id ? "active" : ""}`}
                onClick={() => setState(s => ({ ...s, layout: l.id }))}>{l.label}</button>
            ))}
          </div>
        </div>

        <div className="tweak-row">
          <label>Narration</label>
          <div className="tweak-options" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
            {[
              { id: "turns", label: "Turns" },
              { id: "scroll", label: "Scroll" },
              { id: "focus", label: "Focus" },
            ].map(n => (
              <button key={n.id}
                className={`tweak-chip ${state.narrationMode === n.id ? "active" : ""}`}
                onClick={() => setState(s => ({ ...s, narrationMode: n.id }))}>
                {n.label}
              </button>
            ))}
          </div>
        </div>

        <div className="tweak-row">
          <label>Typeface</label>
          <div className="tweak-options">
            {[
              { id: "baskerville", label: "Baskerville" },
              { id: "crimson", label: "Crimson" },
              { id: "fell", label: "IM Fell" },
              { id: "ebgaramond", label: "Garamond" },
            ].map(f => (
              <button key={f.id}
                className={`tweak-chip ${state.font === f.id ? "active" : ""}`}
                onClick={() => setState(s => ({ ...s, font: f.id }))}>{f.label}</button>
            ))}
          </div>
        </div>

        <div className="tweak-row">
          <label>Density</label>
          <div className="tweak-options" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
            {["compact","normal","roomy"].map(d => (
              <button key={d}
                className={`tweak-chip ${state.density === d ? "active" : ""}`}
                onClick={() => setState(s => ({ ...s, density: d }))}>{d}</button>
            ))}
          </div>
        </div>

        <div className="tweak-row">
          <label>Screen</label>
          <div className="tweak-options" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
            {["connect","chargen","game"].map(s => (
              <button key={s}
                className={`tweak-chip ${state.screen === s ? "active" : ""}`}
                onClick={() => setState(st => ({ ...st, screen: s }))}>{s}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// APP
// ═══════════════════════════════════════════════════════════════
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "layout": "dmscreen",
  "narrationMode": "turns",
  "font": "baskerville",
  "density": "normal",
  "screen": "connect"
}/*EDITMODE-END*/;

function App() {
  const [state, setState] = useState(() => {
    try {
      const saved = localStorage.getItem("sidequest-demo");
      return saved ? { ...TWEAK_DEFAULTS, ...JSON.parse(saved) } : TWEAK_DEFAULTS;
    } catch { return TWEAK_DEFAULTS; }
  });
  const [tweaksOpen, setTweaksOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);

  useEffect(() => {
    try { localStorage.setItem("sidequest-demo", JSON.stringify(state)); } catch {}
    document.documentElement.setAttribute("data-font", state.font);
    document.documentElement.setAttribute("data-density", state.density);
  }, [state]);

  // Edit mode protocol
  useEffect(() => {
    const onMsg = (e) => {
      const d = e.data || {};
      if (d.type === "__activate_edit_mode") { setEditMode(true); setTweaksOpen(true); }
      if (d.type === "__deactivate_edit_mode") { setEditMode(false); setTweaksOpen(false); }
    };
    window.addEventListener("message", onMsg);
    window.parent.postMessage({ type: "__edit_mode_available" }, "*");
    return () => window.removeEventListener("message", onMsg);
  }, []);

  // Persist tweak edits
  useEffect(() => {
    if (!editMode) return;
    window.parent.postMessage({ type: "__edit_mode_set_keys", edits: state }, "*");
  }, [state, editMode]);

  return (
    <>
      <div className="paper-bg" />
      <div className="vignette" />

      <div data-screen-label={state.screen === "connect" ? "01 Connect"
          : state.screen === "chargen" ? "02 Chargen" : "03 GameBoard"}>
        {state.screen === "connect" && (
          <ConnectScreen onEnter={() => setState(s => ({ ...s, screen: "chargen" }))} />
        )}
        {state.screen === "chargen" && (
          <ChargenScreen onDone={() => setState(s => ({ ...s, screen: "game" }))} />
        )}
        {state.screen === "game" && (
          <GameBoard layout={state.layout} narrationMode={state.narrationMode}
            onLeave={() => setState(s => ({ ...s, screen: "connect" }))} />
        )}
      </div>

      {!tweaksOpen && !editMode && (
        <button className="tweak-fab" onClick={() => setTweaksOpen(true)}>
          ☰ Tweaks
        </button>
      )}
      <TweaksPanel state={state} setState={setState} active={tweaksOpen}
        onClose={() => setTweaksOpen(false)} />
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
