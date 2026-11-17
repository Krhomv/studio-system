stamp: 2026-11-17T18:29   (NOT final: the handover call decides)
accepted: AUD-02 wind loop = user ACCEPTED on the board 2026-11-17 17:29 ("Accept.")
already live: nothing
apply tonight:
 1. AUD-02: python studios/audio/staged/aud02/install.py            (dry run: 1 file would change)
    python studios/audio/staged/aud02/install.py --apply            (backup in studios/audio/backup/<stamp>/)
    revert: python studios/audio/staged/aud02/install.py --revert <stamp>
check: play the open field for 2 min: no click at the loop point; the loop length is unchanged (41.0 s).
worse looks like: a gap of silence, or the wind louder than before.
not ready: AUD-01 (rework, not accepted)
