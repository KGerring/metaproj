"""
Validator('NAME', 'OTHER_NAME', 'EVEN_OTHER')
Validator(r'^NAME', r'OTHER./*')

operations:
	is_type_of: isinstance(value, type)
	is_in:  value in sequence
	is_not_in: value not in sequence
	identity: value is other
	cont: contain value in
	len_eq: len(value) == other
	
`env` is which env to be checked, can be a list or default is used.
`when` holds a validator and its return decides if validator runs or not::

	 Validator('NAME', must_exist=True, when=Validator('OTHER', eq=2))
	 # NAME is required only if OTHER eq to 2
	 # When the very first thing to be performed when passed.
     # if no env is passed to `when` it is inherited
	
`must_exist` is alias to `required` requirement. (executed after when)::
condition is a callable to be executed and return boolean::

    Validator('NAME', condition=lambda x: x == 1)
    # it is executed before operations.
    
"""
from __future__ import annotations

import sys

from dynaconf import Dynaconf
from dynaconf.base import LazySettings
from dynaconf.base import Settings

sys.stdout.write("OKOKOK")

# dynaconf_settings
# environments_for_dynaconf
# force_env
# includes_for_dynaconf
# lowercase_read_for_dynaconf
# merge_enabled_for_dynaconf
# preload_for_dynaconf
# project_root
# project_root_for_dynaconf
# root_path_for_dynaconf
# secrets_for_dynaconf

# dynaconf_include = ['configs/*']
ENVIRONMENTS = [
		"DEFAULT",
		"DEVELOPMENT",
		"GLOBAL",
		"PRODUCTION",
		"SECRETS",
		"STAGING",
		"STARTUP",
		"TESTING",
]


settings = LazySettings(
	load_dotenv=True,
	dotenv_override = True,
	dotenv_path = '.env',
	redis_enabled = True,
	includes = [],
	environments = True,
    envvar_prefix="DYNACONF",
	lowercase_read = False,
	LOWERCASE_READ_FOR_DYNACONF = False,
	merge_enabled = True,
    settings_files=['settings/settings.toml', '.secrets.toml',
                    'settings.py', '.secrets.py',
                    'settings.yaml', '.secrets.yaml'],
	secrets = [],
)

"""
# Extra file, or list of files where to look for secrets
# useful for CI environment like jenkins
# where you can export this variable pointing to a local
# absolute path of the secrets file.
SECRETS_FOR_DYNACONF = get("SECRETS_FOR_DYNACONF", None)

# To include extra paths based on envvar
INCLUDES_FOR_DYNACONF = get("INCLUDES_FOR_DYNACONF", [])

# To pre-load extra paths based on envvar
PRELOAD_FOR_DYNACONF = get("PRELOAD_FOR_DYNACONF", [])

# Files to skip if found on search tree
SKIP_FILES_FOR_DYNACONF = get("SKIP_FILES_FOR_DYNACONF", [])


"""

# The current env by default is DEVELOPMENT
# to switch is needed to `export ENV_FOR_DYNACONF=PRODUCTION`
# Merge objects on load
#MERGE_ENABLED_FOR_DYNACONF = get("MERGE_ENABLED_FOR_DYNACONF", False)
# REDIS_ENABLED_FOR_DYNACONF = False

# Use commentjson? https://commentjson.readthedocs.io/en/latest/
#COMMENTJSON_ENABLED_FOR_DYNACONF = get("COMMENTJSON_ENABLED_FOR_DYNACONF", False)

# DOTENV_PATH_FOR_DYNACONF = get("DOTENV_PATH_FOR_DYNACONF", None)
# DOTENV_VERBOSE_FOR_DYNACONF = get("DOTENV_VERBOSE_FOR_DYNACONF", False)
# DOTENV_OVERRIDE_FOR_DYNACONF = get("DOTENV_OVERRIDE_FOR_DYNACONF", False)
# core_loaders = ["YAML", "TOML", "INI", "JSON", "PY"]

# Default values is taken from DEFAULT pseudo env
# this value is used only when reading files like .toml|yaml|ini|json
# DEFAULT_ENV_FOR_DYNACONF = "DEFAULT"
# LOWERCASE_READ_FOR_DYNACONF
# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load this files in the order.

if __name__ == '__main__':
	print(settings.keys())
