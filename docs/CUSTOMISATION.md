# Customisation

## Behaviour

### Quiet hours

In the automation, the `condition: time` block. The "clear" branch deliberately has
no time condition, so the popup still closes at night.

```yaml
  - condition: time
    after: "07:00:00"
    before: "22:00:00"
```

Delete the block for 24-hour operation.

### How long the popup stays

Two values, and they are independent:

- `timeout: 60000` in the automation (milliseconds)
- nothing else — the progress bar shows flight progress, not a countdown

### How long the display stays active after the last aircraft

`delay_off` on `binary_sensor.flightwall_inbound` in the package file. Two minutes by
default. This is the single most important value for the feel of the thing: too short
and the screen flickers between polls, too long and it stays on after the sky is
empty. Near a busy airport, raise it. In quiet airspace, lower it to 60 seconds.

### Showing every aircraft, including repeats

Remove this condition from the automation:

```yaml
  - condition: template
    value_template: >
      {{ states('sensor.flightwall_flight') != states('input_text.flightwall_shown') }}
```

Expect the same aircraft to reappear as the elevation-angle ranking shifts between
two nearby planes.

### Sorting by distance instead of elevation angle

Not recommended, but if you want it, replace the `namespace` loop in the template
sensor with:

```jinja
{% set f = (state_attr('sensor.flightradar24_flights_in_area','flights') or [])
   | selectattr('distance','defined')
   | sort(attribute='distance') | first | default(none) %}
```

You will get cruising traffic at 38,000 ft rather than the aircraft overhead.

### Minimum altitude

The template filters `altitude > 500` to exclude aircraft on the ground. If you live
inside an airport's radius, taxiing aircraft would otherwise permanently win the
ranking. Raise it if you only care about aircraft at cruise.

## Appearance

All in the `card_mod` block.

### Dot-matrix mask

```css
ha-card::after {
  background-image: radial-gradient(circle at center,
    rgba(0,0,0,0) 0 50%, #000 51% 100%);
  background-size: 4px 4px;
}
```

- `background-size` is the dot pitch. Smaller means finer dots and higher apparent
  resolution, but thin glyph strokes start disappearing. 4–7 px is the useful range.
- The two percentages are the hole size. `50%`/`51%` is a hard edge — keep the gap
  at one percentage point. A wider gap (`44%`/`50%`) produces soft rings that read as
  blur, which is the most common way this effect goes wrong.
- Delete the whole `::after` block for plain text with no mask.

### Stroke weight

Press Start 2P has no bold cut, so the browser would synthesise one and shift the
glyphs. Instead the text is thickened with three offset copies:

```css
text-shadow:
  0.04em 0 0 currentColor,
  0 0.04em 0 currentColor,
  0.04em 0.04em 0 currentColor;
```

Raise `0.04em` for heavier strokes, lower it for finer. This matters more than the
mask settings for legibility at a distance.

### Font sizes

Every size uses `min(Xvw, Yvh)` — the smaller of a percentage of width or height.
This means text can never overflow either edge regardless of screen aspect ratio or
orientation.

| Element | Content | Default |
|---|---|---|
| `h1` | Route | `min(12vw, 18vh)` |
| `h2` | Callsign and airline | `min(4.2vw, 5.8vh)` |
| `h3` | Aircraft type | `min(4vw, 5.6vh)` |
| `p` | Status and telemetry lines | `min(3.3vw, 4.7vh)` |
| `p:last-of-type` | Progress bar | `min(2.8vw, 4vh)` |

The constraint is the longest status line ("DEPARTED DUSSELDORF 19M AGO", 27
characters), not the route. If you scale up and it wraps, shrink the logo column
first.

### Logo size

```css
grid-template-columns: min(34vw, 48vh) minmax(0, auto);
```

and

```css
p:first-of-type img { width: min(32vw, 46vh); }
```

Keep the column slightly wider than the image. The column has a **fixed** width
deliberately: if it were `auto`, a missing logo would collapse it and shift the whole
layout sideways.

### Colours

| Element | Value |
|---|---|
| Route, status lines | `#ffffff` |
| Callsign and airline | `#9fb8e8` |
| Aircraft type | `#7ea6ff` |
| Progress bar | `#35ff7a` |
| Close button | `rgba(255,255,255,.28)` |

The progress bar uses `-webkit-text-fill-color` alongside `color` because HA theme
rules can override plain `color` at equal specificity.

### Monochrome logos

Replace the image filter with:

```css
filter: grayscale(1) brightness(1.9) contrast(1.5);
```

More authentic to a real single-colour LED panel, and it rescues logos that are white
on transparent and would otherwise vanish against black.

### Progress bar characters

```jinja
{{ '█' * prog }}{{ '░' * (32 - prog) }}
```

Both are full-cell block characters in the same colour, which is why they render
identically. The bar deliberately does **not** use `<strong>` or a second colour:
Press Start 2P has no bold cut and no block glyphs, so either would trigger a font
fallback and the two halves would no longer line up. This is also why the bar alone
uses `font-family: monospace` rather than the pixel font.

Change `32` in both places to adjust the length.

## Tablet setup (Fully Kiosk)

1. Install Fully Kiosk Browser plus the Plus licence.
2. Enable **Remote Administration** and set a password.
3. Set the screensaver timeout to something longer than your expected popup duration
   — otherwise the tablet sleeps mid-display.
4. Put the tablet's IP and the password into the `rest_command` in the package file.

If you do not use Fully, delete the `rest_command` from the package and remove this
line from the automation:

```yaml
  - action: rest_command.tablet_stop_screensaver
```

Two systems fighting over the screen is the usual failure mode here. Let one own it.
