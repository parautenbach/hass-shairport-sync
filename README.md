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

You need the Home Assistant 
[MQTT integration](https://www.home-assistant.io/integrations/mqtt/) set up.

Copy the `shairport_sync` folder of this repo to 
`<config_dir>/custom_components/shairport_sync/` of your Home Assistant 
installation. Create the `custom_components` directory if it doesn't exist.

Add the following to your `configuration.yaml`'s `media_player` section 
replacing `your/mqtt/topic` with what's in your `shairport-sync.conf` and restart
Home Assistant:

```yaml
  - platform: shairport_sync
    name: Shairport Sync Player
    topic: your/mqtt/topic
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

### Compatibility
This platform has been tested against Shairport Sync 3.3.7rc1 and Home Assistant Core
0.114.1.

My Shairport Sync details:
```
3.3.7rc1-alac-OpenSSL-Avahi-ALSA-pipe-soxr-metadata-mqtt-sysconfdir:/etc.
```

### Troubleshooting

Enable logging and log an issue if necessary. 

```yaml
logger:
  default: info
  logs:
    custom_components.shairport_sync: debug
```

Shairport Sync's MQTT code is chatty so you will see duplicate log entries.
