# Television

For a set that should *be* the flight board when it is on — a shop, a
workshop, a living-room wall. Turn the TV on with the remote. The board
comes up and stays up. Turn the TV off when you are done. Home Assistant
never powers the set down.

The tablet popup is separate. This page is only Cast / TV.

Many smart TVs are not a browser. Their built-in Chromecast often cannot
load a live Home Assistant dashboard. Flight Wall switches the set to
Cast and sends a 4K board image: airline (or a generic aircraft mark),
callsign, route, cities, type, registration, heading, times, altitude,
speed, progress, and the next aircraft when a second one is in range.
Empty sky shows a clock and the last flight overhead.

AirPlay is manual screen mirroring from an iPhone, iPad, or Mac. Home
Assistant cannot start AirPlay.

## HACS

If you installed Flight Wall from HACS, skip the file copies and the TV
automation paste. Add the integration, pick the two TV entities, leave
`switch.flightwall_tv` on. The integration writes
`/local/flightwall-board.png` and plays that image on the Chromecast
when the TV comes on. It refreshes about once a minute while Cast is
showing the board, and immediately when the selected aircraft changes.
If someone switches the set to another app — Netflix, HDMI, the TV's
home screen — Flight Wall does not take over again until the TV is
turned off and on, you re-arm the switch, or you call the
`flightwall.recast` service. Keepalive only refreshes while Cast is
already showing the board, or while the set has not reported a source
yet. That is brand-agnostic: there is no SmartCast-only special case.

**Display**, **Theme**, and **Units** are under **Settings → Devices &
Services → Flight Wall → Configure**.

- **Image** — 4K PNG over Cast. Use this when the Chromecast cannot load
  Home Assistant (typical of older built-in Cast receivers). The LED
  grid exists only in this mode.
- **Live** — `cast.show_lovelace_view` of the Flightwall dashboard. Use
  this on a browser, tablet, or Chromecast with Google TV. If the live
  session does not connect, Flight Wall falls back to the image.
- **Theme** — LED night, plain large type, amber departures, or
  split-flap. Split-flap on the TV is a still board; the tablet HTML
  page is what animates the flaps.

Do not also install `packages/flightwall.yaml`.

You need **two** `media_player` entities. They are easy to mix up.

| Role | What to pick | Typical integration |
|---|---|---|
| TV power | The television itself (`on` / `off`) | Vizio, webOS, Android TV, … |
| Cast player | The Chromecast **on that set** | Google Cast |

## Manual setup (without HACS)

1. TV and Home Assistant on the same subnet.
2. Home Assistant reachable over **HTTPS** (Nabu Casa, or `external_url`
   in `configuration.yaml`).
3. Add the TV integration and note its `media_player.*`. That goes in
   `flightwall_tv_power`.
4. Add **Google Cast** if it is not already discovered. The Chromecast
   on that television is a second `media_player.*`. That goes in
   `flightwall_tv_player`.
5. Copy `dashboards/flightwall.yaml` to `<config>/dashboards/flightwall.yaml`
   and `themes/flightwall.yaml` to `<config>/themes/flightwall.yaml`.
6. Add the includes below, then restart.
7. Open **Flightwall** in the sidebar. You should see the board (or
   `WAITING FOR TRAFFIC`).
8. Paste `automations/flightwall_tv.yaml` as a new automation (no
   leading `- `, no `automation:` key).
9. Set the two helpers, then turn **`input_boolean.flightwall_tv` on and
   leave it on**.

Off means that room is watching something else. On means turning the TV
on is the flight board.

### Dashboard and theme includes

The dashboard key **must contain a hyphen**. `flightwall` is rejected;
`flight-wall` is what the automation casts.

```yaml
lovelace:
  dashboards:
    flight-wall:
      mode: yaml
      filename: dashboards/flightwall.yaml
      title: Flightwall
      icon: mdi:airplane
      show_in_sidebar: true

frontend:
  themes: !include_dir_merge_named themes
```

If you already have `frontend.themes:` or `lovelace.dashboards:`, add
these entries next to what is there. Do not set `resource_mode: yaml`
unless you already load resources from YAML — that would drop HACS cards
from your other dashboards.

### Test the board image by hand

```
http://YOUR_HA:8123/local/flightwall-board.png
```

```yaml
action: media_player.select_source
data:
  entity_id: media_player.YOUR_TV
  source: Cast
```

```yaml
action: media_player.play_media
data:
  entity_id: media_player.YOUR_CAST_PLAYER
  media_content_id: http://YOUR_HA:8123/local/flightwall-board.png
  media_content_type: image/png
```

Then: switch on, TV off, TV on with the remote. After about ten seconds
the board should appear. While Cast is showing it, the image refreshes
about once a minute. Nothing in this project turns the TV off.

Do **not** rely on `cast.show_lovelace_view` on an older built-in
Chromecast. Use Display → Image.

## AirPlay (preview only)

1. Open **Flightwall** in the sidebar on an iPhone, iPad, or Mac.
2. Control Center → Screen Mirroring → the television.
3. Stop mirroring from the same device when you are done.

## Tablet

Install Flight Wall from HACS, then open `/flight-wall/board` in a
browser or Fully Kiosk. The integration copies
`/local/flightwall/splitflap.html` for the animated flap board. No
YAML package.

## Optional: HDMI stick

A Chromecast with Google TV or an Onn box on HDMI *is* a browser. The
tablet LED / animated split-flap popup can run there. Leave
`switch.flightwall_tv` / `input_boolean.flightwall_tv` off if you go
that way, or you will Cast and popup on the same screen.

## Troubleshooting

**TV comes on, board never does.** HTTPS first. Then confirm the Cast
entity is the player and the television entity is power. The
integration waits ten seconds after power-on for Chromecast to wake.

**Cast starts while the TV is off.** The power entity is empty or
pointing at the Cast player. Periodic refresh will then keep waking the
set. The television itself must be the power helper.

**Someone wants to watch something else.** They can switch source with
the remote. Flight Wall will not steal the set back. Turning the TV off
and on, flipping the Flight Wall switch off and on, or calling
**Developer Tools → Actions → `flightwall.recast`**, makes it a flight
board again.

**Need to see why Cast failed.** Settings → Devices & Services →
Flight Wall → ⋮ → Download diagnostics. That dump includes the power
entity, Cast source, player app, and the last cast error. It does not
include tokens.

**Board looks soft on a large set.** Use **Configure → Theme → Plain
large type**. The image is 4K either way.
