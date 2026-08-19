import os, signal

pids = [25428, 19580, 28468]
for pid in pids:
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Killed {pid}")
    except ProcessLookupError:
        print(f"Process {pid} not found")
    except Exception as e:
        print(f"Error killing {pid}: {e}")
print("Done")
