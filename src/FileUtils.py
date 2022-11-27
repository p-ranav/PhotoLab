import os
import glob

def split_file(path, chunk_size=50000000):
    file_number = 1
    filename = os.path.basename(path)
    with open(path, 'rb') as f:
        chunk = f.read(chunk_size)
        while chunk:
            with open(os.path.join(os.path.dirname(path), filename + ".part" + str(file_number)), 'wb') as chunk_file:
                chunk_file.write(chunk)
            file_number += 1
            chunk = f.read(chunk_size)

def merge_files(prefix, dirname):
    '''
    Each file has a .part<num> suffix

    prefix: The name of the output merged file
    dirname: Directory containing the split files to be merged

    This function will find all the parts and merge them
    '''
    files = glob.glob(os.path.join(dirname, prefix) + "*")
    files = list(files)

    files_sorted = []
    for i in range(1, len(files) + 1):
        part_filename = prefix + ".part" + str(i)
        if os.path.exists(os.path.join(dirname, part_filename)):
            files_sorted.append(os.path.join(dirname, part_filename))

    mergedBytes = b''
    for fn in files_sorted:
        with open(fn, 'rb') as fp:
            mergedBytes += fp.read()

    with open(os.path.join(dirname, prefix), 'wb') as fp:
        fp.write(mergedBytes)