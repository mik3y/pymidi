# Changelog

## Current version (in development)

* Bugfix: Fix crash when sender name contains non-ascii characters (#18).
* Internal: Switched from `pipenv` to `poetry`.
* Internal: Added `black` for code formatting.
* Improvement: Calculates latency to client and outputs as info.
* Improvement: Decodes pitch blend change messages.
* Breaking change: `on_midi_commands` callback handler now passes whole MIDI packet rather than a list of commands - this is useful if the journal (or other data) is required.
* Improvement: RTP sequence numbers now increment
* Improvement: Timestamps don't overflow 32-bit field (issue #34)
* Improvement: disconnt() method for client (issue #28)

## v0.5.0 (2020-01-12)

* Python 2 support removed.

## v0.4.0 (2018-12-26)

* Improvement: Python 3 support (#9).
* Bugfix: Demo server: Fix IPv4/IPv6 support in dualstack environments (#8).

## v0.3.0 (2018-10-20)

* Improvement: Server instances can bind to ipv6 addresses.

## v0.2.1 (2018-09-16)

* Repackaged release, no functional changes.

## v0.2.0 (2018-09-16)

* `note_on` and `note_off` messages now report a string note name.
* Cleaned up some logs.

## v0.1.0 (2018-09-16)

* First release.
