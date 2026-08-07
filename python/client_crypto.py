"""Fantasy Tennis client crypto helpers (from ft_restool Crypter RE).

AES-128-ECB key TIMOTEI_ZION\\0\\0\\0\\0 for .set script files.
XOR 0xFF (first 128 or full) for .tex → DDS (see mesh_codec.decrypt_tex_to_dds).
"""

from __future__ import annotations

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

AES_SET_KEY = b"TIMOTEI_ZION\x00\x00\x00\x00"


def decrypt_set_file(raw: bytes) -> bytes:
    """Decrypt a stock .set blob to plaintext (XML or INI).

    Layout (ft_restool Crypter.decryptSetFileInMemory):
      byte0 = nullCountIdentifier
      byte1.. = AES-128-ECB ciphertext (padded to 16 with zeros for decrypt)
    """
    if len(raw) < 17:
        raise ValueError("SET_TOO_SMALL")
    null_id = raw[0]
    body = raw[1:]
    pad = (16 - (len(body) % 16)) % 16
    buf = body + (b"\x00" * pad)
    decryptor = Cipher(algorithms.AES(AES_SET_KEY), modes.ECB()).decryptor()
    out = decryptor.update(buf) + decryptor.finalize()
    size = len(out) - pad - null_id
    if size <= 0:
        size = len(out)
    return out[:size]


def encrypt_set_file(plain: bytes) -> bytes:
    """Encrypt plaintext to .set (mirror of restool encrypt path)."""
    size = len(plain)
    null_count = (16 - (size % 16)) % 16
    if null_count == 0:
        null_count = 16
    buf = plain + (b"\x00" * null_count)
    encryptor = Cipher(algorithms.AES(AES_SET_KEY), modes.ECB()).encryptor()
    data = encryptor.update(buf) + encryptor.finalize()
    return bytes([null_count]) + data
