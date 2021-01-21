Toolsctl
========

Toolsctl is a command line program that can be used to list and create
[Toolforge] tool accounts stored in an LDAP directory. This functionality is
provided as part of the [Striker application] for the production Toolforge
deployment. In a testing environment without Striker, this tool can be used as
an easier replacement than manual LDAP edits.


Usage
-------
Create a configuration file (yaml format) based on the example (values in that
file are aimed at Mediawiki Vagrant's striker role). You are likely to need to 
use the --config argument to point to your file.

The tool name is automatically prepended with the tool name and a dot, so don't
include "tools." before the name.  The required maintainer argument should be an
LDAP user (eg. uid=bstorm,ou=people,dc=wikimedia,dc=org).

Full example:
`./toolsctl.py --config config.yaml add -m uid=bstorm,ou=people,dc=wikimedia,dc=org test6`



License
-------
Toolsctl is licensed under the [Apache-2.0] license.

[Toolforge]: https://wikitech.wikimedia.org/wiki/Portal:Toolforge
[Striker application]: https://wikitech.wikimedia.org/wiki/Striker
[Apache-2.0]: https://www.apache.org/licenses/LICENSE-2.0
