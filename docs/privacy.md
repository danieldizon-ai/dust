# Privacy, private sync and access in hard places

Secure, free and private is the reason Dust exists rather than a hosted API. This
document sets out the architecture. It adapts Always Foundation's ADR 0016 (*Private sync
for Always AI*) and the threat analysis in its Always AI paper (CC BY 4.0), with changes.

## 1. Default: everything on the device

* The model, the Dust layer, the Creed data, Scripture and the person's notes run and live
  on the person's device. Dust's server binds to `127.0.0.1` by default, logs no request
  content and makes no network connections of its own.
* No accounts, analytics or crash reporting in anything Dust ships.
* A cloud model is possible only by the person's explicit choice (any OpenAI-compatible
  endpoint), and should be shown as such while in use. The checker still runs locally.

What this does not protect against: a compromised device, an operating system or keyboard
that sends data elsewhere, or someone with physical access to an unlocked device.

## 2. Private sync, Obsidian-style

Obsidian's model is the right inspiration: the person's library is a folder of plain files
they own (a "vault"), readable without the app, and sync is an optional add-on that can be
end-to-end encrypted. Applied to Dust:

1. **The library is files.** Notes, saved answers, highlights and study plans are Markdown
   with front-matter, in a folder. Nothing is locked in a database only Dust can read.
2. **Sync is off until turned on**, and never needs an account for device-to-device use.
3. **End-to-end encryption.** A random library key is created on the first device and never
   leaves the person's devices in plaintext. Every file is encrypted on the device with
   authenticated encryption from a well-reviewed library (for example libsodium's
   XChaCha20-Poly1305). File names and folder structure are encrypted too and sizes padded
   to buckets, so storage learns as little as possible.
4. **Keys move device to device**, by QR code or a short code verified on both screens, not
   through the storage provider. A recovery code is shown once at setup.
5. **Bring your own storage.** The encrypted vault can sit in any folder the person
   already syncs (iCloud Drive, Google Drive, Dropbox, OneDrive, Syncthing), move directly
   over the local network, travel on a USB stick, or use a church's own server. Nobody
   needs to run a Dust sync service, and Rejoice and Always hold no keys.
6. **Conflict-free merging.** Concurrent edits merge with CRDTs (for example Automerge or
   Yjs documents per note), so offline devices reconcile without a server deciding.
7. **An open format.** The encrypted vault layout, the key-exchange protocol, the threat
   model and test vectors should be published so that anyone can implement a compatible
   client or provider.

What storage still sees: that an encrypted vault exists, roughly how big it is and when it
changes. Lose every device and the recovery code and the library is gone; that is the
price of nobody else holding the key, and people must be told before they turn sync on.

## 3. Other architecture ideas

* **Model files as content-addressed downloads.** Publish SHA-256 hashes and signatures for
  every model, adapter and release, so a file obtained from any mirror, torrent or USB stick
  can be verified offline.
* **Reproducible builds** of the app and the guard (the guard is already reproducible from
  `training/` with a fixed seed), so third parties can confirm a binary matches the source.
* **Local-network sharing for groups.** A teacher's laptop serves the model to a classroom
  over local Wi-Fi with no internet (Dust's server is already OpenAI-compatible).
* **Sealed cloud as a middle tier.** Where a device is too weak, confidential-computing
  inference (attested GPU enclaves) is better than an ordinary provider promise, but it is
  still trust in hardware vendors. Show the trust level to the person: on device, sealed
  hardware, or provider promise (ADR 0016's three layers).
* **Federated evaluation, not federated data.** Churches can run `bench/e2e.py` locally and
  share only aggregate scores, never transcripts, to build a scorecard of models across
  languages.

## 4. Adversarial and censored environments

Christians in some countries face surveillance, censorship of religious material or legal
risk for possessing it. Dust cannot make anyone safe, and it must not pretend to. What
architecture can do:

* **Work fully offline.** After a one-time transfer the model, Scripture, Creed and layer
  need no network. Nothing reaches out, so there is nothing to block or observe on the
  network.
* **Be small and portable.** The pocket tier plus the layer and a Bible fits in a few
  gigabytes: an SD card, a USB stick, a phone-to-phone transfer, a local mesh. The layer
  and Creed data alone are under 1 MB.
* **Be verifiable without contact.** Signed hashes let someone who received a copy by hand
  check it was not tampered with.
* **Avoid leaving traces by default.** No accounts, no telemetry, no update checks unless
  enabled, an option to keep no conversation history, and a quick way to lock or remove the
  library. Always's paper names device seizure as the main threat in hostile contexts; the
  right response is principles (minimise what is stored, encrypt what is kept, make removal
  fast) rather than published step-by-step procedures.
* **Do not promise deniability.** Hidden volumes and disguised apps can create false
  confidence and, if discovered, more danger. Local partners who know the situation should
  decide what to recommend.
* **Multilingual from the start**, because the places where access is hardest are often
  where open Bibles and models are weakest (see `docs/uses.md`).

## 5. Data the layer itself handles

The checker sees the model's draft answer and the user's question. It stores neither. The
HTTP server keeps nothing between requests and does not log bodies. Developers who embed
Dust are responsible for their own logging, and should follow the same rule.
