# ResTool compatibility fixtures

These are tiny synthetic fixtures, not extracted game assets. They were authored for this repository and checked on 2026-08-09 with the public APIs in `oracle/CompatibilityOracle.java` under Java 21. Oracle work is materialized only in a disposable directory. No proprietary JAR is copied into the repository.

The read-only oracle clients are:

- `/home/thewind/Downloads/ft_restool.jar`
- `/home/thewind/Downloads/ft_restool (1).jar`

Both clients have SHA-256 `590ccfa6d88e0e7ae5af864af212543ec41342197603fd183f782315e3b0402f`. The harness is intentionally limited to `FTMParser.parse/store/fromJson/toJson`, `PRJReader.read/write`, and `Crypter` SET/TEX in-memory methods.

## Repository fixture hashes

| File | SHA-256 |
| --- | --- |
| `manifest.json` | `5ab26638f8035556260a5b77085bec6d3810d99803dc6a9270ecc158027c74b2` |
| `sample.ftm.b64` | `7e90c5ee977ae98c449dd775ba58770ee726899d38af1a809df2a22c9990cf33` |
| `sample.ftm.json` | `960d1277d48ad71fb0b49fa4320c5ada00caf464bdb82f111ca0f6e3ab5873f8` |
| `sample.prj.b64` | `354eb1f65a1ff0ba9b25a099ec4b922b26272e268806f5039f4b7ef8346a3751` |
| `set.plain.txt` | `ee07098f4f2930d4169d7a14b739b0e7c510642495431626b47f8d1ac24353c7` |
| `tex.dds.b64` | `450116be076be9f6a693ca504c22afe564997f6f2eb5877754d49e89c921f8b7` |
| `tex.encoded.b64` | `3c681cfb2a518f44d8431887e7e24bb22362ae29f0a1fbea48ddf77a1fc82ac1` |
| `oracle/CompatibilityOracle.java` | `92ea291548f67c00a95e707ddaa6ad92ab1b0b41be5a1b86d07576e6a75ff611` |

Decoded FTM and PRJ hashes are recorded separately in `manifest.json`. Compatibility claims are fixture-bounded: arbitrary assets and live-client acceptance remain explicitly unproven.
