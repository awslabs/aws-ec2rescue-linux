# Copyright 2016-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""
This module contains helper functions that setup the root menu and its sub-menus and menu items.

Functions:
    get_global_menu: given a populated ModuleDir, create and return the Global sub-menu
    get_menu_config: given a populated ModuleDir, create and return the full menu structure.

Classes:
    None

Exceptions:
    None
"""
import ec2rlcore.menu
import ec2rlcore.menu_item


def get_global_menu(module_list):
    """
    Given a populated ModuleDir, create and return the Global sub-menu.

    Parameters:
        module_list (ModuleDir): contains the modules from which the sub-menu will be created.

    Returns:
        global_menu (Menu): the completed sub-menu.
    """
    global_menu = ec2rlcore.menu.Menu(row_left="Configure global module arguments",
                                      header="Select a global option to configure:",
                                      helptext="Display the parameters that have a global/program-wide meaning. These\n"
                                               "parameters can affect all modules run by EC2 Rescue for Linux.",
                                      footer_items=["Select", "Exit", "Help", "Clear"])

    # only-classes sub-menu
    onlyclasses_menu = ec2rlcore.menu.Menu(row_left="only-classes",
                                           header="Select the classes of modules you wish to run:",
                                           helptext="Configure which classes of modules to run",
                                           footer_items=["Select", "Exit", "Help"])
    for class_name in module_list.classes:
        this_class_item = ec2rlcore.menu_item.ToggleItem(row_left=class_name,
                                                         header=class_name,
                                                         helptext="Select whether this class of modules will be run.",
                                                         toggled=True)
        onlyclasses_menu.append(this_class_item)

    # only-domains sub-menu
    onlydomains_menu = ec2rlcore.menu.Menu(row_left="only-domains",
                                           header="Select the domains of modules you wish to run:",
                                           helptext="Configure which domains of modules to run",
                                           footer_items=["Select", "Exit", "Help"])
    for domain_name in module_list.domains:
        this_domain_item = ec2rlcore.menu_item.ToggleItem(row_left=domain_name,
                                                          header=domain_name,
                                                          helptext="Select whether this domain of modules will be run.",
                                                          toggled=True)
        onlydomains_menu.append(this_domain_item)

    # only-modules sub-menu
    onlymodules_menu = ec2rlcore.menu.Menu(row_left="only-modules",
                                           header="Select the modules you wish to run:",
                                           helptext="Configure which modules to run",
                                           footer_items=["Select", "Exit", "Help"])

    for module_obj in module_list:
        this_module_item = ec2rlcore.menu_item.ToggleItem(row_left=module_obj.name,
                                                          header=module_obj.name,
                                                          helptext="Select whether this module will be run.",
                                                          toggled=True)
        onlymodules_menu.append(this_module_item)

    # concurrency item
    concurrency_item = ec2rlcore.menu_item.TextEntryItem(row_left="concurrency",
                                                         header="concurrency",
                                                         helptext="Set how many modules to run in parallel. "
                                                                  "Defaults to 10 threads.",
                                                         message="Set how many modules to run in parallel. "
                                                                 "The default is 10.")

    # perfimpact item
    perfimpact_item = ec2rlcore.menu_item.ToggleItem(row_left="perfimpact",
                                                     header="perfimpact",
                                                     helptext="Enable the running of performance impacting modules.",
                                                     toggled=True)

    global_menu.append(onlyclasses_menu)
    global_menu.append(onlydomains_menu)
    global_menu.append(onlymodules_menu)
    global_menu.append(concurrency_item)
    global_menu.append(perfimpact_item)
    return global_menu


def get_menu_config(module_list):
    """
    Given a populated ModuleDir, create and return the full menu structure.

    Parameters:
        module_list (ModuleDir): contains the modules from which the menu will be created.

    Returns:
        root_menu (Menu): the completed root-level menu.
    """
    # Global menu
    global_menu = get_global_menu(module_list)

    # Modules menu
    modules_menu = ec2rlcore.menu.Menu(row_left="View all modules",
                                       header="Select a module to configure:",
                                       helptext="Displays the full list of all available modules. Each module is a\n"
                                                "further sub-menu containing the module-specific configuration\n"
                                                "parameters.",
                                       footer_items=["Select", "Exit", "Help"])

    # Modules, by class menu
    modules_by_class_menu = \
        ec2rlcore.menu.Menu(row_left="View modules, filtered by class",
                            header="Select a class of modules:",
                            helptext="Displays the available classes of modules. Each displayed module\n"
                                     "class is a further sub-menu containing the modules of the particular\n"
                                     "class. This sub-menu provides filtering to aid in finding relevant\n"
                                     "modules.",
                            footer_items=["Select", "Exit", "Help"])

    for class_name in module_list.classes:
        this_class_item = \
            ec2rlcore.menu.Menu(row_left="View the '{}' class of modules".format(class_name),
                                header="Select a module in the '{}' module class".format(class_name),
                                helptext="Displays modules belonging to the '{}' module class.\n"
                                         "Each module is a further sub-menu containing the module-specific\n"
                                         "configuration parameters.".format(class_name),
                                footer_items=["Select", "Exit", "Help"])
        modules_by_class_menu.append(this_class_item)

    # Modules, by domain menu
    modules_by_domain_menu = \
        ec2rlcore.menu.Menu(row_left="View modules, filtered by domain",
                            header="Select a domain of modules:",
                            helptext="Displays the available module domains. Each displayed module domain\n"
                                     "is a further sub-menu containing the modules of the particular\n"
                                     "domain. This sub-menu provides filtering to aid in finding relevant\n"
                                     "modules.",
                            footer_items=["Select", "Exit", "Help"])

    for domain_name in module_list.domains:
        this_domain_item = \
            ec2rlcore.menu.Menu(row_left="View the '{}' domain of modules".format(domain_name),
                                header="Select a module in the '{}' module domain".format(domain_name),
                                helptext="Displays modules belonging to the '{}' module domain.\n"
                                         "Each module is a further sub-menu containing the module-specific\n"
                                         "configuration parameters.".format(domain_name),
                                footer_items=["Select", "Exit", "Help"])
        modules_by_domain_menu.append(this_domain_item)

    for module_obj in module_list:
        this_module_menu = ec2rlcore.menu.Menu(row_left=module_obj.name,
                                               header="Module '{}' - Select an option to configure:".format(
                                                   module_obj.name),
                                               helptext=module_obj.helptext,
                                               footer_items=["Select", "Exit", "Help", "Clear"])

        # Add required and optional constraints
        for constraint_type in "required", "optional":
            for constraint_name in module_obj.constraint[constraint_type]:
                this_textentryitem = ec2rlcore.menu_item.TextEntryItem(row_left=constraint_name,
                                                                       header="Module '{}' - configure argument:".
                                                                       format(module_obj.name),
                                                                       helptext=module_obj.helptext,
                                                                       message=constraint_name)
                this_module_menu.append(this_textentryitem)

        # If there are no required or optional constraints then add a placeholder to inform the user
        if len(this_module_menu) == 0:
            this_exititem = ec2rlcore.menu_item.ExitItem(row_left="No configurable parameters.",
                                                         header=module_obj.name,
                                                         helptext="There are no parameters to configure for this "
                                                                  "module.")
            this_module_menu.append(this_exititem)

        modules_menu.append(this_module_menu)

        # Update the module grouping mappings so modules appear in the filter menus
        for domain_name in module_obj.constraint["domain"]:
            modules_by_domain_menu["View the '{}' domain of modules".format(domain_name)].append(this_module_menu)

        for class_name in module_obj.constraint["class"]:
            modules_by_class_menu["View the '{}' class of modules".format(class_name)].append(this_module_menu)

    exit_item = ec2rlcore.menu_item.RunItem(row_left="Run this configuration",
                                            header="Run this configuration",
                                            helptext="Exits the menu, saves the current configuration for later use, "
                                                     "and\nruns EC2 Rescue for Linux with the current configuration.")

    run_item = ec2rlcore.menu_item.ExitItem(row_left="Save and exit",
                                            header="Save and exit",
                                            helptext="Exits the menu and saves the current configuration for later "
                                                     "use.")

    # root menu
    root_menu = ec2rlcore.menu.Menu(row_left="root",
                                    header="Select an option:",
                                    helptext="This is the root menu and it has no help option.",
                                    footer_items=["Select", "Exit", "Help"])

    root_menu.append(global_menu)
    root_menu.append(modules_menu)
    root_menu.append(modules_by_class_menu)
    root_menu.append(modules_by_domain_menu)
    root_menu.append(run_item)
    root_menu.append(exit_item)

    return root_menu
