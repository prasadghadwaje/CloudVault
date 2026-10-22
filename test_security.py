
from pathlib import Path

from file_security import split_encrypt_file, decrypt_reassemble

original = Path("uploads/sample.txt")
original.parent.mkdir(exist_ok=True)
original.write_text(
    "CloudVault secure storage test. " * 5000,
    encoding="utf-8"
)

manifest = split_encrypt_file(original, block_size=4096)
print("Encrypted blocks:", len(manifest["blocks"]))

recovered = decrypt_reassemble(
    "encrypted_blocks/sample.txt.manifest.json",
    "uploads/recovered_sample.txt"
)

if original.read_bytes() == recovered.read_bytes():
    print("SUCCESS: File recovered and verified!")
else:
    print("ERROR: Recovered file differs from the original.")
