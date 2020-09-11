[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

# Shairport Sync media player for Home Assistant

This custom [`media_player`](https://www.home-assistant.io/integrations/media_player/) 
for [Home Assistant](https://home-assistant.io/) allows you to control and get 
updates from a [Shairport Sync](https://github.com/mikebrady/shairport-sync/)
installation using [MQTT](https://mqtt.org/).

You need to compile Shairport Sync with at least the MQTT and metadata options, 
for example:

```
 ./configure --with-mqtt-client --with-metadata
```

## Installation

### Manual

Copy the `shairport_sync` folder of this repo to 
`<config_dir>/custom_components/shairport_sync/` of your Home Assistant 
installation. Create the `custom_components` directory if it doesn't exist.

Add the following to your `configuration.yaml`'s `media_player` section 
replacing `<topic>` with what's in your `shairport-sync.conf` and restart
Home Assistant:

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
      artwork:
        topic: <topic>/cover
```

Some important settings required in your `shairport-sync.conf`:

```
mqtt = 
{
    enabled = "yes";
    hostname = "<host_of_your_mqtt_broker>";
    port = 1833; // MQTT broker port; this is the default
    topic = "your/mqtt/topic";
    published_parsed = "yes"; // For metadata
    publish_cover = "yes"; // Album art
    enable_remote = "yes"; // Remote control
}
```

### HACS
[TODO](https://hacs.xyz/)

### Troubleshooting

Enable logging and log an issue if necessary. 

```yaml
logger:
  default: info
  logs:
    custom_components.shairport_sync: debug
```

Shairport Sync's MQTT code is chatty so you will see duplicate log entries.
