# NautilusTrader source

Alladin pins NautilusTrader 1.231.0 at the commit in
`nautilus_trader.lock.json`. Its LGPL-3.0 license is preserved in
`LICENSE.NautilusTrader`. The runtime extra installs the matching compiled release.

Materialize the complete upstream source locally:

```bash
python scripts/vendor_nautilus.py
```

The script clones the pinned tag, verifies its exact commit, records per-file
integrity hashes, removes the clone's `.git` and places the full source under
`vendor/nautilus_trader`. It refuses to overwrite an existing source directory.
It never runs upstream build/setup code. The source and its generated manifest
are ignored by Alladin's Git to avoid duplicating large upstream fixtures in
every checkout. The lock and materializer are the committed reproducible source
reference; the full upstream tree is not stored as thousands of Alladin blobs.
