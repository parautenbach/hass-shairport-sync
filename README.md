# Shairport Sync media player for Home Assistant

This custom [`media_player`](https://www.home-assistant.io/integrations/media_player/) for [Home Assistant](https://home-assistant.io/)
allows you to control and get updates from a [Shairport Sync](https://github.com/mikebrady/shairport-sync/)
installation using [MQTT](https://mqtt.org/).

You need to compile Shairport Sync with at least the MQTT and metadata options, for example:
```
 ./configure --with-mqtt-client --with-metadata
```

## Installation

### Manual

Copy the `shairport_sync` folder of this repo to `<config_dir>/custom_components/shairport_sync/` of your Home Assistant installation.

Add the following to your `configuration.yaml`'s `media_player` section replacing `<topic>` with what's in your `shairport-sync.conf`:

```yaml
  - platform: shairport_sync
    name: Shairport Sync Player
    remote:
      topic: <topic>/remote
    states:
      playing:
        topic: <topic>/play_start
      paused:
        topic: <topic>/play_end
    metadata:
      artist:
        topic: <topic>/artist
      title:
        topic: <topic>/title
```

### HACS
TODO
