import subprocess, os
os.chdir(r"c:\Users\aslan\Desktop\Product Builder-app\versiontest with cadquery\ai-cadquery")

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip()

out, _ = run(["git", "remote", "-v"])
print(f"REMOTE:\n{out}\n")

out, _ = run(["git", "log", "--oneline", "-5"])
print(f"RECENT COMMITS:\n{out}\n")

out, _ = run(["git", "status", "-sb"])
print(f"STATUS:\n{out}\n")

out, err = run(["git", "push", "--dry-run", "origin", "master"])
print(f"PUSH DRY-RUN stdout:\n{out}")
print(f"PUSH DRY-RUN stderr:\n{err}")
