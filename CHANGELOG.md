# Changelog

## 1.10.0

- Add pytest coverage for flight ranking and board text, plus a GitHub Actions check

## 1.9.2

- Public install guide and docs: television vs tablet paths, current
  Display / Theme / Units options, no household-specific wording
- Config flow copy matches the same language

## 1.9.1

- Scale the split-flap board to fill a 16:9 TV instead of sitting in a
  small island in the middle of the screen

## 1.9.0

- Configure **Theme → Split-flap**: mechanical departure-board look on the
  TV image (labels plus 16-character flaps). No airline logo, same as a
  real flap board. The tablet HTML page still animates; the TV shows the
  settled board.

## 1.8.3

- Always show a logo tile: airline mark when we have one, otherwise a
  generic aircraft so every flight uses the same layout

## 1.8.2

- Hide the logo tile when there is no airline mark, and leave a wider gap
  when there is one, so registration text no longer sits on the box

## 1.8.1

- Keep the route and flight text out of the airline logo column

## 1.8.0

- Configure **Display**: Image (Cast-safe) or Live dashboard (HA Cast / browser)
- Live Cast that does not connect falls back to the board image so the TV is
  not left blank
- Configure **Theme**: LED night, plain large type, or amber departures
- PNG and live Lovelace boards share the same text (cities, heading, next,
  empty-sky clock)

## 1.7.0

- TV board refreshes about once a minute (altitude, speed, clock) while Cast
  is showing the board, and immediately when the selected aircraft changes
- Keepalive no longer steals the set if someone switched to Netflix or
  another source; takeover only happens when the TV is turned on or the
  Flight Wall switch is armed
- Empty sky shows a clock and the last aircraft overhead
- Route line adds city names, registration, heading, and a NEXT flight when
  a second aircraft is in range
- Configure **Board style**: LED grid (default) or plain large type
- Airline logos are cached and scaled once from the 128 px source

## 1.6.2

- TV board is 4K (3840×2160) with a finer LED grid
- Configure **Units**: Imperial (ft, kt, mi) or Metric (m, km/h, km)

## 1.5.1

- Register the Flightwall dashboard on the sidebar using the current
  Lovelace storage API (1.5.0 created the files but never the panel)

## 1.5.0

- Guest-room TV path: when the set is turned on, Cast a core-card
  dashboard and leave it up. HA never powers the TV off. AirPlay remains
  manual mirroring only; HA cannot start it
- Installable via HACS as a custom integration (add
  `https://github.com/gmisner/ha-flightwall` as an Integration repository)

## 1.4.0

- Screenshots of both styles in the README

## 1.3.1

- Close button no longer shows a grey rounded box. The button card paints its own
  card background and a ripple layer, neither of which the earlier transparent
  background rule reached

## 1.3.0

- Split-flap row order is now FLIGHT, AIRCRAFT, AIRLINE, TO, ESTIMATED, ALTITUDE,
  AIRSPEED, PROGRESS
- Aircraft type replaces distance. The readable
  model is used when it fits in 16 characters, otherwise the ICAO code, so it never
  truncates mid-word
- AIRLINE no longer falls back to the aircraft type, since that has its own row
- The screen wake now fires after the popup is sent rather than before, so the page
  is already loading when the display comes on and the flap animation is not missed

## 1.2.0

- Split-flap board gains printed row labels: FLIGHT, AIRLINE, TO, ESTIMATED,
  ALTITUDE, AIRSPEED, AIRCRAFT, PROGRESS
- One value per row instead of packed lines, so the board is 16 characters wide
  rather than 22
- ESTIMATED shows the arrival clock time alongside the countdown
- Flap speed halved (`ms` default 38 to 76) and the column sweep slowed to match

## 1.1.0

- Split-flap display style, selectable via `input_select.flightwall_style`
- Standalone `www/splitflap.html` board with per-character mechanical flip animation,
  alphabet cycling, and a staggered column sweep
- Fixed: aircraft with no filed flight plan showed a fully complete progress bar in
  both styles, because the elapsed/total division clamps its denominator to 1

## 1.0.0

Initial release.

- Elevation-angle aircraft selection
- Dot-matrix full-screen display with airline logo, route, type, status and telemetry
- Flight progress bar
- One popup per aircraft per zone entry
- Full-screen popup via browser-mod, with a close button
- Optional Fully Kiosk screen wake
