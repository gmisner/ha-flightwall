# HACS default listing

Flight Wall is already installable as a **custom repository**
(`https://github.com/gmisner/ha-flightwall`, type Integration).

To get it into the default HACS store, open a pull request against
[hacs/default](https://github.com/hacs/default) that adds this
repository under `integration`. The HACS docs for that process:

https://www.hacs.xyz/docs/publish/include/

## Checklist before submitting

- [ ] Latest release is tagged (currently **1.10.0** after these PRs merge)
- [ ] `hacs.json` has `"render_readme": true`
- [ ] README install steps work on a clean Home Assistant
- [ ] `manifest.json` `version` matches the git tag
- [ ] Theme preview images in `docs/images/tv-*.png` are current
  (`python scripts/render_previews.py` from a venv with Pillow)
- [ ] No household-specific names in docs or config-flow copy

## What reviewers will look at

HACS default requires a real Home Assistant custom integration (this
repo's `custom_components/flightwall/`), a valid `manifest.json`, and
a documentation URL. They do not need the legacy YAML package.
