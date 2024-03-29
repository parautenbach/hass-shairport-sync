## v0.1.0
### New
- Initial release.

## v1.0.3
### New
- HACS support (also thanks to [qcasey](https://github.com/qcasey)).

## v1.1.0
### Compatibility
- Support for Home Assistant 2021.12, where the MQTT publish function is now a coroutine.

## v1.1.1
### Deprecations
- Replace deprecated HA device class for media player speakers. 

## v1.2.0
### New
- Support for album name (thanks [ahayworth](https://github.com/ahayworth)).
- Using config flow (UI) (thanks [mill1000](https://github.com/mill1000)).
- Inclusion in HACS.
### Fixes
- Fixing an issue with the MQTT subscription to better handle stopped/paused streams.
### Improvements
- Some technical changes regarding code structure.

## v1.3.0
### Fixes
- Set the idle state when the stream ends and clear the metadata (thanks [mill1000](https://github.com/mill1000)).

## v1.3.1
### New
- Portugese translation for config flow (thanks [ViPeR5000](https://github.com/ViPeR5000)).
