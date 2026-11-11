BOTW 4:3 native UI build tools

Build : python -I tools/build.py "<dump>/01007EF00011E000/romfs" <out_dir>
Verify: python -I tools/verify.py "<dump>/01007EF00011E000/romfs" <out_dir>      (must print FAILS: 0)

<out_dir> must be an empty folder outside the repo with Layout/ and Pack/ subfolders; the build writes only the archives it
changes plus build_report.json (verify reads it). Full command list, environment variables and the copy step into
mod/: see ../AGENTS.md. History of each rule: ../docs/DEVELOPMENT.md.

build.py    applies the rules to the original layouts (float overwrites in place; SARC/Yaz0 rebuilt)
curated.py  every per-layout decision (the only file most fixes touch)
rules.py    shared geometry (1280x720 layouts, 4:3: factor 0.75, visible half-height 480, edge shift 120)
lyt.py      SARC / Yaz0 / BFLYT / BFLAN reader that records byte offsets
verify.py   re-derives every rule from the originals and checks the output (checks 0-22)
mkpatch.py  emits a cave-based exact-4:3 patch; NOT what ships (the shipped patch is hand-edited/exefs/1.6.0.pchtxt)
hand-edited/exefs/1.6.0.pchtxt   the shipped code patch, copied into the mod folder as is
