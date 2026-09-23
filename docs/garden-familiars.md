# Garden Familiars brief — POW first consumer product (source material)

> Saved verbatim 2026-09-23 (enclosure SVG diagram omitted — conceptual
> layout only, kept in the original note). Design concepts with hypothetical
> prices, NOT validated manufacturing costs, sales forecasts, photographs of
> finished products, or waterproof-test results. Every aoc claim derived
> from this file carries those caveats — see `segments/garden_familiars/`.

---

# POW Garden Familiars: personalised garden creatures that talk to your AI

Proposed first consumer product.

A garden creature could support an entire Etsy shop on its own. The appealing
part isn't merely that it measures moisture: you design a little character,
give it a name, put it in your garden and it becomes part of your digital world.

Imagine a little frog called Sir Hopsalot living beside your tomatoes. He glows
when the soil gets dry. Your Muse can ask POW for his latest readings, and you
receive a message when the garden needs attention. For a birthday, someone could
design a character based on the recipient's pet, choose its colours, add the
plant's name and have it delivered ready to pair.

Competition exists at both ends: Etsy sellers offer decorative moisture-indicator
worms and personalised plant markers, while Ecowitt sells wireless outdoor
moisture sensors from $17.99 (separate gateway required for connected features).
The opportunity to test is the combination of original character design,
genuinely useful sensing and an assistant-compatible digital identity.

## 1. The Garden Familiar collection (design concepts + target retail prices)

| Product | Concept | Price |
| --- | --- | --- |
| Sir Hopsalot | Frog guarding tomatoes. Personalised colour, nameplate, watering alerts. | $39 |
| Sporebert | Mushroom among herbs; light changes when its plant needs attention. | $39 |
| Boo Bloom | Little garden ghost, optional personal dedication. Suited to gifting. | $35 |
| Dewdrop | Tiny dragon, detachable decorative wings, custom name. | $39 |

Plus planned: owl (seed trays), bee (balcony flowers), tortoise (succulents),
gnome (vegetable beds). Customers choose body, face, colours, accessories,
name and alert personality.

Manufacturing rule: each creature is a decorative shell fitting the same sealed
electronic capsule + replaceable soil probe. The frog and mushroom must not
require two different circuit boards.

## 2. Three versions (separate the gift from the connected device)

| Version | What the customer gets | Target price |
| --- | --- | --- |
| Garden Friend | Personalised creature + plant label, NFC identity, manual watering journal; no battery | $15–$24 |
| Garden Familiar | Personalised screenless Wi-Fi creature, moisture readings, notifications | $39–$49 |
| Garden Familiar Outdoor+ | Weather-resistant enclosure, qualified outdoor probe, battery status, optional extra sensing | $59–$69 |

The Friend is the Christmas/birthday gift: it creates the named digital plant
with no electronics. The Familiar turns that plant into a living data source.

Connected spec: 55–70 mm character above soil; 80–120 mm probe below;
one button + one LED (tap = status, hold = pairing); replaceable batteries
(proposed 3×AA, subject to testing); wakes periodically, measures, transmits
over 2.4 GHz Wi-Fi, sleeps. No camera, microphone, speaker or screen.

## 3. Components (checked supplier listings; ex-delivery/tax/volume)

- Controller (prototype): ESP32-C3-WROOM-02 via LCSC, ~$2.44 @100 units
- Indoor probe reference: DFRobot SEN0193, $5.90 (moisture-resistant area, indoor-positioned)
- Outdoor probe reference: DFRobot SEN0308, $14.90, explicitly IP65-rated, large probe — reference for early outdoor prototypes, not necessarily the production part
- Board assembly: JLCPCB, economic setup ~$8.18/order + charges
- Outdoor enclosures: JLC3DP, ASA FDM / MJF nylon, quote by design
- Plus: low-power regulator for Wi-Fi peaks, battery holder, gasket, LED, tactile switch, wiring, sealed sensor connection (part numbers after reference-circuit testing; no bulk buys first)

OEM caution: a claimed IP rating, bulk price or epoxy coating is NOT evidence
of long-term outdoor reliability. Test replacements against the DFRobot
reference over repeated wet/dry cycles.

## 4. Waterproofing rules (hard constraints for all copy)

- Two pieces: functional waterproof capsule + decorative replaceable character.
  An elaborate customer shell must never be responsible for keeping rain out.
- Shell sheds water away from the capsule; never traps wet soil against it.
- Target IP65, test the COMPLETE assembled product (battery door + probe
  connection included). IP65 ≠ immersion.
- **Do not advertise any IP rating until the finished design has passed the test.**
- Condensation testing required (temperature swings, trapped moisture; Gore
  vents are a later-revision option, not v1).
- Shell: UV-resistant ASA (outdoor UV/temperature beats indoor materials).

## 5. Copy constraints derived from this brief

- Prices are hypothetical targets ($39–49 etc.), not validated costs.
- Images are design concepts, not photographs of finished/tested products.
- Competition acknowledged wherever differentiation is claimed.
- Screenless Wi-Fi creature: no camera/mic/speaker/screen in the garden model.
- AI sets alarms/config; local device executes (same pattern as Clock Goblin).
