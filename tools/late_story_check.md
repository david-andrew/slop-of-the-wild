Run `tools/late_story_check.sh` from any directory. This headless regression runs the production story, shrine, player, element and camera updates at 60 Hz. It has a 90-second wall-time limit and isolates inherited `BOTW_*` / `SLOPPY_*` switches. It never opens a window or accesses saves.

The check asserts these events in order:

- The old man's campfire greeting, cold damage, cooking spicy steak, exchanging it for the Warm Doublet, and protection from cold.
- Tower activation, its animated rise, shrine reveal, restored control and camera, and the old man gliding to the tower's foot.
- Each shrine's exterior activation and lift, monk interaction, one earned orb, completed-shrine flag, return lift, restored camera and HUD. Exactly four orb awards must appear in the log.
- The old man appearing on the Temple of Thyme roof, no remote paraglider reward, the roof meeting, gift, farewell, and restored control.
- Opening the gifted paraglider, leaving the Plateau, the leaving title appearing and finishing without restarting.

Overland positions, cooking ingredients, a cooking-pot fixture and solved shrine interiors are test fixtures. Story progression, tower activation, orb counts, completion flags and the glider reward are never preset. `shrine_route_check.sh` covers the full puzzle routes separately. Cooking, pot registration, the Give callback and their per-frame availability rules are extracted verbatim from `main.jo` into the generated harness, which fails explicitly if its source anchors change.

The full event trail is `build/late-story-check/run.log`; the generated Sloppy source is `build/late-story-check/harness.jo`. The runner builds from `tools/late_story.jo.in`, whose imports are relative to that generated location.

Run `sloppy/bin/sloppy tools/wake_contact_check.jo` for the accompanying palm-contact regression. It measures both hero models through the entire wake: pinned wrist drift, palm tilt, bent-arm reach, lift-off clearance, and maximum per-frame joint displacement. `opening_test.jo` complements it with interrupted camera handoff checks; `opening_check.sh` supplies the continuous rendered opening.
