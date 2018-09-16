# pymidi

A python RTP-MIDI / AppleMIDI implementation.

## Developer Setup

Set up your workspace with the very excellent [Pipenv](https://pipenv.readthedocs.io/en/latest/):

```
$ pipenv install
```

Once installed, you'll probably find it useful to work in a `pipenv shell`, for ease of testing and running things:

```
$ pipenv shell
(pymidi-tFFCbXNj)
$ python pymidi/server.py
```

### Running tests

Tests are run with nose; either of the following will work:

```
$ python setup.py test
$ nosetests
```

### Developing against something else

If you're working on a project that uses `pymidi` and want to develop both concurrently, leverage the setuptools `develop` command:

```
$ cd ~/git/otherproject
$ pipenv shell
$ pushd ~/git/pymidi && python setup.py develop && popd
```

This creates a link to `~/git/pymidi` within the environment of `~/git/otherproject`.

## Project Status

What works:
* Exchange packet parsing
* Timestamp sync packet parsing
* Exchange & timestamp sync protocol support
* MIDI message parsing

Not (yet) implemented:
* Journal contents parsing
* Verification of peers on the data channel
* Auto-disconnect peers that stop synchronizing clocks

## References and Reading

* Official docs
  - [RFC 6295: RTP Payload Format for MIDI](https://tools.ietf.org/html/rfc6295)
  - [AppleMIDI Reference Documentation from Apple](https://developer.apple.com/library/archive/documentation/Audio/Conceptual/MIDINetworkDriverProtocol/MIDI/MIDI.html)
  - [RTP-MIDI on Wikipedia](https://en.wikipedia.org/wiki/RTP-MIDI)
* Other helpful docs/sites
  - [The MIDI Specification](http://midi.teragonaudio.com/tech/midispec.htm)
