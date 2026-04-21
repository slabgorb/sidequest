/* Gaslamp Hollow — mock session data */

window.MOCK = {
  player: {
    name: "Theodora Millwright",
    title: "Inspector of the Crown's Unusual Affairs",
    class: "Alienist",
    level: 4,
    location: "Ashgate Terrace, No. 7",
    portrait: null,
    pronouns: "she/her",
    stats: {
      Intellect: 16, Resolve: 14, Presence: 13,
      Agility: 11, Constitution: 12, Arcana: 15,
    },
    resources: {
      Vigor:   { current: 18, max: 24 },
      Sanity:  { current: 11, max: 16 },
      Shillings: { current: 47, max: 100, flat: true },
    },
    abilities: [
      { name: "Cold Reading", desc: "Discern a stranger's secret with a successful Presence check." },
      { name: "Phrenological Insight", desc: "Once per scene, glean a truth from a subject's countenance." },
      { name: "Laudanum Fortitude", desc: "Ignore one failed Resolve save per session." },
    ],
    backstory: "Formerly of Bethlem Hospital; now employed at the discreet request of the Home Office to investigate matters that the coroner will not sign his name to."
  },
  party: [
    {
      id: "theo", name: "Theodora Millwright", role: "Alienist",
      hp: { current: 18, max: 24 }, sanity: { current: 11, max: 16 },
      status: ["Alert"], active: true,
    },
    {
      id: "ephraim", name: "Rev. Ephraim Gage", role: "Defrocked Priest",
      hp: { current: 15, max: 22 }, sanity: { current: 14, max: 18 },
      status: ["Holds Revolver"], active: false,
    },
    {
      id: "cora", name: "Cora Whitstable", role: "Medium",
      hp: { current: 9, max: 16 }, sanity: { current: 6, max: 20 },
      status: ["Bleeding", "Entranced"], active: false,
    },
  ],
  // Narration messages — a scene unfolding at Ashgate Terrace
  narration: [
    {
      id: "n1", kind: "gm",
      body: "The hansom halts at the kerb of Ashgate Terrace, where the gaslight throws a sickly halo through the fog. The house at number seven leans a degree past plumb, as though disinclined to meet visitors. A black crepe has been nailed above the door; someone, very recently, has died here.\n\nSergeant Finch is waiting on the step, worrying the brim of his hat. \"Inspector. The housekeeper found him this morning. She hasn't stopped screaming since, poor woman — we've given her brandy and a constable.\""
    },
    {
      id: "n2", kind: "player", speaker: "Theodora",
      body: "\"Has anyone else been inside since she raised the alarm?\""
    },
    {
      id: "n3", kind: "gm",
      body: "Finch shakes his head, relieved to be asked a question he can answer. \"Only myself, ma'am, and Constable Rhodes to cover the back. We've touched nothing. The door to the study is — well. You'll want to see it for yourself, I think.\"\n\nHe leads you up the narrow stair. The air thickens as you climb — not merely with the peculiar sweetness of old roses, but with something beneath it, something that sets the small hairs at the nape of your neck to attention. At the landing, the study door stands ajar by perhaps three fingers' width. A thin seam of yellow candlelight escapes, though no candle should still be lit by now."
    },
    {
      id: "n4", kind: "chapter",
      body: "Chapter II — The Study at Ashgate"
    },
    {
      id: "n5", kind: "gm",
      body: "You push the door. It opens without sound — recently oiled, an observation you store — onto a room that has been arranged with the care of a tableau vivant.\n\nThe body of Dr. Aubrey Whitcombe is seated at his writing desk, head tilted back, jaw slack. His hands rest, palms upward, on either side of an open journal. There is **no blood**, no disarray, and no window open to the cold. The candle on the desk burns steadily — it has burned, you judge by the wax, for not more than two hours.\n\nOn the journal's open page, a single phrase is written in an unsteady hand, and then underscored three times:\n\n*the lamps have been listening*"
    },
  ],
  knowledge: [
    { title: "Dr. Aubrey Whitcombe", kind: "Person", body: "Natural philosopher, Fellow of the Royal Society. Published 'On Sympathetic Resonance in the Galvanic Medium' (1881). No immediate family." },
    { title: "Ashgate Terrace", kind: "Place", body: "A row of twelve Georgian houses in the Bloomsbury parish. Number 7 owned outright by Whitcombe since 1879." },
    { title: "The Gaslamp Choir", kind: "Rumour", body: "A cant phrase overheard in Seven Dials — \"when the lamps sing, the Choir is listening.\" Dismissed by Inspector Halsey as costermonger nonsense." },
    { title: "Sympathetic Resonance", kind: "Lore", body: "Whitcombe's hypothesis: that galvanised materials, tuned correctly, may transmit impressions across distance. Derided by the Society." },
  ],
  inventory: [
    { name: "Laudanum, small bottle", type: "Consumable", qty: 2, equipped: false, desc: "Three drops steady the nerves; five drops are reckless; ten are final." },
    { name: "Derringer, two-barrel", type: "Weapon", qty: 1, equipped: true, desc: "A gentleman's pocket piece. Discreet, inaccurate beyond ten paces." },
    { name: "Brass lens, Dollond & Aitchison", type: "Tool", qty: 1, equipped: false, desc: "Three-diopter; reveals marks the unaided eye misses." },
    { name: "Warrant card", type: "Document", qty: 1, equipped: true, desc: "Sealed authority of the Home Office. Do not misplace." },
    { name: "Notebook, half-filled", type: "Document", qty: 1, equipped: false, desc: "Observations from prior cases. The last entry is illegible." },
    { name: "Silver vesta case", type: "Tool", qty: 1, equipped: true, desc: "A dozen matches. Engraved: 'T.A.M. — 1882.'" },
  ],
  map: {
    currentRoom: "study",
    rooms: [
      { id: "street", name: "Ashgate Terrace", x: 120, y: 220, type: "exterior" },
      { id: "hall",   name: "Entrance Hall",   x: 240, y: 220, type: "normal" },
      { id: "parlour",name: "Parlour",         x: 240, y: 130, type: "normal" },
      { id: "kitchen",name: "Kitchen (below)", x: 340, y: 300, type: "normal" },
      { id: "stair",  name: "Stair Landing",   x: 360, y: 160, type: "normal" },
      { id: "study",  name: "Study",           x: 460, y: 110, type: "scene" },
      { id: "bedroom",name: "Bedroom",         x: 480, y: 210, type: "unknown" },
      { id: "attic",  name: "Attic",           x: 580, y: 90,  type: "unknown" },
    ],
    exits: [
      ["street","hall"], ["hall","parlour"], ["hall","kitchen"],
      ["hall","stair"], ["stair","study"], ["stair","bedroom"],
      ["study","attic"],
    ]
  },
  confrontation: {
    type: "investigation",
    label: "The Thing at the Writing Desk",
    category: "Investigation — Tense",
    mood: "a prickling dread",
    metric: { name: "Insight", current: 3, starting: 2, threshold_high: 8, threshold_low: 0 },
    actors: [
      { name: "Theodora Millwright", role: "Inspector" },
      { name: "Dr. Whitcombe (deceased)", role: "Victim" },
      { name: "The Candle", role: "Unnatural Witness" },
    ],
    beats: [
      { id: "b1", label: "Examine the journal's open page without touching it.", stat: "Intellect", risk: null, delta: 2 },
      { id: "b2", label: "Extinguish the candle. Look for what goes out with it.", stat: "Arcana", risk: "Sanity", delta: 3 },
      { id: "b3", label: "Search the body for hidden papers.", stat: "Agility", risk: "Contaminate scene", delta: 1 },
      { id: "b4", label: "Call for Cora — let her touch the desk.", stat: "Presence", risk: "Cora's Sanity", delta: 4 },
      { id: "b5", label: "Withdraw. Question the housekeeper first.", stat: "Resolve", risk: null, delta: -1, resolution: true },
    ],
  },
  genres: [
    { slug: "victoria",       name: "Victoria", worlds: ["Ashgate Terrace","The Whitechapel Beat","Spiritist Brighton"] },
    { slug: "low_fantasy",    name: "Low Fantasy", worlds: ["The Gilt Road","Hollow Marches"] },
    { slug: "mutant_wasteland",name: "Mutant Wasteland", worlds: ["Flickering Reach"] },
    { slug: "heavy_metal",    name: "Heavy Metal", worlds: ["Blacksteel Peaks"] },
    { slug: "elemental_harmony",name:"Elemental Harmony", worlds: ["The Quiet Archipelago"] },
  ],
  sessions: [
    { host: "H. Carmichael", world: "The Whitechapel Beat", players: 3, turn: 42 },
    { host: "A. Wren",       world: "Spiritist Brighton",   players: 2, turn: 17 },
  ],
  chargenDialogue: [
    { from: "gm", body: "Welcome, traveller. I am the Narrator — the invisible hand that turns the pages of this story with you. Before we begin, I should like to know who you are. Tell me, first: what name do they whisper when they speak of you?" },
    { from: "player", body: "Theodora Anne Millwright." },
    { from: "gm", body: "A fine name, weighted with its own past. And what is your calling? Choose the one that fits like a well-worn glove, or invent a vocation of your own." },
    { from: "gm", body: "Options: Alienist · Defrocked Priest · Medium · Crown's Agent · Other..." },
    { from: "player", body: "Alienist — but one who has seen more than her profession permits her to say." },
    { from: "gm", body: "Good. A physician of minds, haunted by her own. Now, the body — is it spare and watchful, sturdy and slow, or lithe and deft?" },
  ],
};
