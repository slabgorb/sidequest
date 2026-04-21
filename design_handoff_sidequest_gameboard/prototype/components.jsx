/* global React */
const { useState, useEffect, useRef, useMemo, useCallback } = React;

// ═══════════════════════════════════════════════════════════════
// Portrait placeholder — subtle striped SVG with monogram
// ═══════════════════════════════════════════════════════════════
function Portrait({ size = 64, monogram = "?", tone = "dark", label = null }) {
  const bg = tone === "dark"
    ? "linear-gradient(135deg, #3a2818, #1a0f05)"
    : "linear-gradient(135deg, #c9b488, #8a6a2a)";
  return (
    <div className="portrait" style={{ width: size, height: size, background: bg,
      display: "flex", alignItems: "center", justifyContent: "center" }}>
      <svg width={size} height={size} style={{position:"absolute", inset:0, opacity:0.25}}>
        <defs>
          <pattern id={`stripe-${monogram}`} patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
            <rect width="3" height="6" fill="rgba(220,200,160,0.4)"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill={`url(#stripe-${monogram})`} />
      </svg>
      <span style={{
        fontFamily: "var(--font-display)",
        color: "rgba(220,200,160,0.55)",
        fontSize: size * 0.42,
        letterSpacing: "0.05em",
        zIndex: 1,
      }}>
        {monogram}
      </span>
      {label && (
        <span style={{
          position: "absolute", bottom: 2, left: 0, right: 0,
          textAlign: "center", fontFamily: "var(--font-mono)",
          fontSize: 9, color: "rgba(220,200,160,0.4)",
          letterSpacing: "0.15em", textTransform: "uppercase"
        }}>{label}</span>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Resource bar
// ═══════════════════════════════════════════════════════════════
function Bar({ label, cur, max, tone = "hp", flat = false }) {
  const pct = Math.max(0, Math.min(100, (cur / max) * 100));
  return (
    <div style={{ width: "100%" }}>
      <div className="flex justify-between" style={{ marginBottom: 3 }}>
        <span className="smallcaps">{label}</span>
        <span className="mono" style={{ fontSize: "0.75rem", color: "var(--ink-soft)" }}>
          {flat ? cur : `${cur}/${max}`}
        </span>
      </div>
      {!flat && (
        <div className={`resbar resbar-${tone}`}>
          <div className="resbar-fill" style={{ width: pct + "%" }} />
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Narration renderers — three modes
// ═══════════════════════════════════════════════════════════════
function NarrationTurnCards({ messages }) {
  // Group by turn — a turn starts when player speaks
  const turns = useMemo(() => {
    const groups = [];
    let current = { player: null, gm: [], chapter: null };
    for (const m of messages) {
      if (m.kind === "player") {
        if (current.player || current.gm.length) groups.push(current);
        current = { player: m, gm: [], chapter: null };
      } else if (m.kind === "chapter") {
        if (current.player || current.gm.length) groups.push(current);
        current = { player: null, gm: [], chapter: m };
      } else {
        current.gm.push(m);
      }
    }
    if (current.player || current.gm.length || current.chapter) groups.push(current);
    return groups;
  }, [messages]);

  return (
    <div style={{ padding: "3rem 2rem 6rem" }}>
      {turns.map((t, i) => (
        <div key={i} className="turn-card anim-fade-in">
          {t.chapter && (
            <div style={{ textAlign: "center", margin: "2rem 0 3rem" }}>
              <div className="ornament">❦</div>
              <h2 className="display" style={{ fontSize: "1.7rem", fontStyle: "italic" }}>
                {t.chapter.body}
              </h2>
              <hr className="rule-thick" style={{ maxWidth: 200, margin: "1.2rem auto 0" }} />
            </div>
          )}
          {t.player && (
            <>
              <div className="turn-marker">
                <span className="dot" /><span>Turn {i + 1} · {t.player.speaker ?? "You"}</span>
              </div>
              <div className="player-line">{t.player.body}</div>
            </>
          )}
          {t.gm.map((g, gi) => (
            <div key={gi} className={`narration ${i === 0 && gi === 0 ? "drop-cap" : ""}`}>
              {g.body.split("\n\n").map((para, pi) => (
                <p key={pi} dangerouslySetInnerHTML={{
                  __html: para
                    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                    .replace(/\*(.+?)\*/g, "<em>$1</em>")
                }} />
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function NarrationScroll({ messages }) {
  // Continuous book-page scroll — all messages flow as one column
  return (
    <div style={{ padding: "3rem 2rem 6rem" }}>
      <div className="narration drop-cap">
        {messages.map((m, i) => {
          if (m.kind === "chapter") {
            return (
              <div key={i} style={{ textAlign: "center", margin: "2rem 0" }}>
                <div className="ornament">❦ ❦ ❦</div>
                <h2 className="display" style={{ fontSize: "1.5rem", fontStyle: "italic" }}>
                  {m.body}
                </h2>
                <hr className="rule-thick" style={{ maxWidth: 160, margin: "0.8rem auto 1.6rem" }} />
              </div>
            );
          }
          if (m.kind === "player") {
            return <div key={i} className="player-line">{m.body}</div>;
          }
          return m.body.split("\n\n").map((para, pi) => (
            <p key={`${i}-${pi}`} dangerouslySetInnerHTML={{
              __html: para
                .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                .replace(/\*(.+?)\*/g, "<em>$1</em>")
            }} />
          ));
        })}
      </div>
    </div>
  );
}

function NarrationFocus({ messages }) {
  // Focus mode: last turn bright, older fades
  const turns = useMemo(() => {
    const groups = [];
    let current = { player: null, gm: [], chapter: null };
    for (const m of messages) {
      if (m.kind === "player") {
        if (current.player || current.gm.length) groups.push(current);
        current = { player: m, gm: [], chapter: null };
      } else if (m.kind === "chapter") {
        if (current.player || current.gm.length) groups.push(current);
        current = { player: null, gm: [], chapter: m };
      } else { current.gm.push(m); }
    }
    if (current.player || current.gm.length || current.chapter) groups.push(current);
    return groups;
  }, [messages]);

  return (
    <div style={{ padding: "2rem 2rem 6rem" }}>
      {turns.map((t, i) => {
        const isCurrent = i === turns.length - 1;
        const distance = turns.length - 1 - i;
        const opacity = isCurrent ? 1 : Math.max(0.25, 1 - distance * 0.25);
        return (
          <div key={i} className="turn-card" style={{
            opacity, transition: "opacity 400ms",
            filter: isCurrent ? "none" : "saturate(0.6)",
          }}>
            {t.chapter && (
              <div style={{ textAlign: "center", margin: "1.5rem 0" }}>
                <h2 className="display" style={{ fontSize: "1.4rem", fontStyle: "italic" }}>{t.chapter.body}</h2>
              </div>
            )}
            {t.player && (
              <>
                <div className="turn-marker">
                  <span className="dot" /><span>{t.player.speaker ?? "You"}</span>
                </div>
                <div className="player-line">{t.player.body}</div>
              </>
            )}
            {t.gm.map((g, gi) => (
              <div key={gi} className={`narration ${isCurrent && gi === 0 ? "drop-cap" : ""}`}>
                {g.body.split("\n\n").map((para, pi) => (
                  <p key={pi} dangerouslySetInnerHTML={{
                    __html: para
                      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                      .replace(/\*(.+?)\*/g, "<em>$1</em>")
                  }} />
                ))}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Character card (stacked)
// ═══════════════════════════════════════════════════════════════
function CharacterCard({ ch, expanded = false }) {
  const mon = ch.name.split(" ").map(w => w[0]).slice(0, 2).join("");
  return (
    <div className="card anim-fade-in" style={{
      borderLeft: ch.active ? "3px solid var(--accent)" : "3px solid transparent",
    }}>
      <div className="flex gap-3" style={{ alignItems: "flex-start" }}>
        <Portrait size={expanded ? 72 : 56} monogram={mon} />
        <div className="flex-1" style={{ minWidth: 0 }}>
          <div className="flex justify-between items-baseline">
            <div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "1.05rem", lineHeight: 1.1 }}>
                {ch.name}
              </div>
              <div className="smallcaps" style={{ marginTop: 2 }}>{ch.role}</div>
            </div>
            {ch.active && <span className="tag tag-danger">Acting</span>}
          </div>
          <div className="flex-col" style={{ display: "flex", gap: 6, marginTop: 10 }}>
            <Bar label="Vigor" cur={ch.hp.current} max={ch.hp.max} tone="hp" />
            <Bar label="Sanity" cur={ch.sanity.current} max={ch.sanity.max} tone="sanity" />
          </div>
          {ch.status.length > 0 && (
            <div style={{ marginTop: 8, display: "flex", gap: 4, flexWrap: "wrap" }}>
              {ch.status.map(s => (
                <span key={s} className="tag" style={{
                  color: s === "Bleeding" ? "var(--accent)"
                       : s === "Entranced" ? "var(--brass)" : "var(--ink-mute)",
                  borderColor: "currentColor"
                }}>{s}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SVG Map
// ═══════════════════════════════════════════════════════════════
function MapSvg({ data, compact = false }) {
  const roomsById = useMemo(() => {
    const m = {};
    data.rooms.forEach(r => { m[r.id] = r; });
    return m;
  }, [data]);

  const h = compact ? 260 : 380;
  return (
    <div style={{ position: "relative", width: "100%" }}>
      <svg viewBox="0 0 700 380" style={{ width: "100%", height: h, display: "block" }}>
        <defs>
          <pattern id="map-hatch" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(30)">
            <line x1="0" y1="0" x2="0" y2="4" stroke="rgba(60,38,18,0.12)" strokeWidth="1" />
          </pattern>
          <filter id="ink-rough">
            <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" />
            <feDisplacementMap in="SourceGraphic" scale="1.5" />
          </filter>
        </defs>

        {/* Paper bed */}
        <rect x="0" y="0" width="700" height="380" fill="url(#map-hatch)" opacity="0.5" />

        {/* Exits */}
        {data.exits.map(([a, b], i) => {
          const A = roomsById[a], B = roomsById[b];
          if (!A || !B) return null;
          return (
            <line key={i}
              x1={A.x} y1={A.y} x2={B.x} y2={B.y}
              stroke="var(--ink-soft)" strokeWidth="1.2"
              strokeDasharray={A.type === "unknown" || B.type === "unknown" ? "3 4" : "0"}
              opacity="0.6" />
          );
        })}

        {/* Rooms */}
        {data.rooms.map(r => {
          const isCurrent = r.id === data.currentRoom;
          const isUnknown = r.type === "unknown";
          const w = r.name.length * 6 + 28;
          return (
            <g key={r.id} transform={`translate(${r.x},${r.y})`}>
              {isCurrent && (
                <circle r="26" fill="none" stroke="var(--accent)" strokeWidth="1.5"
                  strokeDasharray="2 3" style={{ animation: "dieRoll 8s linear infinite" }} />
              )}
              <rect x={-w/2} y="-14" width={w} height="28" rx="1"
                fill={isUnknown ? "rgba(60,38,18,0.15)" : "rgba(245, 236, 213, 0.9)"}
                stroke={isCurrent ? "var(--accent)" : "var(--ink-soft)"}
                strokeWidth={isCurrent ? 1.6 : 1}
                opacity={isUnknown ? 0.5 : 1} />
              <text textAnchor="middle" y="4"
                fontFamily="var(--font-display)"
                fontSize="11"
                letterSpacing="0.06em"
                fill={isUnknown ? "var(--ink-faint)" : isCurrent ? "var(--accent)" : "var(--ink)"}>
                {isUnknown ? "?" : r.name}
              </text>
            </g>
          );
        })}

        {/* compass */}
        <g transform="translate(640, 50)" opacity="0.4">
          <circle r="22" fill="none" stroke="var(--ink-soft)" strokeWidth="0.8" />
          <text y="-10" textAnchor="middle" fontSize="10" fontFamily="var(--font-display)" fill="var(--ink-soft)">N</text>
          <text y="18" textAnchor="middle" fontSize="10" fontFamily="var(--font-display)" fill="var(--ink-soft)">S</text>
          <line x1="0" y1="-18" x2="0" y2="18" stroke="var(--ink-soft)" strokeWidth="0.6" />
          <line x1="-18" y1="0" x2="18" y2="0" stroke="var(--ink-soft)" strokeWidth="0.6" />
          <polygon points="0,-14 -3,0 0,-3 3,0" fill="var(--accent)" />
        </g>
      </svg>
      <div style={{
        position: "absolute", top: 8, left: 10,
        fontFamily: "var(--font-hand)", fontStyle: "italic",
        fontSize: "0.8rem", color: "var(--ink-mute)"
      }}>
        {data.rooms.find(r => r.id === data.currentRoom)?.name} —
        <span style={{ marginLeft: 4 }}>surveyed {data.rooms.filter(r => r.type !== "unknown").length} of {data.rooms.length} chambers</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Inventory
// ═══════════════════════════════════════════════════════════════
function Inventory({ data }) {
  const grouped = useMemo(() => {
    const g = {};
    data.forEach(i => { (g[i.type] ||= []).push(i); });
    return g;
  }, [data]);
  return (
    <div style={{ padding: "0.4rem 0" }}>
      {Object.entries(grouped).map(([type, items]) => (
        <div key={type} style={{ marginBottom: "0.9rem" }}>
          <div className="smallcaps" style={{ marginBottom: 4 }}>{type}</div>
          {items.map(it => (
            <div key={it.name} style={{
              padding: "0.5rem 0.6rem",
              borderLeft: it.equipped ? "2px solid var(--accent)" : "2px solid transparent",
              background: it.equipped ? "rgba(122,31,34,0.05)" : "transparent",
              marginBottom: 3
            }}>
              <div className="flex justify-between items-baseline">
                <span style={{ fontFamily: "var(--font-serif)", fontSize: "0.95rem" }}>
                  {it.name}
                  {it.qty > 1 && <span style={{ color: "var(--ink-mute)", marginLeft: 6 }}>×{it.qty}</span>}
                </span>
                {it.equipped && <span className="smallcaps" style={{ color: "var(--accent)" }}>Worn</span>}
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--ink-mute)", fontStyle: "italic", marginTop: 2 }}>
                {it.desc}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Knowledge journal
// ═══════════════════════════════════════════════════════════════
function Knowledge({ entries }) {
  return (
    <div>
      {entries.map((e, i) => (
        <div key={i} style={{ marginBottom: "1rem", paddingBottom: "0.8rem", borderBottom: "1px solid var(--ink-ghost)" }}>
          <div className="flex items-baseline justify-between">
            <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem" }}>{e.title}</div>
            <span className="tag tag-note">{e.kind}</span>
          </div>
          <div style={{ fontSize: "0.88rem", color: "var(--ink-soft)", marginTop: 4, fontStyle: "italic" }}>
            {e.body}
          </div>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Combat drawer — turn order, beats, dice
// ═══════════════════════════════════════════════════════════════
function CombatDrawer({ open, data, onClose, onBeat, onRoll }) {
  if (!data) return null;
  const pct = data.metric.threshold_high
    ? (data.metric.current / data.metric.threshold_high) * 100 : 0;

  return (
    <div className={`drawer ${open ? "open" : ""}`}>
      <div style={{ padding: "1.2rem 1.4rem 1.4rem" }}>
        <div className="flex justify-between items-baseline" style={{ marginBottom: 10 }}>
          <div>
            <div className="smallcaps" style={{ color: "var(--accent-soft)" }}>{data.category}</div>
            <h2 className="display" style={{ fontSize: "1.4rem", color: "var(--paper)", marginTop: 4 }}>
              {data.label}
            </h2>
          </div>
          <button className="btn btn-sm" style={{ color: "var(--paper)", borderColor: "rgba(220,180,120,0.4)" }}
            onClick={onClose}>✕</button>
        </div>

        <div style={{ fontFamily: "var(--font-hand)", fontStyle: "italic",
          color: "rgba(220,200,160,0.7)", fontSize: "0.92rem", marginBottom: "1.2rem" }}>
          The air carries {data.mood}.
        </div>

        {/* Metric */}
        <div style={{ marginBottom: "1.4rem" }}>
          <div className="flex justify-between" style={{ marginBottom: 4 }}>
            <span className="smallcaps" style={{ color: "rgba(220,200,160,0.6)" }}>
              {data.metric.name}
            </span>
            <span className="mono" style={{ color: "var(--paper)", fontSize: "0.82rem" }}>
              {data.metric.current} / {data.metric.threshold_high}
            </span>
          </div>
          <div style={{ height: 8, background: "rgba(220,180,120,0.15)",
            border: "1px solid rgba(220,180,120,0.3)", position: "relative" }}>
            <div style={{ position: "absolute", inset: 0, width: pct + "%",
              background: "linear-gradient(to right, var(--accent), var(--accent-bright))" }} />
          </div>
        </div>

        {/* Actors */}
        <div className="smallcaps" style={{ color: "rgba(220,200,160,0.6)", marginBottom: 8 }}>
          Dramatis Personae
        </div>
        {data.actors.map((a, i) => (
          <div key={i} className="flex items-center gap-3" style={{ marginBottom: 8 }}>
            <Portrait size={36} monogram={a.name.split(" ").map(w => w[0]).slice(0, 2).join("")} />
            <div>
              <div style={{ color: "var(--paper)", fontFamily: "var(--font-serif)", fontSize: "0.92rem" }}>
                {a.name}
              </div>
              <div style={{ color: "rgba(220,200,160,0.5)", fontSize: "0.72rem", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                {a.role}
              </div>
            </div>
          </div>
        ))}

        <hr style={{ border: "none", borderTop: "1px solid rgba(220,180,120,0.2)", margin: "1.3rem 0" }} />

        <div className="smallcaps" style={{ color: "rgba(220,200,160,0.6)", marginBottom: 10 }}>
          Available Beats
        </div>
        {data.beats.map(b => (
          <button key={b.id} className="beat-option"
            style={{ borderLeftColor: b.resolution ? "var(--brass)" : "var(--accent)" }}
            onClick={() => onBeat(b)}>
            <div>
              <span className="stat-tag">{b.stat}</span>
              {b.label}
            </div>
            <div style={{ marginTop: 6, display: "flex", gap: 8, alignItems: "center" }}>
              <span className="mono" style={{ fontSize: "0.72rem", color: "rgba(220,200,160,0.55)" }}>
                {b.delta > 0 ? `+${b.delta}` : b.delta} insight
              </span>
              {b.risk && (
                <span className="tag" style={{ color: "var(--accent-bright)", borderColor: "var(--accent-bright)" }}>
                  risks {b.risk}
                </span>
              )}
              {b.resolution && <span className="tag tag-note">resolves</span>}
            </div>
          </button>
        ))}

        <button className="btn" style={{ width: "100%", marginTop: "1rem",
          borderColor: "rgba(220,180,120,0.4)", color: "var(--paper)" }}
          onClick={onRoll}>
          ⚅ Throw the dice
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Dice overlay
// ═══════════════════════════════════════════════════════════════
function DiceOverlay({ open, onDone }) {
  const [face, setFace] = useState(null);
  const [rolling, setRolling] = useState(false);

  useEffect(() => {
    if (open) {
      setRolling(true);
      setFace(null);
      const t = setTimeout(() => {
        const n = 1 + Math.floor(Math.random() * 20);
        setFace(n);
        setRolling(false);
      }, 900);
      return () => clearTimeout(t);
    }
  }, [open]);

  if (!open) return null;
  return (
    <div className="dice-overlay" onClick={() => !rolling && onDone(face)}>
      <div className="smallcaps" style={{ color: "rgba(220,200,160,0.6)", marginBottom: "1.5rem" }}>
        Intellect check · DC 13
      </div>
      <div className={`die d20 ${rolling ? "rolling" : ""}`}>
        {face ?? "⚅"}
      </div>
      {!rolling && face !== null && (
        <>
          <div style={{ color: "var(--paper)", fontFamily: "var(--font-display)",
            fontSize: "1.4rem", marginTop: "1.5rem", letterSpacing: "0.1em" }}>
            {face} + 5 = {face + 5} · {face + 5 >= 13 ? "SUCCESS" : "FAIL"}
          </div>
          <div style={{ color: "rgba(220,200,160,0.5)", marginTop: "0.8rem",
            fontFamily: "var(--font-hand)", fontStyle: "italic" }}>
            click anywhere to continue
          </div>
        </>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Input bar — pen & ink
// ═══════════════════════════════════════════════════════════════
function InputBar({ onSend }) {
  const [value, setValue] = useState("");
  const [aside, setAside] = useState(false);

  const send = () => {
    if (!value.trim()) return;
    onSend(value, aside);
    setValue("");
  };

  return (
    <div className="flex items-center gap-3" style={{
      padding: "1rem 1.4rem",
      borderTop: "1px solid var(--paper-edge)",
      background: "linear-gradient(to top, rgba(232,220,190,0.6), transparent)",
    }}>
      <span className="smallcaps" style={{ color: aside ? "var(--brass)" : "var(--ink-mute)" }}>
        {aside ? "Aside" : "You"}
      </span>
      <input
        className="ink-input"
        value={value}
        placeholder={aside ? "a private word with the narrator…" : "what do you do?"}
        onChange={e => setValue(e.target.value)}
        onKeyDown={e => e.key === "Enter" && send()}
      />
      <button className="btn btn-sm btn-ghost" onClick={() => setAside(a => !a)}>
        {aside ? "speak aloud" : "aside"}
      </button>
      <button className="btn btn-sm btn-primary" onClick={send}>↵ Send</button>
    </div>
  );
}

Object.assign(window, {
  Portrait, Bar,
  NarrationTurnCards, NarrationScroll, NarrationFocus,
  CharacterCard, MapSvg, Inventory, Knowledge,
  CombatDrawer, DiceOverlay, InputBar,
});
