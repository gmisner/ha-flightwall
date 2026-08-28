# Troubleshooting

Work top to bottom. Each step assumes the ones above it pass.

## No flights at all

**Check `sensor.flightradar24_flights_in_area` in Developer Tools → States.**

State is `0` or `unknown` with an empty `flights` attribute:

- **Radius units.** The most common cause. Depending on the integration version the
  radius field may be metres, not kilometres. If you entered `30` and it wants
  metres, you are searching a 30-metre circle. Try `50000` and see whether flights
  appear.
- **Coordinates.** If the latitude and longitude fields were left blank during setup,
  the integration may be looking at 0,0 in the Atlantic.
- **Rate limiting or blocking.** Check **Settings → System → Logs**, filter for
  `flightradar24`. A 403 means FR24 is refusing the requests. Nothing to configure;
  this is the fragility the README warns about.

After changing anything, reload the integration (three-dot menu → Reload) and wait
one or two poll cycles.

## Flights exist but `sensor.flightwall_flight` is `none`

The entity name does not match. The package expects
`sensor.flightradar24_flights_in_area`. Rename it in **Settings → Devices &
Services → Entities** rather than editing the templates.

If the name is right, check the attribute keys inside `flights`. The template needs
`altitude` and `distance` on each entry. If they are named differently in your
version, adjust the template sensor.

## `sensor.flightwall_flight` works but no popup appears

Check in order:

1. **Time window.** Is it outside 07:00–22:00?
2. **The dedup helper.** Look at `input_text.flightwall_shown`. If it equals the
   current callsign, the automation is correctly suppressing a repeat. Set it to `-`
   manually to force the next popup.
3. **browser-mod registration.** Open Home Assistant on the target device, go to
   Settings → Browser Mod, confirm the browser is registered.
4. **Test browser-mod directly.** Developer Tools → Actions, YAML mode:

   ```yaml
   action: browser_mod.popup
   data:
     title: Test
     dismissable: true
     size: fullscreen
     timeout: 15000
     content:
       type: markdown
       content: "# TEST"
   ```

   If this does not appear, the problem is browser-mod, not this project. Note that
   adding unsupported keys to `data` will cause the whole call to fail silently —
   this is worth knowing if you have been editing the automation.

## Popup appears but the text is tiny

card-mod is not applying. Hard-reload the browser (Ctrl+Shift+R) or fully restart
the tablet app; card-mod CSS caches aggressively.

If it persists: the HA markdown card sanitises HTML, and `class` attributes on
injected `div`s do not survive. This is why the layout is built entirely from
markdown headings styled by tag selector rather than by class. If you have been
editing the content and added your own HTML, that is the cause.

## Everything is blurry

Check the mask settings first — a soft gradient (`44%`/`50%`) produces rings rather
than holes, and reads as blur. Use `50%`/`51%`.

If text is blurry beyond the mask, something in the ancestor chain is rasterising the
subtree. Run this in the browser console while the popup is open:

```js
(() => {
  const walk = (root, path = '') => {
    const res = [];
    for (const el of root.querySelectorAll('*')) {
      const cs = getComputedStyle(el);
      const bad = ['filter','backdropFilter','transform','zoom','opacity','willChange']
        .filter(p => cs[p] && !['none','normal','1','auto'].includes(cs[p]));
      if (bad.length) res.push([path + el.tagName.toLowerCase(), ...bad.map(p => p + '=' + cs[p])]);
      if (el.shadowRoot) res.push(...walk(el.shadowRoot, path + el.tagName.toLowerCase() + ' >> '));
    }
    return res;
  };
  console.table(walk(document));
})();
```

Look for `filter: blur()`, `backdrop-filter: blur()`, or a `transform: matrix()` on
any `browser-mod-*` or dialog element. Any of these rasterises everything inside it.
The dashboard variant avoids this entirely because there is no dialog in the chain —
if you cannot resolve it, switch variants.

## Layout breaks when a logo is missing

Should not happen: the image tag is unconditional (only the URL changes) and the grid
column has a fixed width. If you made the image conditional, the first `<p>` becomes
a text line and the `p:first-of-type` rule drags it into the logo column. Keep the
image unconditional.

## Route shows `NONE-NONE`

Fixed in the current templates. FR24 returns the string `"None"` for positioning
flights and aircraft without a filed flight plan, so Jinja's `default()` does not
trigger — the key exists, it just contains junk. The `clean()` macro catches this and
falls back to the registration, then to `IN FLIGHT`.

## Progress bar renders unevenly

Both halves must use the same colour, the same weight, and a font that actually has
block glyphs. Press Start 2P has none, so the bar uses `font-family: monospace`.
Colouring one half differently or wrapping it in `<strong>` reintroduces the problem.

## Screen does not wake

`rest_command` is fire-and-forget with no status feedback, so a lost request is
silent. Check:

1. Fully Plus licence is active — the remote API does not exist without it.
2. Remote administration is enabled and the password matches.
3. Test the URL directly in a browser:
   `http://TABLET_IP:2323/?cmd=stopScreensaver&password=YOURPASSWORD&type=json`

If reliability matters, add a periodic sync automation that re-issues the command
every two minutes while `binary_sensor.flightwall_inbound` is on. The command is
idempotent, so this costs nothing.
