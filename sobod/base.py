import os
import bisect
import struct
from enum import IntFlag
from typing import Tuple, Optional, Iterator
from collections.abc import MutableSequence

from .util import quickSort as _quickSort


class SOBError(Exception):
    pass


class SOBFlags(IntFlag):
    SORTED = 1


class SOBFile(MutableSequence):
    MAGIC = b"SOB\x00\x00\x00\x00\x00"
    MIN_HEADER_SIZE = 32
    # HEADER FIELDS OFFSETS
    OFFSET_SIZEOF_HEADER = len(MAGIC)
    OFFSET_FLAGS = OFFSET_SIZEOF_HEADER + 4
    OFFSET_SIZEOF_ITEM = OFFSET_FLAGS + 4

    def __init__(self, filepath: str, mode: str = "r", cachesize: int = 10240):
        self._path = None
        self._sorted = False
        self._cachesize = cachesize
        self._cache = dict()
        self._closed = True
        self._headersize = self.MIN_HEADER_SIZE
        self._flags = SOBFlags(0)
        if filepath:
            self.open(filepath, mode)

    def parse_header(self) -> Tuple[int, SOBFlags, int, int, bytes]:
        """Parse the file header.
           Returns header size, flags, item size, #of items,
           and a raw copy of the header.
        """
        self._fh.seek(0)
        buf = self._fh.read(self.MIN_HEADER_SIZE)
        if buf[: len(self.MAGIC)] != self.MAGIC:
            raise TypeError("Invalid header (MAGIC value)")
        h_size = struct.unpack_from("<I", buf, offset=self.OFFSET_SIZEOF_HEADER)[0]
        i_size = struct.unpack_from("<I", buf, offset=self.OFFSET_SIZEOF_ITEM)[0]
        flags = struct.unpack_from("<I", buf, offset=self.OFFSET_FLAGS)[0]
        # read rest of header
        if h_size > self.MIN_HEADER_SIZE:
            buf += self._fh.read(h_size - self.MIN_HEADER_SIZE)
        # check for truncation
        fsize = self._fh.seek(0, os.SEEK_END)
        if (fsize - h_size) % i_size != 0:
            raise SOBError("Truncated file".format(self._path))
        num_items = (fsize - h_size) / i_size
        # header size, flags, item size, #of items, raw header
        return h_size, SOBFlags(flags), i_size, int(num_items), buf

    ##################################################################
    ## Getters and setters

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def itemsize(self) -> int:
        return self._itemsize

    @itemsize.setter
    def itemsize(self, value: int):
        if not isinstance(value, int):
            raise TypeError(type(value))
        if len(self) != 0:
            raise SOBError("Item size cannot be changed")
        self._itemsize = value
        self._fh.seek(self.OFFSET_SIZEOF_ITEM)
        self._fh.write(struct.pack("<I", value))

    @property
    def headersize(self) -> int:
        return self._headersize

    @headersize.setter
    def headersize(self, value: int):
        if not isinstance(value, int):
            raise TypeError(type(value))
        if len(self) != 0:
            raise SOBError("Header size cannot be changed")
        if value < self.MIN_HEADER_SIZE:
            raise ValueError("value must be >= {}".format(self.MIN_HEADER_SIZE))
        if not self.closed:
            # grow or shrink file
            self._fh.truncate(value)
        self._headersize = value
        self._fh.seek(self.OFFSET_SIZEOF_HEADER)
        self._fh.write(struct.pack("<I", value))

    @property
    def flags(self) -> SOBFlags:
        return self._flags

    def set_flags(self, value):
        if not isinstance(value, SOBFlags):
            raise TypeError("expected {}, got {}".format(SOBFlags, type(value)))
        if value in self._flags:
            return
        self._flags |= value
        self._fh.seek(self.OFFSET_FLAGS)
        self._fh.write(struct.pack("<I", self._flags))

    def unset_flags(self, value):
        if not isinstance(value, SOBFlags):
            raise TypeError("expected {}, got {}".format(SOBFlags, type(value)))
        if value not in self._flags:
            return
        self._flags &= ~value
        self._fh.seek(self.OFFSET_FLAGS)
        self._fh.write(struct.pack("<I", self._flags))

    @property
    def sorted(self) -> bool:
        return SOBFlags.SORTED in self.flags

    ##################################################################
    ## Mutable Sequence

    ####################
    ### Abstract methods

    def __getitem__(self, key) -> bytes:
        if isinstance(key, slice):
            # TODO
            raise NotImplementedError("slicing not (yet) implemented")
            # inefficient but simple
            step = 1 if key.step is None else key.step
            return [self[index] for index in range(key.start, key.stop, step)]
        elif isinstance(key, int):
            if key in self._cache:
                item = self._cache[key]
                return item
            item_offset = key * self.itemsize
            if key >= 0:
                if key >= self._len:
                    raise IndexError(key)
                self._fh.seek(self.headersize + item_offset)
                buf = self._fh.read(self.itemsize)
            else:
                if key * -1 >= self._len:
                    raise IndexError(key)
                # offset from end
                self._fh.seek(item_offset, os.SEEK_END)
                buf = self._fh.read(self.itemsize)
            return buf
        else:
            raise TypeError()

    def __setitem__(self, key, buf: bytes):
        if isinstance(key, slice):
            # TODO
            raise NotImplementedError("slicing not (yet) implemented")
        if not isinstance(key, int):
            raise TypeError("key is not int")
        if not isinstance(buf, bytes):
            raise TypeError("buf is not bytes")
        if len(buf) != self.itemsize:
            raise TypeError(
                "len(buf)={} but itemsize={}".format(len(buf), self.itemsize)
            )
        # pack item
        item_offset = key * self.itemsize
        if key >= 0:
            if key >= self._len:
                raise IndexError()
            self._fh.seek(self.headersize + item_offset)
        else:
            if key * -1 >= self._len:
                raise IndexError()
            # offset from end
            self._fh.seek(item_offset, os.SEEK_END)
        # write data
        self._fh.write(buf)
        if self.sorted:
            # TODO: check
            self.unset_flags(SOBFlags.SORTED)

    def __len__(self) -> int:
        return self._len

    def __delitem__(self, index: int):
        raise NotImplementedError()

    def insert(self, index: int, value: bytes):
        raise NotImplementedError()

    ###################
    ### Other Overidden

    def append(self, buf: bytes):
        if not isinstance(buf, bytes):
            raise TypeError("buf is not bytes")
        if len(buf) != self.itemsize:
            raise TypeError(
                "len(buf)={} but itemsize={}".format(len(buf), self.itemsize)
            )
        self._fh.seek(0, os.SEEK_END)
        self._fh.write(buf)
        self._len += 1
        if self.sorted:
            # TODO check
            self.unset_flags(SOBFlags.SORTED)

    def clear(self):
        self._fh.truncate(self.headersize)
        self._len = 0
        self._cache.clear()

    def index(self, buf: bytes, start=0, end=None) -> Optional[int]:
        """Return index of item or None."""
        if end is None or end < start:
            end = len(self)
        if not self.sorted:
            # linear search :(
            for i in range(start, end):
                item = self[i]
                if item == buf:
                    return i
            raise ValueError()
        # sorted, binary search
        x = self._sorted_find(buf, start, end)
        if x is None:
            raise ValueError()
        return x

    ## Mutable Sequence
    ##################################################################

    def open(self, filepath: str, mode: str):
        self._path = filepath
        if mode == "r":
            self._fh = open(filepath, "rb")
            (
                self._headersize,
                self._flags,
                self._itemsize,
                self._len,
                _,
            ) = self.parse_header()
        elif mode == "w":
            self._fh = open(filepath, "wb")
            # write header
            self._fh.write(self.MAGIC)
            self._fh.write(b"\x00" * (self.headersize - len(self.MAGIC)))
            # number of entries = 0
            self._len = 0
            # this causes headersize to be written to header on disk
            self.headersize = self.headersize
        elif mode == "a":
            self._fh = open(filepath, "rb+")
            (
                self._headersize,
                self._flags,
                self._itemsize,
                self._len,
                _,
            ) = self.parse_header()
        else:
            raise SOBError("Unknown mode '{}'".format(mode))
        self._closed = False

    def close(self):
        self._fh.close()
        self._closed = True

    def fill_cache(self):
        self._fill_cache()

    def sort(self, key=None):
        _quickSort(self, 0, len(self) - 1, key)
        self.set_flags(SOBFlags.SORTED)

    def __enter__(self):
        return self

    def __exit__(self, typ, value, traceback):
        self.close()

    def _bisect_indexes(
        self, lo: int = 0, hi: Optional[int] = None, iterations: int = 1024
    ) -> Iterator[int]:
        if int(iterations) == 0 or hi == lo:
            return
        # This algorithm is copied from the CPython src for bisect
        if lo < 0:
            raise ValueError("lo must not be negative")
        if hi is None:
            hi = len(self)
        if hi < lo:
            raise ValueError(f"{hi} < {lo}")
        mid = (lo + hi) // 2
        yield mid
        iterations -= 1
        odd = iterations % 2
        # down
        yield from self._bisect_indexes(lo, mid, (iterations - odd) / 2)
        # up
        yield from self._bisect_indexes(mid + 1, hi, (iterations + odd) / 2)

    def _fill_cache(self):
        if self._cachesize and self._cachesize > 0:
            if self.sorted:
                # cache values for binary search
                for i in self._bisect_indexes(iterations=self._cachesize):
                    self._cache[i] = self[i]
            else:
                # cache values for linear search
                for i in range(self._cachesize):
                    self._cache[i] = self[i]

    def _sorted_find(self, value: bytes, start: int, end: int):
        """Locate the first (leftmost) entry"""
        i = bisect.bisect_left(self, value, start, end)
        item = self[i]
        if i != len(self) and item == value:
            return i
        return None
