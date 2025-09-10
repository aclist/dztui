import json
import struct
import typing  # noqa

from dataclasses import dataclass
from enum import Enum
from packaging.version import Version
from pathlib import Path
from shlex import shlex
from typing import BinaryIO, Union

# https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
endian = "<"
IMAGE_DIRECTORY_ENTRY = 2
VERSION_RESOURCE = 16
RESOURCE_NODE = ".rsrc"
PE32_x86 = "0x10b"
PE32_x64 = "0x20b"
VS_VERSION_INFO_MAGIC = "0xfeef04bd0000"
VS_VERSION_INFO_ID = "VS_VERSION_INFO"


class VersionMatch(Enum):
    LOCAL_OLDER = 1
    LOCAL_NEWER = 2
    SAME_VERSION = 3
    FAIL = 4


class u8:
    fmt = "B"


class u16:
    fmt = "H"


class u32:
    fmt = "L"


class u64:
    fmt = "Q"


class i8:
    fmt = "b"


class i16:
    fmt = "h"


class i32:
    fmt = "l"


class i64:
    fmt = "q"


class PackedData:
    @classmethod
    def unpack(cls, data: BinaryIO):
        r = []
        for key, value in cls.__annotations__.items():
            if value == str:
                f = data.read(8).rstrip(b"\x00\x00").decode()
            else:
                fmt = endian + (value.fmt)
                size = struct.calcsize(fmt)
                f = struct.unpack(fmt, data.read(size))[0]
            r.append(f)
        return cls(*r)


@dataclass(slots=True, frozen=True)
class COFF_FILE_HDR(PackedData):
    machine_type: u16
    number_of_sections: u16
    timestamp: u32
    pointer_to_symbol_table: u32
    number_of_symbols: u32
    size_of_optional_header: u16
    characteristics: u16


@dataclass(slots=True, frozen=True)
class OPTIONAL_HDR_X86(PackedData):
    magic: u16
    major_linker_ver: u8
    minor_linker_ver: u8
    size_of_code: u32
    size_of_initialized_data: u32
    size_of_uninitialized_data: u32
    address_of_entry_point: u32
    base_of_code: u32
    base_of_data: u32


@dataclass(slots=True, frozen=True)
class OPTIONAL_HDR_X64(PackedData):
    magic: u16
    major_linker_ver: u8
    minor_linker_ver: u8
    size_of_code: u32
    size_of_initialized_data: u32
    size_of_uninitialized_data: u32
    address_of_entry_point: u32
    base_of_code: u32


@dataclass(slots=True, frozen=True)
class OPTIONAL_HDR_WIN_X86(PackedData):
    image_base: u32
    section_alignment: u32
    file_alignment: u32
    major_operating_system_version: u16
    minor_operating_system_version: u16
    major_image_version: u16
    minor_image_version: u16
    major_subsystem_version: u16
    minor_subsystem_version: u16
    win32_version_value: u32
    size_of_image: u32
    size_of_headers: u32
    checksum: u32
    subsystem: u16
    dll_characteristics: u16
    size_of_stack_reserve: u32
    size_of_stack_commit: u32
    size_of_heap_reserve: u32
    size_of_heap_commit: u32
    loader_flags: u32
    number_of_rva_and_sizes: u32


@dataclass(slots=True, frozen=True)
class OPTIONAL_HDR_WIN_X64(PackedData):
    image_base: u64
    section_alignment: u32
    file_alignment: u32
    major_operating_system_version: u16
    minor_operating_system_version: u16
    major_image_version: u16
    minor_image_version: u16
    major_subsystem_version: u16
    minor_subsystem_version: u16
    win32_version_value: u32
    size_of_image: u32
    size_of_headers: u32
    checksum: u32
    subsystem: u16
    dll_characteristics: u16
    size_of_stack_reserve: u64
    size_of_stack_commit: u64
    size_of_heap_reserve: u64
    size_of_heap_commit: u64
    loader_flags: u32
    number_of_rva_and_sizes: u32


@dataclass(slots=True, frozen=True)
class DATA_DIR(PackedData):
    virtual_address: u32
    size: u32


@dataclass(slots=True, frozen=True)
class SECTION_HDR(PackedData):
    name: str
    virtual_size: u32
    virtual_address: u32
    size_of_raw_data: u32
    pointer_to_raw_data: u32
    pointer_to_relocations: u32
    pointer_to_line_numbers: u32
    number_of_relocations: u16
    number_of_line_numbers: u16
    characteristics: u32


@dataclass(slots=True, frozen=True)
class RESOURCE_DIRECTORY_TABLE(PackedData):
    characteristics: u32
    timestamp: u32
    major_version: u16
    minor_version: u16
    number_of_name_entries: u16
    number_of_id_entries: u16


@dataclass(slots=True, frozen=True)
class RESOURCE_DIRECTORY_ENTRY(PackedData):
    """
    This field is either a string identifying a data leaf
    (if the high bit is set) or an ID to another nested directory
    (if the high bit is clear). The outermost level is always a
    directory. If it is a name, the lower 31 bits are the offset from the
    beginning of the resource section's raw data to the name
    (the name consists of 16 bits length and trailing wide characters,
    in Unicode, not 0-terminated).
    """
    name_or_id: u32
    data_or_subdir: u32


@dataclass(slots=True, frozen=True)
class RESOURCE_DATA_ENTRY(PackedData):
    data_rva: u32
    size: u32
    codepage: u32
    reserved: u32


@dataclass(slots=True, frozen=True)
class VS_VERSION_INFO_HDR(PackedData):
    size: u16
    value_length: u16
    value_type: u16


@dataclass(slots=True, frozen=True)
class DayZVersion:
    major: int
    minor: int
    patch: int


@dataclass(slots=True, frozen=True)
class FileVersion:
    major: int
    minor: int
    build: int
    revision: int


@dataclass(slots=True, frozen=True)
class Result:
    local: Union[str, None]
    remote: str
    build: str
    path: Union[Path, None]
    match: VersionMatch
    error: Union[Exception, None]


class PeFileError(Exception):
    """Expected contents missing from headers or resource nodes"""
    pass


class AppNotInstalledError(Exception):
    """App not present in user's libraryfolders"""
    pass


class AppMovedError(Exception):
    """VDF points to a nonexistent location on disk"""
    pass


class VDFLoadError(Exception):
    """Malformed VDF or JSON conversion"""
    pass


def parse_version_number(data: BinaryIO):
    # https://learn.microsoft.com/en-us/windows/win32/api/verrsrc/ns-verrsrc-vs_fixedfileinfo
    minor = struct.unpack("<L", data.read(4))[0] >> 16 & 0xffff
    major = struct.unpack("<L", data.read(4))[0] >> 0 & 0xffff
    build = struct.unpack("<L", data.read(4))[0] >> 0 & 0xffff
    revision = struct.unpack("<L", data.read(4))[0] >> 16 & 0xffff
    return FileVersion(major, minor, build, revision)


def seek_to_hex(address: str, data: BinaryIO) -> None:
    data.seek(int(address, base=16))


def seek_to_pe_stub(data: BinaryIO) -> None:
    MAGIC = "0x3c"
    seek_to_hex(MAGIC, data)
    e_lfanew = hex(struct.unpack("<h", data.read(2))[0])
    seek_to_hex(e_lfanew, data)
    pe_stub = data.read(4).rstrip(b"\x00\x00\x00\x00").decode()
    if pe_stub != "PE":
        raise PeFileError("missing PE header data")


def get_dayz_version(file: Path) -> DayZVersion:
    version = get_version(file)
    patch = str(version.build) + str(version.revision)
    dz_vers = DayZVersion(version.major, version.minor, int(patch))
    return dz_vers


def get_dayz_version_str(file: Path) -> str:
    v = get_dayz_version(file)
    concat = ".".join(str(el) for el in [v.major, v.minor, v.patch])
    return concat


def get_version(file):
    with open(file, "rb") as f:
        seek_to_pe_stub(f)
        COFF = COFF_FILE_HDR.unpack(f)

        pos = f.tell()
        blob = f.read()
        magic = hex(struct.unpack("<H", (blob[0:2]))[0])
        f.seek(pos)

        if magic == PE32_x86:
            OPTIONAL_HDR_X86.unpack(f)
            OBJW = OPTIONAL_HDR_WIN_X86.unpack(f)
        else:
            OPTIONAL_HDR_X64.unpack(f)
            OBJW = OPTIONAL_HDR_WIN_X64.unpack(f)

        if OBJW.number_of_rva_and_sizes < 1:
            raise PeFileError("no data resource directory")

        data_dirs = []
        for rva in range(OBJW.number_of_rva_and_sizes):
            data_dir = DATA_DIR.unpack(f)
            data_dirs.append(data_dir)

        res_dir = data_dirs[IMAGE_DIRECTORY_ENTRY]
        dir_va = res_dir.virtual_address

        for section in range(COFF.number_of_sections):
            hdr = SECTION_HDR.unpack(f)
            if hdr.name == RESOURCE_NODE:
                va = hdr.virtual_address
                ptr = hdr.pointer_to_raw_data
                offset = dir_va - va + ptr
                seek_to_hex(hex(offset), f)
                break

        if hdr.name != RESOURCE_NODE:
            raise PeFileError("no root resource node found")

        table = RESOURCE_DIRECTORY_TABLE.unpack(f)
        total = table.number_of_name_entries + table.number_of_id_entries

        for entry in range(total):
            entry = RESOURCE_DIRECTORY_ENTRY.unpack(f)
            if entry.name_or_id == VERSION_RESOURCE:
                while entry.data_or_subdir & (1 << 31):
                    shift = entry.data_or_subdir & ~(1 << 31)
                    seek_to_hex(hex(offset + shift), f)
                    table = RESOURCE_DIRECTORY_TABLE.unpack(f)
                    total = (
                            table.number_of_name_entries +
                            table.number_of_id_entries
                             )
                    for entry in range(total):
                        entry = RESOURCE_DIRECTORY_ENTRY.unpack(f)
                break
            if entry.name_or_id > VERSION_RESOURCE:
                raise PeFileError("no version info node found")
        seek_to_hex(hex(offset + entry.data_or_subdir), f)

        data = RESOURCE_DATA_ENTRY.unpack(f)
        # https://stackoverflow.com/questions/2170843/va-virtual-address-rva-relative-virtual-address
        offset = data.data_rva - hdr.virtual_address + hdr.pointer_to_raw_data
        seek_to_hex(hex(offset), f)

        hdr = VS_VERSION_INFO_HDR.unpack(f)
        # https://learn.microsoft.com/en-us/windows/win32/menurc/vs-versioninfo
        byte_len = len(VS_VERSION_INFO_ID.encode("utf-16le"))
        label = f.read(byte_len).decode("utf-16le")
        if label != VS_VERSION_INFO_ID:
            raise PeFileError(f"header identifier != '{VS_VERSION_INFO_ID}'")
        f.read(32 - byte_len)

        identifier = hex(struct.unpack("<Q", f.read(8))[0])
        if identifier != VS_VERSION_INFO_MAGIC:
            raise PeFileError(
                f"{VS_VERSION_INFO_ID} address != '{VS_VERSION_INFO_MAGIC}'"
            )

        try:
            version = parse_version_number(f)
        except Exception as e:
            return PeFileError(e)

        return version


def is_older_version(local: str, remote: str) -> bool:
    return Version(local) < Version(remote)


def is_newer_version(local: str, remote: str) -> bool:
    return Version(local) > Version(remote)


def get_pefile_path(path: str, appid: int) -> Path:
    binary = "DayZ_x64.exe"
    identifier = {221100: "DayZ", 1024020: "DayZ Exp"}
    name = identifier[appid]

    pe_path = None
    path = path + "/steamapps/libraryfolders.vdf"

    with open(path, "r") as f:
        try:
            j = json.loads(vdf_to_json(f))
        except Exception:
            raise VDFLoadError("Failed to parse libraryfolders")

        for obj in j["libraryfolders"]:
            if str(appid) in j["libraryfolders"][obj]["apps"]:
                pe_path = j["libraryfolders"][obj]["path"]
                pe_path += f"/steamapps/common/{name}/{binary}"
                break

    if pe_path is None:
        raise AppNotInstalledError(
            f"Failed to find a libraryfolder for the appid '{appid}'"
        )

    pe_path = Path(pe_path)
    if pe_path.exists() is False:
        raise AppMovedError(
            f"Path '{pe_path}' specified in libraryfolders does not exist"
        )

    return pe_path


def compare_versions(remote: str, appid: int, path: str):
    if appid == 221100:
        build = "DayZ"
    else:
        build = "DayZ Experimental"

    local = None
    pe_filepath = None
    error = None

    try:
        pe_filepath = get_pefile_path(path, appid)
    except Exception as e:
        return Result(
            local, remote, build, pe_filepath, VersionMatch.FAIL, e
        )

    try:
        local = get_dayz_version_str(pe_filepath)
    except PeFileError:
        return Result(
            local, remote, build, pe_filepath, VersionMatch.FAIL, error
        )

    if is_older_version(local, remote):
        res = VersionMatch.LOCAL_OLDER
    elif is_newer_version(local, remote):
        res = VersionMatch.LOCAL_NEWER
    else:
        res = VersionMatch.SAME_VERSION

    return Result(local, remote, build, pe_filepath, res, error)


def vdf_to_json(stream):
    def _istr(indent, string):
        return (indent * '  ') + string

    jbuf = '{\n'
    lex = shlex(stream)
    indent = 1

    while True:
        tok = lex.get_token()
        if not tok:
            return jbuf + '}\n'
        if tok == '}':
            indent -= 1
            jbuf += _istr(indent, '}')
            ntok = lex.get_token()
            lex.push_token(ntok)
            if ntok and ntok != '}':
                jbuf += ','
            jbuf += '\n'
        else:
            ntok = lex.get_token()
            if ntok == '{':
                jbuf += _istr(indent, tok + ': {\n')
                indent += 1
            else:
                jbuf += _istr(indent, tok + ': ' + ntok)
                ntok = lex.get_token()
                lex.push_token(ntok)
                if ntok != '}':
                    jbuf += ','
                jbuf += '\n'
