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
Add the repository URL as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories).

### Compatibility
This platform has been tested against Shairport Sync 3.3.7rc1 and Home Assistant Core
0.114.1.

Tested Shairport Sync details:
```
3.3.7rc1-alac-OpenSSL-Avahi-ALSA-pipe-soxr-metadata-mqtt-sysconfdir:/etc.
```

## Troubleshooting

Enable logging and log an issue if necessary.

```yaml
logger:
  default: info
  logs:
    custom_components.shairport_sync: debug
```

Shairport Sync's MQTT code is chatty so you will see duplicate log entries.

## Advanced Usage

If you have a device such as a Raspberry Pi that runs Shairport Sync which is connected to an
audio system that can be switched on and off with a smart plug and you would like to have a power
button on your media player card in Lovelace (Home Assistant) you can create a
[universal player](https://www.home-assistant.io/integrations/universal/). Here is an example
based on the example player config above.

```yaml
  - platform: universal
    name: Universal Shairport Sync Player
    children:
      - media_player.shairport_sync_player
    commands:
      turn_on:
        service: switch.turn_on
        target:
          entity_id: switch.your_smart_plug
      turn_off:
        service: switch.turn_off
        target:
          entity_id: switch.your_smart_plug
    attributes:
      state: switch.your_smart_plug
```

Here is one way to use this with the custom [Mini Media Player](https://github.com/kalkih/mini-media-player) card.

```yaml
  - type: custom:mini-media-player
    name: Shairport Sync Player
    entity: media_player.universal_shairport_sync_player
    artwork: cover
    volume_stateless: true
    toggle_power: false  # make it use turn_on/turn_off instead of the toggle service
    hide:
      power: false
      power_state: false
      volume: false
      mute: true
    idle_view:
      when_idle: false
      when_paused: false
      when_standby: false
```

PS: Note the use of `toggle_power` above. Using the `toggle` service of the universal media player
won't work as expected in this case (it won't do anything). Tell MMP to use the explicit `turn_on` and `turn_off`
services instead. You can find more information [here](https://community.home-assistant.io/t/lovelace-mini-media-player/68459/2242).