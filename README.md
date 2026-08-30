# Flight Wall

A flight display for Home Assistant. When an aircraft passes overhead, a full-screen
panel shows the airline, callsign, route, aircraft type, arrival estimate, live
telemetry, and a flight progress bar — as a dot-matrix LED panel or as a mechanical
split-flap departure board.

Built for a wall-mounted tablet. Inspired by physical LED flight boards, in
particular [The Flightwall](https://theflightwall.com/).

![Dot-matrix style](docs/images/dot-matrix.jpg)

## Two display styles

Switch with `input_select.flightwall_style`. Takes effect on the next popup, no
restart needed. Add the dropdown to any dashboard if you want to flip between them
easily.

**`dot-matrix`** (default) — large LED panel look with the airline logo on the left
and the route as the hero line. Shown above.

**`split-flap`** — a mechanical departure board with printed row labels, in the style
of an airport board. Each cell is a two-leaf flap that physically cycles through the
alphabet until it reaches its letter, so reaching `Z` visibly takes longer than
reaching `B`. Columns start in a left-to-right sweep with slight jitter, so they do
not move in lockstep.

![Split-flap style](docs/images/split-flap.jpg)

Labels are printed on the frame rather than set in flaps, which is how a real board
does it. They are fixed unless you override them with `l1`–`l8` in the URL.

No airline logo, deliberately: a flap board cannot display one. That also sidesteps
the 128 px logo resolution ceiling. Values are hard-truncated at 16 characters.

The board is a standalone HTML page at `www/splitflap.html`, rendered in an iframe.
The automation passes the seven values and the progress figure as URL parameters, so
the page knows nothing about Home Assistant and can be opened directly in a browser
to preview it. This also sidesteps the markdown card's HTML sanitiser, which strips
`class` attributes and scripts and therefore cannot animate individual characters.

## What it does

- Picks the single most visible aircraft in range using **elevation angle**, not
  ground distance. A jet cruising at 11 km altitude that happens to be 9 km away
  horizontally is not the plane you can see out of the window; the one on approach
  at 3000 ft is. Sorting by distance alone gets this wrong constantly.
- Shows each aircraft **once** as it enters the zone, rather than repeating while it
  crosses.
- Optionally wakes a wall-mounted tablet when traffic appears.

## Requirements

### Home Assistant

All four are required.

| Component | Source | Why |
|---|---|---|
| [Flightradar24 integration](https://github.com/AlexandrErohin/home-assistant-flightradar24) | HACS | Flight data |
| [browser-mod](https://github.com/thomasloven/hass-browser_mod) | HACS | Renders the full-screen popup |
| [card-mod](https://github.com/thomasloven/lovelace-card-mod) | HACS | All styling |
| [stack-in-card](https://github.com/custom-cards/stack-in-card) | HACS | Holds the display and the close button in one card, since `browser_mod.popup` accepts only one |

### Optional hardware

- A tablet or old phone for wall mounting.
- [Fully Kiosk Browser](https://www.fully-kiosk.com/) with the **Plus licence**
  (~€12 one-off) if you want Home Assistant to wake the screen. Without Plus the
  remote API is unavailable and screen control is not possible.

### Caveat about the data source

The Flightradar24 integration uses an undocumented endpoint. It is a grey area with
respect to FR24's terms of service, and it will break whenever FR24 changes their
API. Do not build anything load-bearing on it. If you want something durable, run a
local ADS-B receiver (RTL-SDR dongle plus `readsb`/`tar1090`, around €40) and adapt
the template sensor to read from that instead; the rest of this project works
unchanged.

## Installation

### HACS (guest-room TV, recommended)

This is the path if you want the board on a Vizio / Chromecast TV. Do **not**
also copy `packages/flightwall.yaml` — you would get duplicate entities.

1. Install [Flightradar24](https://github.com/AlexandrErohin/home-assistant-flightradar24) via HACS, set coordinates and a **30 km** radius, and rename the flights-in-area sensor to `sensor.flightradar24_flights_in_area` if you want the default name.
2. HACS → three dots → **Custom repositories** →
   `https://github.com/gmisner/ha-flightwall` → type **Integration** → Add.
3. Find **Flight Wall** in HACS and download it. Restart Home Assistant.
4. **Settings → Devices & Services → Add integration → Flight Wall.**
   Pick the FR24 flights sensor, the Vizio `media_player` (power), and the
   Chromecast `media_player` on that TV.
5. Home Assistant must be reachable over **HTTPS** (Nabu Casa or
   `external_url`) for Cast discovery. The board image itself is sent over
   the LAN (`http://…:8123/local/flightwall-board.png`).
6. Leave `switch.flightwall_tv` on. Put it on a dashboard if someone in
   that room will want Netflix instead. While the switch is on, turning
   the TV on with the remote takes over Cast. If they then switch to
   another app, Flight Wall stays out of the way until the set is turned
   off and on again, or you re-arm the switch.
7. **Display**, **Theme**, and **Units** are under
   **Settings → Devices & Services → Flight Wall → Configure**.
   Use **Image** on a 2019 Vizio or old Chromecast. Use **Live** on a
   tablet, Fully Kiosk, or a Chromecast that can load Home Assistant.
   If live Cast fails, the board image is shown instead. Theme includes
   LED, plain, amber, and split-flap.

The integration creates `sensor.flightwall_flight`, the inbound binary
sensor, the TV switch, and a **Flightwall** sidebar dashboard. Turning the
TV on with the remote should show the board after about ten seconds.

Tablet LED / split-flap popup is still the manual package path below
(browser-mod, card-mod, stack-in-card).

### Manual package (tablet popup)

### 1. Set up Flightradar24

Install via HACS, add the integration, and set your coordinates and a radius. **Start
with 30 km.** Anything smaller and aircraft will have crossed your position before
the next poll (the integration polls roughly every 30 seconds, and an airliner covers
about 4 km in that time).

Then go to **Settings → Devices & Services → Entities**, find the "flights in area"
sensor, and rename it to:

```
sensor.flightradar24_flights_in_area
```

This step is not optional. The integration names entities after your Home Assistant
language, so a German install gets `sensor.flightradar24_fluge_im_bereich`, a French
one something else again. Renaming once is simpler than editing eight template
references.

### 2. Install the package

Enable packages in `configuration.yaml` if you have not already:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Copy `packages/flightwall.yaml` into your `<config>/packages/` directory, edit the
`rest_command` block at the bottom with your tablet's IP and Fully password, then
restart Home Assistant.

This creates:

- `sensor.flightwall_flight` — the selected aircraft, with all its data in the
  `flight` attribute
- `binary_sensor.flightwall_inbound` — on while any aircraft is in range
- `input_text.flightwall_shown` — remembers the last shown callsign
- `input_boolean.flightwall_tv` — guest-room TV is a flight board (leave on)
- `input_text.flightwall_tv_power` — Vizio `media_player` used as the on/off signal
- `input_text.flightwall_tv_player` — the Google Cast `media_player` entity
- `rest_command.tablet_stop_screensaver` — wakes the tablet

### 3. Install the split-flap board page

Only needed if you want the `split-flap` style. Copy `www/splitflap.html` to
`<config>/www/flightwall/splitflap.html`, creating the folders if they do not exist,
then restart Home Assistant — the `www` directory is only scanned at startup.

Confirm it is served by opening it directly:

```
http://your-ha:8123/local/flightwall/splitflap.html
```

With no parameters it renders a demo board, which is also the quickest way to tune
the look without waiting for an aircraft.

### 4. Verify the data before going further

Open **Developer Tools → States** and check `sensor.flightwall_flight`. If it says
`none` with an empty `flight` attribute, stop here and fix that first — the display
work downstream is pointless until data arrives. See
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

Also look at the attribute keys in the `flight` attribute. They come straight from
FR24 and may differ from what the templates expect; every field is wrapped in a
fallback, so a missing key degrades gracefully rather than breaking the layout, but
you may see `IN FLIGHT` where you expected a route.

### 5. Add the automation

Go to **Settings → Automations → Create automation**, then the three-dot menu →
**Edit in YAML**, and paste the contents of `automations/flightwall_popup.yaml`.

Do not include a leading `- ` or an `automation:` key — the editor expects a single
automation body, and that is the most common paste error.

The popup appears when new traffic arrives and closes after 60 seconds, on tap, or
when the last aircraft leaves the zone.

### 6. Optional: guest-room TV

For a set that should *be* the flight board whenever someone turns it on
(a guest room, a shop). The remote is the only on/off. Home Assistant
never powers the TV down.

A Vizio cannot run the tablet popup. Copy
`dashboards/flightwall.yaml` and `themes/flightwall.yaml`, add the
includes, paste `automations/flightwall_tv.yaml`, and fill the two TV
helpers — Vizio power and Chromecast — then leave
`input_boolean.flightwall_tv` on. Full walkthrough:
[docs/TV.md](docs/TV.md).

AirPlay on the Vizio is manual mirroring from an Apple device, not
something HA can start.

## Configuration

Everything worth changing is documented in
[docs/CUSTOMISATION.md](docs/CUSTOMISATION.md). The three settings most people want:

| What | Where | Default |
|---|---|---|
| Quiet hours | `condition: time` in the automation | 07:00–22:00 |
| How long the popup stays | `timeout` in the automation | 60000 ms |
| How long after the last aircraft the display stays active | `delay_off` on the binary sensor | 2 minutes |
| Guest-room TV is a flight board | `input_boolean.flightwall_tv` | off until you finish TV setup |
| Which TV reports on/off | `input_text.flightwall_tv_power` | empty |
| Which Cast player to use | `input_text.flightwall_tv_player` | empty |

## Known limitations

- **Airline logos max out at 128 px.** They come from the Kiwi CDN, which has no
  higher resolution. Under a dot-matrix mask, wordmark logos in script fonts stay
  hard to read no matter what. Roundels and simple marks work well.
- **Logos are third-party.** If the Kiwi CDN goes away, logos break. Unknown airline
  codes fall back to a generic aircraft icon from the same CDN.
- **`aircraft_model` is not always populated.** When it is missing the display falls
  back to the ICAO type code (`A320`, `B738`), which is less readable but always
  present.
- **The dot-matrix effect softens text by design.** It cuts holes in every glyph. The
  mask spacing and the faux-bold `text-shadow` are tuned as a compromise; see
  CUSTOMISATION for the two values to adjust.
- **A Vizio cannot run the tablet LED or split-flap pages.** Those need a
  browser. The guest-room path sends a 4K board image over Cast instead
  (LED grid or plain large type). AirPlay is manual mirroring from an
  Apple device, not something HA can start. See [docs/TV.md](docs/TV.md).

## Trademarks and affiliation

This is an independent hobby project. It is not affiliated with, endorsed by,
sponsored by, or connected to The Flightwall, Flightradar24, Kiwi.com, or any
airline.

All product names, logos, and brands are the property of their respective owners.
Airline logos are fetched at display time from a third-party CDN and shown solely to
identify the aircraft currently overhead. If you would rather not display them, set
the image filter to `grayscale(1)` for a monochrome LED look, or point the URL at
your own assets — see [docs/CUSTOMISATION.md](docs/CUSTOMISATION.md).

## Credits

Inspired by [The Flightwall](https://theflightwall.com/). Flight data via the
[Flightradar24 integration](https://github.com/AlexandrErohin/home-assistant-flightradar24)
by AlexandrErohin. Airline logos from the Kiwi.com CDN. Typeface is
[Press Start 2P](https://fonts.google.com/specimen/Press+Start+2P) by CodeMan38.

## Licence

MIT. See [LICENSE](LICENSE).
