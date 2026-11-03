# Shairport Sync media player for Home Assistant

This custom [`media_player`](https://www.home-assistant.io/integrations/media_player/)
for [Home Assistant](https://home-assistant.io/) allows you to control and get
updates from a [Shairport Sync](https://github.com/mikebrady/shairport-sync/)
installation using [MQTT](https://mqtt.org/).

You need to compile Shairport Sync with at least the MQTT and metadata options.

Example:

```
 ./configure --with-mqtt-client --with-metadata
```

## Installation

### Pre-requisites

You need Home Assistant Core 2026.9.0 or newer (see [Compatibility](#compatibility) for older
versions), with the [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) set up.

### HACS

This is the recommended way to install this integration.

It is available from the main HACS index.

### Manual

Copy the `custom_components/shairport_sync` folder of this repo to
`<config_dir>/custom_components/shairport_sync/` of your Home Assistant
installation. Create the `custom_components` directory if it doesn't exist.

## Configuration

### GUI
Click the `Add Integration` button and search for "Shairport". Enter a friendly name, and the MQTT topic when prompted.

### YAML
Add the following to your `configuration.yaml`'s `media_player` section
replacing `your/mqtt/topic` with what's in your `shairport-sync.conf` and restart
Home Assistant:

```yaml
  - platform: shairport_sync
    name: Shairport Sync Player
    topic: your/mqtt/topic
```

### Shairport Sync
Some important settings that are required in your `shairport-sync.conf`:

```
mqtt =
{
    enabled = "yes";
    hostname = "<host_of_your_mqtt_broker>";
    port = 1883; // MQTT broker port; this is the default
    topic = "your/mqtt/topic";
    publish_parsed = "yes"; // For metadata
    publish_cover = "yes"; // Album art
    enable_remote = "yes"; // Remote control
}
```

## Compatibility

Version 1.5 requires Home Assistant Core 2026.9.0 or newer.

The current version of this integration has been tested against Shairport Sync 5.6.2 and Home Assistant Core 2026.10.4.

### Version 1.4

This version has been tested against Shairport Sync 3.3.7rc1 and Home Assistant Core 2024.10.0.

### Version 1.3.1

This version has been tested against Shairport Sync 4.1 and Home Assistant Core 2023.1.7 and 2023.3.0.

### Version 1.1.1

This version has been tested against Shairport Sync 3.3.7rc1 and Home Assistant Core
2021.12.5.

### Version 1.0.3 

This version has been tested against Home Assistant 0.114.1 and supported up to version 2021.11.5.

Tested Shairport Sync details:
```
3.3.7rc1-alac-OpenSSL-Avahi-ALSA-pipe-soxr-metadata-mqtt-sysconfdir:/etc.
```

## Controlling Shairport Sync Through Home Assistant

Remote control of AirPlay 2 devices requires Shairport Sync 5.6 or newer.

Shairport Sync 5.6 has a [bug](https://github.com/mikebrady/shairport-sync/issues/2314) that prevents track metadata (title, artist, album and cover art) from being sent through MQTT. If a newer release that fixes this bug is available, it is recommended to upgrade.

If you need to stay on Shairport Sync 5.6, you can work around the bug by adding the following setting to the `diagnostics` section of your `shairport-sync.conf`:

```
	get_plist_metadata = "no"; // set this temporary setting to "no" to get the older classic metadata information even in AirPlay 2 mode. For backwards compatibility. Deprecated.
```

Note that this setting is deprecated and may be removed in a future release.

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

## Development

### Setup

Create a virtual environment with the Python version that the targeted Home Assistant release
requires (3.14 at the time of writing) and install the test requirements:

```shell
uv venv -p 3.14 venv
source venv/bin/activate
uv pip install -r requirements_test.txt
```

This installs [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component),
which pins a specific Home Assistant release. To test against a newer Home Assistant, bump its
version in `requirements_test.txt` (the comment there explains how to find the right one).

### Unit tests

```shell
pytest --cov=custom_components.shairport_sync --cov-report=term-missing
```

The tests run against a mocked MQTT broker and need neither a broker nor Shairport Sync.
They also run on GitHub Actions for every push.

### Linting

```shell
black custom_components tests && isort custom_components tests && pylint --rcfile pylintrc custom_components/shairport_sync && mypy
```

mypy runs in strict mode on the integration (see `setup.cfg`).

### hassfest

[hassfest](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) validates the manifest,
translations and config flow. It runs on GitHub Actions for every push. To run it locally, start
Docker and use the same image as the action:

```shell
docker run --rm -v "$PWD":/github/workspace ghcr.io/home-assistant/hassfest
```

Or, with a working Home Assistant Core development environment (see below), from the root of
the core checkout:

```shell
python -m script.hassfest --integration-path /path/to/hass-shairport-sync/custom_components/shairport_sync
```

### Running Home Assistant locally

The venv above already contains Home Assistant, so you don't need a Home Assistant Core checkout.
The `config` directory is a minimal configuration with `config/custom_components/shairport_sync`
symlinked to the integration, so edits are picked up on restart:

```shell
hass -c config
```

Open http://localhost:8123, complete onboarding, add the MQTT integration pointing at a real
broker, and then add Shairport Sync. Everything that Home Assistant writes to `config` is ignored by git.

`default_config` is deliberately not used in `config/configuration.yaml`, because its Bluetooth
component crashes Home Assistant on macOS.

To test against an unreleased Home Assistant, set up a
[Core development environment](https://developers.home-assistant.io/docs/development_environment).
Core's `script/setup` installs the requirements of every integration (many GBs); for running
Home Assistant and hassfest a lighter install is enough, because integration requirements are
installed on demand. From the root of the core checkout:

```shell
uv venv -p "$(cat .python-version)" venv && source venv/bin/activate
uv pip install -e . -e packages/pytest-home-assistant -r requirements_test.txt colorlog \
  --config-settings editable_mode=compat
python -m script.translations develop --all
```

Then symlink the integration into core's config directory and run it from there, replacing
`/path/to/hass-shairport-sync` with the location of this repo:

```shell
mkdir -p config/custom_components
ln -sfn /path/to/hass-shairport-sync/custom_components/shairport_sync config/custom_components/
hass -c config
```

### Releasing

1. Update `version` in `custom_components/shairport_sync/manifest.json`, `CHANGELOG.md` and the
   compatibility section above.
2. If the minimum Home Assistant version changes, update `homeassistant` in `hacs.json` and the
   matching plugin pin in the minimum job of `.github/workflows/tests.yaml`.
3. Make sure the Tests, HACS and hassfest workflows pass.
4. Tag the commit as `vX.Y.Z` and create a GitHub release from it. HACS picks up the release.

<a href="https://www.buymeacoffee.com/parautenbach" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
