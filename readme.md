# Home Assistant IHC Version 2.0
Originally this was a Home Assistant Custom integration for beta testing the IHC integration.
I now consider this as IHC integration version 2.0

(Note the github repository still has the same name, I may move to new one later)

## History

Getting the PR into the official HA was not going well, and for now I am not continuing working on that. The process was just too long, and I had to rebase my branch many times to keep up with the changes from HA. A lost of wasted time.

If anybody has the time and skill to do it - feel free to port this into HA.
Note it must be split up info many small thunks to have a changes to be accepted.

But since it has been working fine for a long time, I do not condider this a "beta" version anymore.

[Read more about it here](https://www.dingus.dk/help-testing-the-new-home-assistant-ihc-integration/)

## Installing

Intall using [hacs](https://hacs.xyz/).
Add a custom repository to hacs (using the github url of this repository).

Alternatively you can copy the custom_components/ihc folder manually to your Home Assistant configuration folder.

## Reporting bugs

If you find any bugs/problems use the issues here in github to report your findings.

## Current state

Currently these are the changes compared to the build in ihc integration:

* Configflow. Allow you to setup the IHC controller using the UI.
* The controller will be represented as a device in HA, and identified by its serial number.
* Entities will get a unique id, allowing you to easier change name/icon
* Autosetup IHC products as devices in HA. To group related entities, and easier automation (Because the HA UI now have better support for automations on devices)
* Extra attribute to identify the IHC controller on an entity. (When you have multiple IHC controllers)
* Migrating old manual config to new ihc_manual_setup.yaml file

Also see [Home Assistant IHC itegration](https://github.com/dingusdk/home-assistant.io/blob/ihcconfigflow/source/_integrations/ihc.markdown)
This my fork of the Home assistant documentation web page - and I will try to keep it updated with this beta.


