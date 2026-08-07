# Fantasy Tennis client reverse-engineering notes

Captured 2026-08 during Content Studio work. Source of truth is the stock Linux client under `JFTSE/.jftse-client-linux/client`.

## Binaries

| File | Notes |
|------|--------|
| `FantaTennis.exe` | PE32 GUI, Direct3D9 fixed-function pipeline (D3DTSS_*, D3DFVF_* strings) |
| `jftse.dll` | PE32 DLL (emulator companion) |
| `FT_Launcher.exe` | .NET launcher |

## Crypto (ft_restool Crypter)

| Format | Algorithm |
|--------|-----------|
| `.set` scripts | AES-128-ECB, key `TIMOTEI_ZION\0\0\0\0`, first byte = pad/null identifier |
| `.tex` textures | XOR `0xFF` on first 128 bytes (full-file XOR also yields valid DDS) |

Implementation: `python/client_crypto.py`, `mesh_codec.decrypt_tex_to_dds`.

## Stage scripts (`Res/Stage/Info.res`)

After AES decrypt, INI-like text, e.g. `1_Emerald_Beach.set`:

- `WorldFile` / `World_Chat` → stage court DAT path
- `SkyFile`, `Collision`, `Coll_Chat`
- `ShadowColor`, `SkyColor`, fog, camera names, end-present cams

API: `GET /api/stage-set/decrypt?member=1_Emerald_Beach.set`

## Mesh DAT (`Res/Stage/MeshNN.res` members)

- Header: 12× uint32 LE
- Dense float3 runs (interleaved pos/normal/UV at stride 12–32)
- Vertex recovery: multi-stride score (reject cube noise, unit normals, UV false runs)
- Index recovery: **score u16 runs by solid triangle area × coverage** (not first long run)
  - BF_Court01: ~582 solid tris, ~39% vertex coverage (was ~322 / 15%)
- UVs: interleaved when stride ≥20, else planar XZ projection
- Materials: stock stage `.tex` via prefix (e.g. `BF_Lawn00_A.tex`)

## Equipment mesh catalog (`Res/Script/Item.res` → `Info_Item_Mesh.set`)

AES → UTF-8 XML:

```xml
<Item Char="NIKI" Index="214" Path="Res/Player/PlayerA/Item07/Niki_CommonRacket41.dat" Desc="드래곤 슬레이어"/>
```

Shop item `mesh` field is this `Index`. 1921 entries across characters.

API: `GET /api/item-mesh/resolve?meshIndex=214&char=NIKI`

Player archives: `Res/Player/Player{A-G}/ItemNN.res` + `Mesh.res` body meshes.

## Honest limits

- Not a full Ghidra/DX9 renderer; topology still best-effort index recovery
- Racket preview is mesh decode + optional co-located tex, not bone-attached Equipment
- Multi-material stage layers (lawn+coat+mark+LM) not fully bound from DAT materials tables
