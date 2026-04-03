## Architect Decisions

- **Narrative consistency is the #1 product goal.** Mechanical state must back the story. Every subsystem exists to prevent the LLM from "winging it" with zero mechanical backing.
- **World building creative split.** Keith owns mechanics/crunch. World Builder gets creative freedom on flavor/lore/story.
- **Music is cinematic.** Film soundtrack behavior — overtures, cues, one-shots via a2a theme variations. Not looping video game BGM. Pre-rendered files in genre_packs.
- **Infra: Tailscale + R2 + Cloudflare.** Tailscale for playtest networking, R2 for asset backup, Tunnel for long-term exposure.
