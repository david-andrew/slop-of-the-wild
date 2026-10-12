# Round 65 defect hunt

Base `932b6a4`, `sol/work`. Run `python3 tools/defect_hunt_check.py`.
The harness extracts production cooking/pickup callbacks and scripts physical
input through production gameplay code. All 22 save scenarios use separate
writer/reader processes and native-close `save_update`. Reproductions and logs
remain under ignored `build/round65*`.

## Defects fixed

- **Lost dropped inventory.** Equip a Sword, drop with Inventory/X, quit,
  reload: it is absent from inventory and ground. Shock, throw and held releases
  also failed. Optional validated save records now preserve these drops, motion
  and material state. Regressions verify one pickup, subsequent save removal,
  duplicate-free restore and two identical peppers. Projectile damage cannot replay.
- **Lost encounter rewards.** Kill a Bokoblin and quit during its death, or
  leave its dropped weapon unclaimed, then reload: the camp stays defeated but
  its reward disappears. Rewards now spawn once at accepted death, before the
  defeat autosave, and persist. Both fresh-process regressions verify exactly one
  weapon, including after the corpse disappears.
- **Disconnected pad releases attacks.** Hold RT until a bow is drawn, then
  disconnect: an arrow fires. Hold X through a sword swing into charge, then
  disconnect: a spin starts. Both now cancel. A regression also disconnects while
  Inventory pauses aim, waits three updates, then resumes; disconnect stays
  pending until gameplay consumes it.
- **Surfing without a shield.** Start a surf, open Inventory, drop the sole
  shield, resume: Link still surfs. Equipment revalidation now ends the ride
  immediately. Regressions cover ground/airborne surf, unequipping and replacement.

## Passed clean

- Mid-glide, cliff/Talus climb and swim reload at safe anchors; held ingredients
  return to inventory; cooking retains one dish; burning retains its timer.
- Interrupted title crane and tower rise restore control; the tower completes
  at its foot. Orb saves before/after the award preserve atomic reward state and
  resume outside. First skip is ignored; repeat skip follows the award.
- A moved shrine crate pressing a plate resumes outside the reset puzzle;
  pushing cannot cross its boundary. Night skeletons emerge after reload and
  retreat at dawn. Floating/downhill logs retain position, roll, wetness and support.
- Full inventory leaves a pickup available; consumed last food cannot be bound;
  equipping preserves glide; opposed movement cancels; occupied rebinding swaps.
  Indoor weather changes and a pending equipped lightning warning are harmless
  in Keh Namut. Legacy saves and malformed drop-record rejection pass.

**26 runtime checks and 22 writer/reader scenarios pass.** Sleeping and fast
travel are absent. Crate probes use collision fixtures and production puzzle
transactions; the usual checks cover all four complete shrine routes.

## Validation

All usual 20 pass: feel, fauna, element test/check, save/isolation, integration,
input, combat, camera, title handoff, journey controller, prepared-assets
equivalence, four shrine routes, late story, traversal (headless), slots, four
shrine exits, passage, opening and occluder. The affected CPU checks were rerun
after the encounter-reward fix. Status-save, encounter/weather-save and Talus
save/element integration also pass. Final results/logs: `build/round65-checks/`
(`summary-final.txt`, `cpu-final-summary.txt`, `*-final.log`); new hunt:
`build/round65-defects-final.log`.

The opening fixture originally ended at frame 3980, 28 frames before its control
handoff; its horizon is now 4300, with the same route and
checkpoint assertions. This overlaps Sol2's `tools/opening_check.sh` adjustment.
Renders acquire `/tmp/botw-render.lock` once; self-locking scripts use their own lock. No music,
cave-rock, forest-floor-colour or brushwork/grain files changed.
