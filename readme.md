# Home Assistant IHC Beta testing

This is a Home Assistant Custom integration for beta testing the IHC integration.
I will used this when making some bigger changes to the IHC integration in Home Assisant for beta testing before the code is commited to the main Home Assistant.
This makes it easier for you to do testing, and it also makes it easier and faster to do changes without having to wait for a PR in home assistant.

## Installing

Intall using [hacs](https://hacs.xyz/).
Add a custom repository to hacs (using the github url of this repository).

Alternatively you can copy the custom_components/ihc folder manually to your Home Assistant configuration folder.

## Reporting bugs

If you find any bugs/problems use the issues here in github to report your findings.

## Current state

Currently the beta testing has these changes:

* Configflow. Allow you to setup the IHC controller using the UI.
* The controller will be represented as a device in HA, and identified by its serial number.
* Entities will get a unique id, allowing you to easier change name/icon
* Autosetup IHC products as devices in HA. To group related entities, and easier automation (Because the HA UI now have better support for automations on devices)
* Extra attribute to identify the IHC controller on an entity. (When you have multiple IHC controllers)
* Migrating old manual config to new ihc_manual_setup.yaml file

See [dingus.dk](https://www.dingus.dk) for more infomation.
Also see [Home Assistant IHC itegration](https://github.com/dingusdk/home-assistant.io/blob/current/source/_integrations/ihc.markdown)
This my fork of the Home assistant web page - and I will try to keep it updated with this beta.


