# Guest-room TV

Meant for a set that is a flight board when it is on — a guest room, a
shop, a wall TV for someone who likes airplanes. Turn the TV on with the
remote. The board comes up and stays up. Turn the TV off when you are
done. Home Assistant never powers the set down.

The tablet popup is separate. This page is only the TV.

A Vizio cannot run the LED or split-flap styles. SmartCast is not a
browser, and many built-in Chromecasts cannot load the live Home
Assistant dashboard. Flight Wall switches the set to the Cast app and
sends a full-screen board image instead: airline, callsign, route, type,
times, altitude, speed, progress. Empty sky shows `WAITING FOR TRAFFIC`
until the next one.

AirPlay on the Vizio is manual screen mirroring from an iPhone, iPad, or
Mac. Home Assistant cannot start AirPlay. Use it to preview. Day to day
is Cast.

## HACS

If you installed Flight Wall from HACS, skip the file copies and the TV
automation paste. Add the integration, pick the two TV entities, leave
`switch.flightwall_tv` on. The integration creates the dashboard and
casts it when the TV comes on.

Do not also install `packages/flightwall.yaml`.

## Manual setup (without HACS)

You need **two** `media_player` entities. They are easy to mix up.

| Helper | What to put in it | Integration |
|---|---|---|
| `input_text.flightwall_tv_power` | The Vizio itself (`on` / `off`) | [Vizio](https://www.home-assistant.io/integrations/vizio) |
| `input_text.flightwall_tv_player` | The built-in Chromecast | Google Cast |

1. TV and Home Assistant on the same subnet.
2. Home Assistant reachable over **HTTPS** (Nabu Casa, or `external_url`
   in `configuration.yaml`). Cast does nothing over plain HTTP.
3. Add the **Vizio** integration, pairing code on the TV. Note the
   `media_player.*` entity. That goes in `flightwall_tv_power`.
4. Add **Google Cast** if it is not already discovered. The Chromecast
   *on that Vizio* is a second `media_player.*`. That goes in
   `flightwall_tv_player`.
5. Copy `dashboards/flightwall.yaml` to `<config>/dashboards/flightwall.yaml`
   and `themes/flightwall.yaml` to `<config>/themes/flightwall.yaml`.
6. Add the includes below, then restart.
7. Open **Flightwall** in the sidebar on a phone. You should see the
   board (or `WAITING FOR TRAFFIC`).
8. Paste `automations/flightwall_tv.yaml` as a new automation (same
   paste rules as the popup: no leading `- `, no `automation:` key).
9. Set the two helpers, then turn **`input_boolean.flightwall_tv` on and
   leave it on**.

Put that boolean on any dashboard. Off means “this room is watching
something else.” On means “turning the TV on is the flight board.”

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

### Test Cast by hand

```yaml
action: cast.show_lovelace_view
data:
  entity_id: media_player.YOUR_CAST_PLAYER
  dashboard_path: flight-wall
  view_path: board
```

Then: boolean on, TV off, TV on with the remote. After about ten seconds
the board should appear. It re-casts every three minutes and when the
selected aircraft changes, so the Vizio idle screen does not win.
Nothing in this project turns the TV off.

## AirPlay (preview only)

1. Open **Flightwall** in the sidebar on an iPhone, iPad, or Mac.
2. Control Center → Screen Mirroring → the Vizio.
3. Stop mirroring from the same device when you are done.

That is also the only way to put the LED / split-flap popup on this TV
without adding an HDMI stick.

## Optional: HDMI stick for the pretty styles

A Chromecast with Google TV or an Onn box on HDMI *is* a browser. The
existing tablet popup (LED mask, flaps) can run there. Leave
`input_boolean.flightwall_tv` off if you go that way, or you will Cast
and popup on the same screen.

## Troubleshooting

**TV comes on, board never does.** HTTPS first. Then confirm
`flightwall_tv_player` is the Cast entity and `flightwall_tv_power` is
the Vizio. The automation waits ten seconds after power-on for
Chromecast to wake.

**Cast starts while the TV is off.** `flightwall_tv_power` is empty or
pointing at the Cast entity. Periodic re-cast will then keep waking the
set. The Vizio entity must be the power helper.

**“Configuration error” on the TV.** A custom card landed on the view.
`dashboards/flightwall.yaml` must stay core markdown only.

**Someone wants to watch a movie in that room.** Turn
`input_boolean.flightwall_tv` off before they use the remote. Turn it
back on when the room is a flight board again.
