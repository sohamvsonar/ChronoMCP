import h5py
import numpy as np

# Path to your HDF5 file
fname = '/home/ssonar/chronolog/Debug/output/chatgpt.cake.1746510240.vlen.h5'

new_ts = 1732752000000000000
with h5py.File(fname, 'r+') as f:
    ds = f['story_chunks/data.vlen_bytes']
    # Load into memory
    records = ds[:]
    # Modify the eventTime column (for all entries, or only index 0):
    records['eventTime'] = new_ts
    # Write the modified array back to the dataset
    ds[:] = records
    # Flush to disk
    f.flush()
print("eventTime updated successfully.")
