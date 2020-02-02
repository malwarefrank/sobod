import os
import pytest
from sobod import SOBFile, SOBFlags

TESTDIR = "test_data"
TESTFILE = os.path.join(TESTDIR, "file1.sob")


def test_create():
    if not os.path.exists(TESTDIR):
        os.makedirs(TESTDIR)
    sob = SOBFile(TESTFILE, mode="w")
    sob.itemsize = 5
    sob.append(b"cccc\x02")
    sob.append(b"bbbb\x05")
    sob.append(b"dddd\x2a")
    sob.append(b"aaaa\x01")
    sob.close()


def test_load():
    sob = SOBFile(TESTFILE)
    assert sob.sorted == False
    assert sob.itemsize == 5
    assert len(sob) == 4
    assert sob[0] == b"cccc\x02"
    assert sob[-1] == b"aaaa\x01"
    assert sob.count(b"cccc\x02") == 1
    assert sob.index(b"bbbb\x05") == 1
    sob.close()
    assert sob.closed


def test_sort():
    sob = SOBFile(TESTFILE, mode="a")
    sob.sort()
    assert sob.sorted
    assert sob.index(b"aaaa\x01") == 0


def test_context_manager():
    with SOBFile(TESTFILE) as sob:
        assert sob.closed == False
        assert sob.sorted
        assert sob.index(b"aaaa\x01") == 0
    assert sob.closed

def test_exceptions():
    with SOBFile(TESTFILE) as sob:
        with pytest.raises(NotImplementedError):
            sob.insert(2, b"eeee\x0e")
        with pytest.raises(NotImplementedError):
            del sob[2]
        with pytest.raises(NotImplementedError):
            # __getitem__ slice
            x = sob[1:3]
        with pytest.raises(NotImplementedError):
            # __setitem__ slice
            sob[3:6] = [b"ffff\x0f", b"gggg\x10", b"hhhh\x11"]
        with pytest.raises(TypeError):
            sob["frank"]
        with pytest.raises(IndexError):
            x = sob[100]
        with pytest.raises(IndexError):
            x = sob[-100]
        with pytest.raises(ValueError):
            x = sob.index(b"abcde")

def test_clear():
    with SOBFile(TESTFILE, mode="a") as sob:
        sob.clear()
        assert len(sob) == 0
        hsize = sob.headersize
    sob.close()
    assert os.path.getsize(TESTFILE) == hsize
