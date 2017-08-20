import sqlite3
import numpy as np
import hashlib

# Create table
arrsize = 192

def initialize(c):
    arr_fields = []
    for i in range(0, arrsize):
        arr_fields.append("s%d real"%(i))
    fieldstr = ", ".join(arr_fields)

    c.execute('CREATE TABLE IF NOT EXISTS summaries(filename text primary key, '+fieldstr + ')')
    c.execute('CREATE TABLE IF NOT EXISTS badfiles(filename text primary key)')

def hash(filename):
    return hashlib.sha256(bytes(filename, encoding = 'utf-8')).digest()

def update(new_files, summaries, bad_files):
    conn = sqlite3.connect('cache.db')
    c = conn.cursor()
    initialize(c)

    field_str = "INSERT OR IGNORE INTO summaries VALUES (?"+ ", ?"*arrsize +")"

    for filename in new_files:
        list_summary = summaries[filename].tolist()
        values = [filename] + list_summary
        c.execute(field_str, (values))

    for filename in bad_files:
        c.execute("INSERT OR IGNORE INTO badfiles VALUES (?)", (filename,))

    conn.commit()

    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()

def load(files):
    conn = sqlite3.connect('cache.db')
    c = conn.cursor()
    summaries = {}
    bad_files = set([])

    found = 0
    missed = 0
    try:
        for f in files:
            c.execute("SELECT * FROM summaries WHERE filename=?", (f,))
            vals = c.fetchone()
            if not vals is None:
                summary_vals = vals[1:]
                summaries[f] = np.array(summary_vals)
                found = found + 1
            else:
                # Check if this is known to be missing.
                c.execute("SELECT * FROM badfiles WHERE filename=?", (f,))
                vals = c.fetchone()
                if vals is None:
                    missed = missed + 1
                else:
                    bad_files.add(f)

        print("Found %d, missed %d, bad %d" % (found, missed, len(bad_files)))
    except sqlite3.OperationalError as e:
        pass

    return summaries, bad_files
