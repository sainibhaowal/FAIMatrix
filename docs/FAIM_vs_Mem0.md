So each “node” is not just a dumb DB row. It’s:

payload + meta + fractal vector + parent links + antisym merge + indices + journal entry.

a faster storage backend (Postgres/RocksDB/etc.),

or moving hot loops to compiled code (Rust/C++/Cython).