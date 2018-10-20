# pymidi

A python RTP-MIDI / AppleMIDI implementation. You can use this library to build a network attached virtual MIDI device.

[![Build Status](https://travis-ci.org/mik3y/pymidi.svg?branch=master)](https://travis-ci.org/mik3y/pymidi)

**Latest release:** v0.3.0 (2018-10-20) ([changelog](https://github.com/mik3y/pymidi/blob/master/CHANGELOG.md))

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [Quickstart](#quickstart)
- [Developer Setup](#developer-setup)
  - [Running tests](#running-tests)
  - [Developing against something else](#developing-against-something-else)
- [Demo Server](#demo-server)
- [Using in Another Project](#using-in-another-project)
- [Project Status](#project-status)
- [References and Reading](#references-and-reading)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Quickstart

```
$ pip install pymidi
```
or

```
pipenv install pymidi
```

See [Using in Another Project](#using-in-another-project) and the [Developer Setup wiki](wiki/Developer-MIDI-Setup) for more information.

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

## Demo Server

The library includes a simple demo server which prints stuff.

```
$ python pymidi/server.py
```

See `--help` for usage.

## Using in Another Project

Most likely you will want to embed a server in another project, and respond to MIDI commands in some application specific way. The demo serve is an example of what you need to do.

First, create a subclass of `server.Handler` to implement your policy:

```py
from pymidi import server

class MyHandler(server.handler)
    def on_peer_connected(self, peer):
        print('Peer connected: {}'.format(peer))

    def on_peer_disconnected(self, peer):
        print('Peer disconnected: {}'.format(peer))

    def on_midi_commands(self, command_list):
        for command in command_list:
            if command.command == 'note_on':
                key = command.params.key
                velocity = command.params.velocity
                print('Someone hit the key {} with velocity {}'.format(key, velocity))
```

Then install it in a server and start serving:

```
server = new Server()
server.add_handler(MyHandler())
server.serve_forever()
```

See the [Developer Setup wiki](wiki/Developer-MIDI-Setup) for ways to test with real devices.

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
