# HACS default listing

Flight Wall is already installable as a **custom repository**
(`https://github.com/gmisner/ha-flightwall`, type Integration).

To get it into the default HACS store, open a pull request against
[hacs/default](https://github.com/hacs/default) that adds this
repository under `integration`. The HACS docs for that process:

https://www.hacs.xyz/docs/publish/include/

## Checklist before submitting

- [x] Latest release is tagged (**1.11.0**)
- [x] `hacs.json` has `"render_readme": true`
- [x] README install steps work on a clean Home Assistant
- [x] `manifest.json` `version` matches the git tag
- [x] Theme preview images in `docs/images/tv-*.png` are current
  (`python scripts/render_previews.py` from a venv with Pillow)
- [x] Brand images in `custom_components/flightwall/brand/` (`icon.png`, `logo.png`)
- [x] GitHub social preview set to `docs/images/social.png`
  (repo Settings → General → Social preview)
- [x] No household-specific names in docs or config-flow copy
- [x] HACS Action and hassfest pass with no `ignore` keys
- [x] Pull request open against [hacs/default](https://github.com/hacs/default/pull/10480)

## What reviewers will look at

HACS default requires a real Home Assistant custom integration (this
repo's `custom_components/flightwall/`), a valid `manifest.json`, and
a documentation URL. They do not need the legacy YAML package.
