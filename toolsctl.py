#!/usr/bin/env python3
#
# Copyright (c) 2020 Wikimedia Foundation and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import logging
import sys

import ldap3
import ldap3.utils.log
import yaml


def list_tools(args):
    """List tools."""
    conn = ldap3.Connection(
        args.config["ldap"]["servers"],
        auto_bind=True,
        read_only=True,
    )
    r = conn.extend.standard.paged_search(
        "ou=servicegroups,{}".format(args.config["ldap"]["basedn"]),
        "(&(objectClass=groupOfNames)(cn={}.*))".format(args.config["project"]),
        attributes=["cn", "member"],
        paged_size=256,
        time_limit=5,
        generator=True,
    )
    for tool in r:
        print(tool["attributes"]["cn"][0])
        for member in tool["attributes"]["member"]:
            print("    {}".format(member))
    return 0


def add_tool(args):
    """Add a tool."""
    conn = ldap3.Connection(
        args.config["ldap"]["servers"],
        user=args.config["ldap"]["user"],
        password=args.config["ldap"]["password"],
        auto_bind=True,
    )

    base_dn = "ou=servicegroups,{}".format(args.config["ldap"]["basedn"])
    # Create the service group
    group_cn = "{}.{}".format(args.config["project"], args.tool)
    group_dn = "cn={},{}".format(group_cn, base_dn)
    gid = str(get_next_gid(conn, args))
    r = conn.add(
        dn=group_dn,
        object_class=["posixGroup", "groupOfNames"],
        attributes={
            "cn": group_cn,
            "gidNumber": gid,
            "member": args.maintainer,  # FIXME
        },
    )
    if r:
        logging.info("Created %s", group_dn)
    else:
        logging.error("Failed to create %s: %s", group_dn, conn.last_error)
        return 1

    # Create the tool user
    user_dn = "cn={},ou=people,{}".format(group_cn, base_dn)
    r = conn.add(
        dn=user_dn,
        object_class=["shadowAccount", "posixAccount", "person", "top"],
        attributes={
            "uid": group_cn,
            "cn": group_cn,
            "sn": group_cn,
            "uidNumber": gid,
            "gidNumber": gid,
            "homeDirectory": "/data/project/{}".format(args.tool),
            "loginShell": "/bin/bash",
        },
    )
    if r:
        logging.info("Created %s", user_dn)
    else:
        logging.error("Failed to create %s: %s", user_dn, conn.last_error)
        return 1

    # Create sudoers rule
    sudo_cn = "runas-{}".format(group_cn)
    sudo_dn = "cn={},ou=sudoers,cn={},ou=projects,{}".format(
        sudo_cn, args.config["project"], args.config["ldap"]["basedn"]
    )
    r = conn.add(
        dn=sudo_dn,
        object_class=["sudoRole"],
        attributes={
            "cn": sudo_cn,
            "sudoUser": ["%{}".format(group_cn)],
            "sudoHost": ["ALL"],
            "sudoCommand": ["ALL"],
            "sudoOption": ["!authenticate"],
            "sudoRunAsUser": [group_cn],
        },
    )
    if r:
        logging.info("Created %s", sudo_dn)
    else:
        logging.error("Failed to create %s: %s", sudo_dn, conn.last_error)
        return 1
    return 0


def get_gid(args):
    conn = ldap3.Connection(
        args.config["ldap"]["servers"],
        auto_bind=True,
        read_only=True,
    )
    print(get_next_gid(conn, args))
    return 0


def get_next_gid(conn, args):
    r = conn.extend.standard.paged_search(
        args.config["ldap"]["basedn"],
        "(objectClass=posixGroup)",
        attributes=["gidNumber"],
        paged_size=256,
        time_limit=5,
        generator=True,
    )
    next_id = max(
        max(int(g["attributes"]["gidNumber"][0]) for g in r) + 1,
        args.config["gid"]["min"]
    )
    if next_id > args.config["gid"]["max"]:
        logging.warning(
            "GID range limit exceeded. Soft limit %d; next %d",
            args.config["gid"]["max"],
            next_id
        )
    return next_id


def main():
    """Manage tools."""
    parser = argparse.ArgumentParser(description="Tools manager")
    parser.add_argument(
        "-v", "--verbose", action="count",
        default=0, dest="loglevel", help="Increase logging verbosity")
    parser.add_argument(
        "--config", default="/home/bd808/projects/toolsbeta/config.yaml",
        help="Configuration file")

    subparsers = parser.add_subparsers(
        title="actions", description="valid actions", dest="action",
        help="additional help")
    subparsers.required = True

    parser_list = subparsers.add_parser("list", help="List tools")
    parser_list.set_defaults(func=list_tools)

    parser_gid = subparsers.add_parser("gid", help="Show next GID")
    parser_gid.set_defaults(func=get_gid)

    parser_add = subparsers.add_parser("add", help="Add a new tool")
    parser_add.add_argument(
        "tool", help="Tool name")  # FIXME: validate tool name
    parser_add.add_argument(
        "-m", "--maintainer", action="append", required=True,
        help="Tool maintainer")
    parser_add.set_defaults(func=add_tool)

    args = parser.parse_args()

    logging.basicConfig(
        level=max(logging.DEBUG, logging.WARNING - (10 * args.loglevel)),
        format="%(asctime)s %(name)-12s %(levelname)-8s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ"
    )
    logging.captureWarnings(True)
    ldap3.utils.log.set_library_log_detail_level(ldap3.utils.log.EXTENDED)

    cfg = yaml.safe_load(open(args.config))
    args.config = cfg

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
