Sequence of Bytes on Disk
=========================

A collection of disk-backed sequences.

- SOBFile


Install
-------

```bash
pip install .
```


Example
-------

```python
from sosod import SOBFile, SOBFlags

with SOBFile("myfile", "a") as sob:
    sob.itemsize = 4
    sob.append(b"efgh")
    sob.append(b"abcd")
    sob.append(b"ijkl")
    print(sob[0])           # b'efgh'
    sob.index(b"ijkl")      # 2
    len(sob)                # 3

    # Searching a sorted SOBFile is more efficient. It
    # implements a binary search.
    sob.sort()
    sob.index(b"efgh")



SOBFile
-------

A Sequence of Bytes file contains a sequence bytes items, where
each item is the same size.
