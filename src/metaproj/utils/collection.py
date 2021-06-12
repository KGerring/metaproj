from __future__ import annotations

import collections
import contextlib
import os
import re
import threading
from ast import literal_eval
from collections.abc import MutableMapping
from contextlib import contextmanager
from typing import Any
from typing import Generator
from typing import Iterable
from typing import Iterator
from typing import MutableMapping as T_MutableMapping
from typing import Optional
from typing import Pattern
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast

import appdirs
from box import Box
from dotenv import dotenv_values
from dotenv import find_dotenv

from ..common import config as fixit_config

appdirs.system = "linux2"

ENV_FILE: str = find_dotenv(".env", usecwd=True)
_env = dotenv_values(ENV_FILE, verbose=True)


class DotDict(MutableMapping):
    """
    A `dict` that also supports attribute ("dot") access. Think of this as an extension
    to the standard python `dict` object.  **Note**: while any hashable object can be added to
    a `DotDict`, _only_ valid Python identifiers can be accessed with the dot syntax; this excludes
    strings which begin in numbers, special characters, or double underscores.

    :param dict init_dict: dictionary to initialize the `DotDict` with
    :param kwargs: key, value pairs with which to initialize the DotDict

    .. :code-block: python
    >>> dotdict = DotDict({'a': 34}, b=56, c=set())
    >>> dotdict.a # 34
    ... 34
    >>> dotdict['b'] # 56
    ... 56
    >>> dotdict.c # set()
    ... set()

    """
    
    def __init__(self, init_dict: DictLike = None, **kwargs: Any):
        # a DotDict could have a key that shadows `update`
        if init_dict:
            super().update(init_dict)
        super().update(kwargs)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        This method is defined for MyPy, which otherwise tries to type
        the inherited `.get()` method incorrectly.

        :param str key (str): the key to retrieve
        :param Any default: a default value to return if the key is not found
        :return: the value of the key, or the default value if the key is not found
        :rtype: Any
        """
        return super().get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        return self.__dict__[key]  # __dict__ expects string keys
    
    def __setitem__(self, key: str, value: Any) -> None:
        self.__dict__[key] = value
    
    def __setattr__(self, attr: str, value: Any) -> None:
        self[attr] = value
    
    def __iter__(self) -> Iterator[str]:
        return iter(self.__dict__.keys())
    
    def __delitem__(self, key: str) -> None:
        del self.__dict__[key]
    
    def __len__(self) -> int:
        return len(self.__dict__)
    
    def __repr__(self) -> str:
        if len(self) > 0:
            return "<{}: {}>".format(type(self).__name__, ", ".join(sorted(repr(k) for k in self.keys())))
        else:
            return "<{}>".format(type(self).__name__)
    
    def copy(self) -> DotDict:
        """Creates and returns a shallow copy of the current DotDict"""
        return type(self)(self.__dict__.copy())
    
    def to_dict(self) -> dict:
        """
        Converts current `DotDict` (and any `DotDict`s contained within)
        to an appropriate nested dictionary.
        """
        # mypy cast
        return cast(dict, as_nested_dict(self, dct_class=dict))

D = TypeVar("D", bound=Union[dict, MutableMapping])
DictLike = Union[dict, DotDict]
INTERPOLATION_REGEX: Pattern[str] = re.compile(r"\${(.[^${}]*)}")
DOTENV_REGEX: Pattern[str] = re.compile(r'\$\{(?P<name>[^\}:]*)(?::-(?P<default>[^\}]*))?\}')
ENV_VAR_PREFIX = "FIXIT"
DEFAULT_CONFIG = fixit_config.LINT_CONFIG_TOML_NAME.resolve() #LINT_CONFIG_TOML_NAME
YAML_CONFIG =   fixit_config.LINT_CONFIG_FILE_NAME.resolve()
LINT_CONFIG_SCHEMA_NAME = fixit_config.LINT_CONFIG_SCHEMA_NAME
appdir = appdirs.AppDirs("fixit")
_config_dir: str = appdir.user_config_dir

def flatten_seq(seq: Iterable) -> Generator:
    """
    Generator that returns a flattened list from a possibly nested list-of-lists
    (or any sequence type).
    :param Iterable seq: the sequence to flatten
    :return: a generator that yields the flattened sequence

    >>> flatten_seq([1, 2, [3, 4], 5, [6, [7]]])
    ... [1, 2, 3, 4, 5, 6, 7]


    """
    for item in seq:
        if isinstance(item, collections.abc.Iterable) and not isinstance(item, (str, bytes)):
            yield from flatten_seq(item)
        else:
            yield item

def merge_dicts(d1: DictLike, d2: DictLike) -> DictLike:
    """
    Updates `d1` from `d2` by replacing each `(k, v1)` pair in `d1` with the
    corresponding `(k, v2)` pair in `d2`.

    If the value of each pair is itself a dict, then the value is updated
    recursively.

    :param MutableMapping d1: A dictionary to be replaced
    :param MutableMapping d2: A dictionary used for replacement

    :return: A `MutableMapping` with the two dictionary contents merged
    :rtype: MutableMapping
    """

    new_dict = d1.copy()

    for k, v in d2.items():
        if isinstance(new_dict.get(k), MutableMapping) and isinstance(v, MutableMapping):
            new_dict[k] = merge_dicts(new_dict[k], d2[k])
        else:
            new_dict[k] = d2[k]
    return new_dict

def as_nested_dict(
    obj: Union[DictLike, Iterable[DictLike]],
    dct_class: type = DotDict
) -> Union[DictLike, Iterable[DictLike]]:
    """
    Given a obj formatted as a dictionary, transforms it (and any nested dictionaries)
    into the provided dct_class

    :param Any obj: An object that is formatted as a `dict`
    :param type dct_class: the `dict` class to use (defaults to DotDict)
    :return: A `dict_class` representation of the object passed in
    """
    if isinstance(obj, (list, tuple, set)):
        return type(obj)([as_nested_dict(d, dct_class) for d in obj])

    # calling as_nested_dict on `Box` objects pulls out their "private" keys due to our recursion
    # into `__dict__` if it exists. We can special-case Box and just convert it to dict this way,
    # which automatically handles recursion.
    elif isinstance(obj, Box):
        return dict(obj)
    elif isinstance(obj, (dict, DotDict)):
        # DotDicts could have keys that shadow `update` and `items`, so we
        # take care to avoid accessing those keys here
        return dct_class({k: as_nested_dict(v, dct_class) for k, v in getattr(obj, "__dict__", obj).items()})
    return obj

class CompoundKey(tuple):
    pass

def dict_to_flatdict(dct: DictLike, parent: CompoundKey = None) -> dict:
    """Converts a (nested) dictionary to a flattened representation.

        Each key of the flat dict will be a CompoundKey tuple containing
        the "chain of keys" for the corresponding value.
        :param dct: The dictionary to flatten
        :param CompoundKey parent: Defaults to `None`. The parent key (you shouldn't need to set this)
        :return: A flattened dict
        
    """
    items = []  # type: list
    parent = parent or CompoundKey()
    for k, v in dct.items():
        k_parent = CompoundKey(parent + (k,))
        if isinstance(v, dict):
            items.extend(dict_to_flatdict(v, parent=k_parent).items())
        else:
            items.append((k_parent, v))
    return dict(items)

def flatdict_to_dict(dct: dict, dct_class: Type[D] = None) -> D:
    """Converts a flattened dictionary back to a nested dictionary.
    :param dict dct: The dictionary to be nested. Each key should be a
            `CompoundKey`, as generated by `dict_to_flatdict()`
    :param type Type[D] dct_class: the type of the result; defaults to `dict`
    :return: An instance of `dct_class` used to represent a nested dictionary, bounded
        as a MutableMapping or dict
    """
    result = cast(D, (dct_class or dict)())
    for k, v in dct.items():
        if isinstance(k, CompoundKey):
            current_dict = result
            for ki in k[:-1]:
                current_dict = current_dict.setdefault(ki, (dct_class or dict)())  # type: ignore
            current_dict[k[-1]] = v
        else:
            result[k] = v

    return result

class Config(Box):
    """
    A config is a Box subclass
    """
    
    def copy(self) -> Config:
        """
        Create a recursive copy of the config. Each level of the Config is a new Config object, so
        modifying keys won't affect the original Config object. However, values are not
        deep-copied, and mutations can affect the original.
        """
        new_config = Config()
        for key, value in self.items():
            if isinstance(value, Config):
                value = value.copy()
            new_config[key] = value
        return new_config

def validate_config(config: Config) -> None:
    """
    Validates that the configuration file is valid.
        - keys do not shadow Config methods

    Note that this is performed when the config is first loaded, but not after.
    """
    def check_valid_keys(config: Config) -> None:
        """
        Recursively check that keys do not shadow methods of the Config object
        """
        invalid_keys = dir(Config)
        for k, v in config.items():
            if k in invalid_keys:
                raise ValueError(f"Invalid config key: {k!r}")
            if isinstance(v, Config):
                check_valid_keys(v)
    check_valid_keys(config)

def string_to_type(val: str) -> Union[bool, int, float, str]:
    """
    Helper function for transforming string env var values into typed values.

    Maps:
        - "true" (any capitalization) to `True`
        - "false" (any capitalization) to `False`
        - any other valid literal Python syntax interpretable by ast.literal_eval

    Arguments:
        - val (str): the string value of an environment variable

    Returns:
        Union[bool, int, float, str, dict, list, None, tuple]: the type-cast env var value
    """
    
    # bool
    if val.upper() == "TRUE":
        return True
    elif val.upper() == "FALSE":
        return False
    
    # dicts, ints, floats, or any other literal Python syntax
    try:
        from ast import literal_eval
        
        val_as_obj = literal_eval(val)
        return val_as_obj
    except Exception:
        pass
    
    # return string value
    return val

def interpolate_env_vars(
    env_var: str
) -> Optional[Union[bool, int, float, str]]:
    """
    Expands (potentially nested) env vars by repeatedly applying
    `expandvars` and `expanduser` until interpolation stops having
    any effect.
    """
    if not env_var or not isinstance(env_var, str):
        return env_var
    counter = 0
    while counter < 10:
        interpolated = os.path.expanduser(os.path.expandvars(str(env_var)))
        if interpolated == env_var:
            # if a change was made, apply string-to-type casts; otherwise leave alone
            # this is because we don't want to override TOML type-casting if this function
            # is applied to a non-interpolated value
            if counter > 1:
                interpolated = string_to_type(interpolated)  # type: ignore
            return interpolated
        else:
            env_var = interpolated
        counter += 1
    return None

def interpolate_config(config: dict,
                       env_var_prefix: str = None
                       ) -> Config:
    """
    Processes a config dictionary, such as the one loaded from `load_toml`.
    :param dict config:
    :param str env_var_prefix:

    # check if any env var sets a configuration value with the format:
        [ENV_VAR_PREFIX]__[Section]__[Optional Sub-Sections...]__[Key] = Value
         and if it does, add it to the config file.

    """
    # toml supports nested dicts, so we work with a flattened representation to do any
    # requested interpolation
    flat_config = dict_to_flatdict(config)
    
    # --------------------- Interpolate env vars -----------------------
    # check if any env var sets a configuration value with the format:
    #     [ENV_VAR_PREFIX]__[Section]__[Optional Sub-Sections...]__[Key] = Value
    # and if it does, add it to the config file.
    
    if env_var_prefix:
        
        for env_var, env_var_value in os.environ.items():
            if env_var.startswith(env_var_prefix + "__"):
                
                # strip the prefix off the env var
                env_var_option = env_var[len(env_var_prefix + "__") :]
                
                # make sure the resulting env var has at least one delimitied section and key
                if "__" not in env_var:
                    continue
                
                # place the env var in the flat config as a compound key
                if env_var_option.upper().startswith("CONTEXT__SECRETS"):
                    formatted_option = env_var_option.split("__")
                    formatted_option[:-1] = [val.lower() for val in formatted_option[:-1]]
                    config_option = CompoundKey(formatted_option)
                else:
                    config_option = CompoundKey(env_var_option.lower().split("__"))
                
                flat_config[config_option] = string_to_type(
                    cast(str, interpolate_env_vars(env_var_value)))
    
    # interpolate any env vars referenced
    for k, v in list(flat_config.items()):
        val = interpolate_env_vars(v)
        if isinstance(val, str):
            val = string_to_type(val)
        flat_config[k] = val
    
    # --------------------- Interpolate other config keys -----------------
    # TOML doesn't support references to other keys... but we do!
    # This has the potential to lead to nasty recursions, so we check at most 10 times.
    # we use a set called "keys_to_check" to track only the ones of interest, so we aren't
    # checking every key every time.
    
    keys_to_check = set(flat_config.keys())
    for _ in range(10):
        
        # iterate over every key and value to check if the value uses interpolation
        for k in list(keys_to_check):
            
            # if the value isn't a string, it can't be a reference, so we exit
            if not isinstance(flat_config[k], str):
                keys_to_check.remove(k)
                continue
            
            # see if the ${...} syntax was used in the value and exit if it wasn't
            match = INTERPOLATION_REGEX.search(flat_config[k])
            if not match:
                keys_to_check.remove(k)
                continue
            
            # the matched_string includes "${}"; the matched_key is just the inner value
            matched_string = match.group(0)
            matched_key = match.group(1)
            
            # get the referenced key from the config value
            ref_key = CompoundKey(matched_key.split("."))
            # get the value corresponding to the referenced key
            ref_value = flat_config.get(ref_key, "")
            
            # if the matched was the entire value, replace it with the interpolated value
            if flat_config[k] == matched_string:
                flat_config[k] = ref_value
            # if it was a partial match, then drop the interpolated value into the string
            else:
                flat_config[k] = flat_config[k].replace(
                    matched_string, str(ref_value), 1)
    return cast(Config, flatdict_to_dict(flat_config, dct_class=Config))


def load_configuration(
    path: str = DEFAULT_CONFIG,
    env_var_prefix: str = ENV_VAR_PREFIX,
    user_config_path: str = YAML_CONFIG,
    *,
    backend_config_path: Optional[str] = None,
) -> Config:
    """
    Loads a configuration from a known location.

    :param str path: the path to the default TOML configuration file.
    :param str user_config_path: an optional path to a user config file.
        If a user config is provided, it will be used to update the main config prior to interpolation
    :param str backend_config_path:
    :param str env_var_prefix: any env vars matching this prefix will be used to create
            configuration values

    :rtype: Config

    """
    
    from anyconfig import load

    # load default config
    
    default_config = load(interpolate_env_vars(path))
    
    # load user config
    if user_config_path and os.path.isfile(str(interpolate_env_vars(user_config_path))):
        user_config = load(user_config_path)
        
        # merge user config into default config
        default_config = cast(dict, merge_dicts(default_config, user_config))
    
    # load backend config
    if backend_config_path and os.path.isfile(str(interpolate_env_vars(backend_config_path))):
        
        backend_config = load(backend_config_path)
        # merge backend config into default config
        default_config = cast(dict, merge_dicts(default_config, backend_config))
    
    # interpolate after user config has already been merged
    config = interpolate_config(default_config, env_var_prefix=env_var_prefix)
    
    validate_config(config)
    return config

config = load_configuration()

class Context(DotDict, threading.local):
    """
    A thread safe context store for Prefect data.

    The `Context` is a `DotDict` subclass, and can be instantiated the same way.

    Args:
        - *args (Any): arguments to provide to the `DotDict` constructor (e.g.,
            an initial dictionary)
        - **kwargs (Any): any key / value pairs to initialize this context with
    # Initialize with config context
    init = {}
    init.update(config.get("context", {}))
    # Overwrite with explicit args
    init.update(dict(*args, **kwargs))
    init["config"] = merge_dicts(config, init.get("config", {}))

    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        init = {}
        # Initialize with config context
        init.update(config.get("context", {}))
        # Overwrite with explicit args
        init.update(dict(*args, **kwargs))
        # Merge in config (with explicit args overwriting)
        init["config"] = merge_dicts(config, init.get("config", {}))
        super().__init__(init)
    
    def __getstate__(self) -> None:
        """
        Because we dynamically update context during runs, we don't ever want to pickle
        or "freeze" the contents of context.  Consequently it should always be accessed
        as an attribute of the prefect module.
        """
        raise TypeError("Pickling context objects is explicitly not supported. You should always " "access context as an attribute of the `prefect` module, as in `prefect.context`")
    
    def __repr__(self) -> str:
        return "<Context>"
    
    @contextlib.contextmanager
    def __call__(self, *args: T_MutableMapping, **kwargs: Any) -> Iterator[Context]:
        """
        A context manager for setting / resetting the Prefect context

        Example:
            import prefect.context
            with prefect.context(dict(a=1, b=2), c=3):
                print(prefect.context.a) # 1
        """
        # Avoid creating new `Context` object, copy as `dict` instead.
        previous_context = self.__dict__.copy()
        try:
            new_context = dict(*args, **kwargs)
            if "config" in new_context:
                new_context["config"] = merge_dicts(self.get("config", {}), new_context["config"])
            self.update(new_context)  # type: ignore
            yield self
        finally:
            self.clear()
            self.update(previous_context)

context = Context()

@contextmanager
def set_temporary_config(temp_config: dict) -> Iterator:
    """
    Temporarily sets configuration values for the duration of the context manager.

    :param dict temp_config: a dictionary containing (possibly nested) configuration keys and
            values. Nested configuration keys should be supplied as `.`-delimited strings.

    .. :code-block: python
    >>> with set_temporary_config({'setting': 1, 'nested.setting': 2}):
        assert config.setting == 1
        assert config.nested.setting == 2

    """
    try:
        old_config = config.copy()
        for key, value in temp_config.items():
            # the `key` might be a dot-delimited string, so we split on "." and set the value
            cfg = config
            subkeys = key.split(".")
            for subkey in subkeys[:-1]:
                cfg = cfg.setdefault(subkey, Config())
            cfg[subkeys[-1]] = value
        # ensure the new config is available in context
        with prefect.context(config=config):
            yield config
    finally:
        config.clear()
        config.update(old_config)




__all__ = sorted(
    [
        getattr(v, "__name__", k)
        for k, v in list(globals().items())  # export
        if ((callable(v) and getattr(v, "__module__", "") == __name__ or k.isupper()) and not getattr(v, "__name__", k).startswith("__"))  # callables from this module  # or CONSTANTS
    ]
)  # neither marked internal
