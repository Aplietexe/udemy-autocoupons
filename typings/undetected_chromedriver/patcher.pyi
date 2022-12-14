"""
This type stub file was generated by pyright.
"""

logger = ...
IS_POSIX = ...
class Patcher:
    url_repo = ...
    zip_name = ...
    exe_name = ...
    platform = ...
    if platform.endswith("win32"):
        ...
    if platform.endswith("linux"):
        ...
    if platform.endswith("darwin"):
        ...
    if platform.endswith("win32"):
        d = ...
    else:
        d = ...
    data_path = ...
    def __init__(self, executable_path=..., force=..., version_main: int = ...) -> None:
        """

        Args:
            executable_path: None = automatic
                             a full file path to the chromedriver executable
            force: False
                    terminate processes which are holding lock
            version_main: 0 = auto
                specify main chrome version (rounded, ex: 82)
        """
        ...
    
    def auto(self, executable_path=..., force=..., version_main=...): # -> int | bool | None:
        """"""
        ...
    
    def patch(self): # -> bool:
        ...
    
    def fetch_release_number(self): # -> LooseVersion:
        """
        Gets the latest major version available, or the latest major version of self.target_version if set explicitly.
        :return: version string
        :rtype: LooseVersion
        """
        ...
    
    def parse_exe_version(self): # -> LooseVersion | None:
        ...
    
    def fetch_package(self): # -> str:
        """
        Downloads ChromeDriver from source

        :return: path to downloaded file
        """
        ...
    
    def unzip_package(self, fp): # -> str | None:
        """
        Does what it says

        :return: path to unpacked executable
        """
        ...
    
    @staticmethod
    def force_kill_instances(exe_name): # -> bool:
        """
        kills running instances.
        :param: executable name to kill, may be a path as well

        :return: True on success else False
        """
        ...
    
    @staticmethod
    def gen_random_cdc(): # -> bytes:
        ...
    
    def is_binary_patched(self, executable_path=...): # -> bool:
        """simple check if executable is patched.

        :return: False if not patched, else True
        """
        ...
    
    def patch_exe(self): # -> int:
        """
        Patches the ChromeDriver binary

        :return: False on failure, binary name on success
        """
        ...
    
    def __repr__(self): # -> str:
        ...
    
    def __del__(self): # -> None:
        ...
    


