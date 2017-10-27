#!/usr/bin/python
#
# Copyright 2017 Sam Novak
#
# Based on autopkg processors written by Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""See docstring for MinimumOSExtractor class"""

import os.path

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter
import FoundationPlist
import platform

__all__ = ["MinimumOSExtractor"]



class MinimumOSExtractor(DmgMounter):
    """Returns a string of valid operating systems from a plist and puts it in OS_REQUIREMENTS
       Example usage:
        <dict>
            <key>Arguments</key>
            <dict>
                <key>input_plist_path</key>
                <string>%RECIPE_CACHE_DIR%/downloads/%NAME%.app/Contents/Info.plist</string>
                <key>maximum_os_version</key>
                <string>10.12</string>
            </dict>
            <key>Processor</key>
            <string>MinimumOSExtractor</string>
        </dict>
       """
    description = __doc__

    input_variables = {
        "input_plist_path": {
            "required": True,
            "description":
                ("File path to a plist. Can point to a path inside a .dmg "
                 "which will be mounted."),
        },
        "maximum_os_version": {
            "required": False,
            "default": "HOST_OS",
            "description":
                ("The maximum support operating system; "
                 "Defaults to the OS Version of the system running autopkg."),
        },
        "minimum_os_version": {
            "required": False,
            "default": "10.7",
            "description":
                ("The oldest operating system that is to be used in the range; "
                 "Defaults to 10.7. If the value of the second digit matches that of"
                 "LSMinimumSystemVersion, no OS_REQUIREMENTS value will be generated."
                 "Long story short, if it runs on, in this case, 10.7, don't make an OS list"),
        },
    }
    output_variables = {
        "os_requirements": {
            "description": "Version of the item.",
        },
    }

    def main(self):
        """Return a version for file at input_plist_path"""
        # Check if we're trying to read something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = (
            self.parsePathForDMG(self.env['input_plist_path']))
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                input_plist_path = os.path.join(mount_point, dmg_source_path)
            else:
                # just use the given path
                input_plist_path = self.env['input_plist_path']
            if not os.path.exists(input_plist_path):
                raise ProcessorError(
                    "File '%s' does not exist or could not be read." %
                    input_plist_path)
            try:
                plist = FoundationPlist.readPlist(input_plist_path)
                minimum_os_version = plist.get("LSMinimumSystemVersion", "No_Minimum")

                # Set the Maximum OS, if default
                # https://stackoverflow.com/a/1777365
                maximum_os_version = str(self.env['maximum_os_version'])
                if maximum_os_version is 'HOST_OS':
                    # https://stackoverflow.com/a/1777365
                    v, _, _ = platform.mac_ver()
                    v = str('.'.join(v.split('.')[:2]))
                    # Append on .x
                    # maximum_os_version = v + '.x'
                # else:
                #   if not maximum_os_version.endswith(".x"):
                #       maximum_os_version = maximum_os_version + '.x'

                # At this point it's fairly safe to say the Lion (10.7)
                # is an acceptably low number to consider an app not having a minimum OS
                if int(minimum_os_version.split('.')[1]) is int((self.env['minimum_os_version']).split('.')[1]):
                    minimum_os_version = 'No_Minimum'

                if not minimum_os_version is 'No_Minimum':
                    # Create the list of all the OS's between the min and max
                    # It's ok if minimum_os_version contains 3 numbers, since
                    # we only use the second one to create our range
                    os_min = int(minimum_os_version.split('.')[1])
                    # You have to add one to the maximum OS version, because the range
                    # appears to start at the minimum, but end one short of the max
                    os_max = int(maximum_os_version.split('.')[1]) + 1
                    os_requirement = ''
                    for os_version in range(os_min, os_max):
                        if os_requirement is '':
                            os_requirement = '10.' + str(os_version) + '.x'
                        else:
                            os_requirement = os_requirement + ',10.' + str(os_version) + '.x'
                    self.env['OS_REQUIREMENTS'] = os_requirement
                else:
                    self.env['OS_REQUIREMENTS'] = ''

                self.output("OS Version requirements %s in file %s"
                            % (self.env['os_requirement'], input_plist_path))

            except FoundationPlist.FoundationPlistException, err:
                raise ProcessorError(err)

        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == '__main__':
    PROCESSOR = MinimumOSExtractor()
    PROCESSOR.execute_shell()