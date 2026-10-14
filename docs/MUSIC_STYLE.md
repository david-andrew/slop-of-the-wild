# Breath of the Wild music: a composition brief for original music in the style

Purpose: a guide for writing original music in the style of BotW, for a parody game. Describe and imitate the techniques; never reuse BotW melodies note for note.

**How the sources were gathered.** YouTube blocks plain caption downloads (empty `timedtext` responses), and `yt-dlp` was not installed. I got the full auto-generated transcripts of all four 8-bit Music Theory (8BMT) videos from YouTube's own transcript panel, through a headless browser:
- Part 1, Hyrule Field: https://www.youtube.com/watch?v=tl-6K3zrcr0
- Part 2, Main Theme: https://www.youtube.com/watch?v=F6YaK8bOvWY
- Part 3, Kakariko Village: https://www.youtube.com/watch?v=xZBodzjVSjA
- Part 4, Hyrule Castle: https://www.youtube.com/watch?v=nUoophDioZA

I got transcripts the same way for:
- Scruffy, "invisible design": https://www.youtube.com/watch?v=Vgev9Gzybk8
- Nomax, shrine music: https://www.youtube.com/watch?v=6logXysLpNk
- GMTK, "The Music of BotW": https://www.youtube.com/watch?v=3FWVKu1gnWs
- pixeltea: https://www.youtube.com/watch?v=K3wYxjbhqx0
- Jack Schooley: https://www.youtube.com/watch?v=wVp24yyq120
- Kevin Armes: https://www.youtube.com/watch?v=YBFogpYHpco
- jazzbandit: https://www.youtube.com/watch?v=qMcQGBH-6tc

Timestamps below refer to those transcripts.

**Gaps.** I found no Game Score Fanfare video on BotW. I could not reach the CEDEC 2017 slides; their content is known only from a Japanese blog summary. No source analyses "Field (Night)" or the 0:44 "Opening" cue in musical detail. Everything marked **[inference]** is mine, not a source's.

---

## 1. What the music is for

- Sound director Hajime Wakai: the team "stopped using the phrase 'World BGM' and replaced it with 'Environmental BGM'". The environmental noise itself is the background music. He chose piano, "which hasn't been used much in the series", to express a huge open world. Stirring music "would end up forcing a feeling of intensity onto players" during small actions. Source: the soundtrack booklet interview, https://nintendoeverything.com/breath-of-the-wild-composers-on-changing-up-zeldas-music-formula-and-more/
- Lead composer Manaka Kataoka, in the same interview: they "sacrificed some of the music" so players could hear "the distant cry of a beast or the burbling of a river".
- Yasuaki Iwata, in the same interview: the team spent about a month walking Hyrule to tune how far from a shrine its music should change, and how loud it should be.
- GMTK (1:48): the music "often fades out into complete silence, leaving you with nothing but ambient sounds and Link's footsteps."
- The score follows things the composers could predict: region, temperature and time of day (Schooley 8:13). It does not follow Link's mood.

## 2. The field piano ("Field (Day)" 2:46, "Field (Night)" 4:08)

### System behaviour (how it is played back)

- **Fragments, not a loop.** The CEDEC 2017 talk, as summarised by geekdrums (https://note.com/geekdrums/n/naeac6465b1a5?hl=en), says the field music is several phrase parts. Their order, the gaps between them, their volume and their left/right pan are randomised, so each play is slightly different. The randomness keeps a recognisable cycle, with branches and variations.
- **Spot BGM.** Piano phrases tied to places, such as cold areas and spots near shrines, are inserted into the field stream (same source).
- **Two independent voices.** Scruffy (4:42–5:14): the piece "always starts the same", but the high piano samples and the low piano samples are two separate tracks. Each plays at slightly randomised intervals, so they drift out of sync into new combinations. At longer random intervals "you might get a reverse piano note". This is the rare hidden event.
- **Gaps make region changes easy.** Each motif plays "in a random order after a random amount of time", so a crossfade between regions can happen in the silences (Schooley 9:24–9:48).
- **Music gives way to other cues.** Field music stops for combat, towns, stables, shrines, horse riding and the like.
- **Ducking when sneaking.** Crouching ducks the music (Schooley 5:49). Snowy weather puts the mountain-summit theme through a high-pass filter, which opens up when the weather clears (Scruffy 7:01–8:39).

### Note-level construction

**8BMT Part 1 (tl-6K3zrcr0) walks through the field theme step by step:**
- **2:37** "The first two notes immediately put us in the key of E-flat… this 2-1 melodic figure". A falling step to the tonic is enough to set the key. There is "no harmony to speak of".
- **2:53** The opening phrases "keep coming back to a B-flat", the fifth, which "keeps the music from resolving". Phrases are built on the 5th; avoid the tonic.
- **3:01** Phrases build intensity, then slow into **mode mixture: the ♭7** (D♭), which here "adds a somberness".
- **4:19** Phrases outline a **D♭7** chord, then a "leap down from D♭ to E♭, mirroring the very beginning".
- **4:53** A bare **4th** is "harmonically ambiguous… with no third… these notes could imply either" major or minor. 8BMT: "this ambiguity between major and minor is at the heart of what makes Zelda music sound like Zelda music."
- **5:18** The climax is a big, bright **B♭ over E♭ with no third**, on "by far the lowest note we've heard". The lowest note is held back for the climax.
- **5:35** A "harsh roll down of a **D♭13** chord and ominously low bass note."
- **5:49** Only at the end do the last three notes outline **E♭maj7**, "third and all". The major 3rd is withheld until the very end.
- **2:21** "What it lacks in energy it makes up for in mood… the composition process was very deliberate."

**Zelda Dungeon's analysis of "Field (Day)"** (https://www.zeldadungeon.net/musical-musings-listening-closely-to-the-emptiness-of-breath-of-the-wilds-hyrule-field-day/):
- Solo piano. "More silence than there is active motion… up to 13 consecutive seconds."
- A fan transcription counts about **¾ silence**.
- Activity is "almost exclusively in the higher registers". The rare low notes are "very low", and the middle register is left empty.
- Range is B♭1 to B♭7.
- Probably written in rubato with no time signature; published arrangements force it into 4/4.
- This writer hears B♭ major, while 8BMT hears E♭. Without harmony the key really is ambiguous, and that ambiguity is part of the style.

### Working numbers [inference, from the sources above and listening knowledge; verify by ear]

- **Phrases:** 2–7 notes over about 1.5–6 s, then 3–13 s of silence.
- **Dynamics:** pp–mp, with rare mf peaks.
- **Pedal:** sustain pedal held through each phrase so it rings into the silence. Most notes are legato or let ring; true staccato is rare in field music.
- **Ornaments:** occasional quick grace-note pickups and repeated notes (two or three strikes of one pitch).
- **Intervals:** steps, 4ths, 5ths and occasional 7th or 9th leaps.
- **Harmony:** single notes, open 5ths/4ths dyads, or rolled add9/maj7/13 chords.
- **Rhythm:** unmetered.

**Day versus night.** No source compares the two field tracks.
- Generally documented: in towns, night versions are slower and drop instruments (Wakai, via geekdrums). GMTK (3:26) says the same song's "tempo… shifts down during the night".
- [inference] Apply the same idea to the field music at night: sparser, softer, lower-centred, more ♭7/♭6 and sus colours, longer gaps.

## 3. Main theme and the opening moment

**8BMT Part 2 (F6YaK8bOvWY):**
- **0:36** The theme is "constructed out of only a few motifs". Kataoka probably wrote the main section first and then filled in the build-up, which "foreshadows" it (0:45).
- **1:21** The main section is "extremely dramatic". It uses huge leaps emphasising scale degrees 1 and 5.
- **1:41** It is built as a classical sentence:
  - a 2-bar motif, then two 1-bar variations (down, then back up), ending on a "♭2" cadence;
  - this is stretched to 8 bars, with the octave leap widened to a **tenth**;
  - "this main theme is in a minor key and borrows from the parallel major", which reverses the usual Zelda practice (2:42). 8BMT reads this as "Ganon has already pretty much won… but there's a glimmer of hope".
- **3:47** The cadence is "a classic ♭6–♭7–1 walkup" to a **C5 chord with no 3rd**: "will our hero come out on top or will he fall to the darkness".
- **5:02** The intro is "high alternating fourths and fifths on the piano". A somber 8-bar piano solo follows, with light choir: an antecedent–consequent period from F minor to A♭, where the ♯4 turns into ♮4 on the repeat.
- **6:09** An abrupt modulation to B major, scored for flute and strings, plays the main theme's first four bars "flipped around".
- **7:57** After the opening returns in C major, a transition over a chromatically descending bass reaches D dim → B♭sus → ♭7–1 into C minor.
- **9:09** "This one interval got stretched into two bars… four… eight… a 16-bar call and response."
- **9:50** The melody is first given to the **erhu**.

**Other sources on the main theme:**
- Kataoka's blog, as reported (https://zeldauniverse.net/2017/06/15/the-composer-of-breath-of-the-wilds-main-theme-gives-details-on-its-creation-and-purpose/): the land is "the true protagonist". She chose shinobue and erhu for its history. The sudden **full stop** (about 1:03 on the album) is Link's 100-year sleep, and the restart is "Link's first breath".
- Hooktheory (user transcription, https://www.hooktheory.com/theorytab/view/manaka-kataoka/legend-of-zelda---breath-of-the-wild-main-theme): **3/4** throughout. The chorus in C minor runs i – VI9 – iv7 – **♭II** – i.
- Kevin Armes (0:57–6:00) argues that the **♭II chord** appears in the main theme, all four Champion themes, the Divine Beasts and King Rhoam's theme, as a sign of defeat.

**Opening (OST Disc 1 track 2, 0:44, Kataoka).** It plays "when Link first exits the Shrine of Resurrection and looks over the Great Plateau" (Zelda Wiki). As the sprint begins, "the sound of a piano kicks in, and birds tweet" (Screen Rant).
- [inference, from memory of the scene; check by ear] Piano notes over wind and birdsong; strings swell as Link reaches the cliff and the camera circles; a full-orchestra statement of main-theme material lands on the wide reveal and title card; then a quick release back to ambience.
- Why it works:
  - this is the only big tutti in the first hour, so the contrast makes it land;
  - the land, not Link, gets the theme;
  - a sustained, open, unresolved chord leaves the player looking outward.

## 4. Combat

**Battle (Field)** (geekdrums, Scruffy 5:14–6:44, and https://www.zeldadungeon.net/?p=143188):
- **Form:** Intro, A, B, C, D, Outro.
  - Few or weak enemies: Intro→A→B, looped.
  - More or stronger enemies: A→B→C→D. C and D play only for strong foes.
  - Changes take effect at the start of the next loop, not instantly.
  - B→A ends quietly. B→C uses an ascending string scale. The outro is an ascending marimba run at the next beat.
- **Keys:** each part exists in about **3 keys a major third apart**. Scruffy: "equidistant". Zelda Dungeon hears A♭ → C → E.
  - B and D each have 6 variants (2 orchestrations × 3 keys). [inference] The selection probably avoids repeating the last key.
- **Hits are quantised.** Hits trigger piano or percussion gestures on the *next beat*, tiered by hit strength, with one set per key.
- **Build:**
  - starts with quiet percussion: marimba, bongos, güiro, castanets, shakers;
  - staccato string stabs;
  - **7/4**;
  - melody only after about 33 s; full motion at about 1:05; trumpets and a switch to 4/4 at the peak;
  - "the music dies back down, as though indicating… if they wish to leave the fight, now is the time."
- **Guardian:**
  - a high, atonal **piano trill** over a mechanical swell (pixeltea 22:58: "there's no mistaking what it means: run");
  - G major, 3/4, harmonised synth ostinato;
  - hits play a string "whoosh" on beat 2 of the next bar.

## 5. Shrines, towers, discoveries

**Shrine** (Iwata, https://www.zeldadungeon.net/?p=143757):
- Mostly electronic melody, over Japanese plucked strings, gamelan and a **bagpipe** drone.
- Tonal centre C, circling F and G, with D prominent.
- Floating **6/8** with no clear downbeat.
- Nomax (0:29): "five instrument layers that each have several variations". The game picks how many layers, which layers, and which variations, then repeats, following rules about what fits together.

**Shrine battle:** C major, 4/4 → 13/4, heavily syncopated, computer "beeps", and the shrine's bagpipe drone kept as a tether (https://www.zeldadungeon.net/musical-musings-an-analysis-of-the-complexity-of-breath-of-the-wilds-battle-shrine-theme/).

**Towers:** "Kataoka juxtaposes the piano and electronics… airy vocals ascend to weightless highs as you scale" (A Closer Listen).

**Tower activation** (Iwata, 0:19):
- Composer Soshi Abe names it a favourite: "when it plays, the camera pans out and shows the world around you" (Nintendo Everything).
- [inference] Write it as a short rising synth-and-piano gesture into a held, open chord, timed to the camera move.

**Jingles** (OST Disc 5, https://zeldawiki.wiki/wiki/The_Legend_of_Zelda:_Breath_of_the_Wild_Original_Soundtrack):
- Item Acquired 0:04; Important Item 0:07; Key Item 0:09
- Heart Container 0:06
- Korok Puzzle 0:06; A Korok Appears 0:06
- New Location 0:07
- Puzzle Solved 0:06
- Cooking jingles: 0:06–0:07, in three tiers (disaster, triumph, perfection)

Jingles are tiered by importance, and none is longer than 9 s.

## 6. Places, time of day, horse, and nostalgia

**Towns:**
- Each has day and night versions. They switch at **4:30 AM** and **8:30 PM**, with a 15-minute recorded tempo ramp (slower and thinner at night). The switch waits for a musical boundary (geekdrums; Scruffy 3:37–4:37).
- Town music fades in by distance from an intro, so towns, stables and Kass pull the player toward them (pixeltea 19:01; Schooley 10:52).

**Riding** (https://www.zeldadungeon.net/?p=145220):
- A bouncy piano ostinato in **6/8 that sounds like 4/4**, E♭ major.
- After long uninterrupted riding, strings enter. By day they play Zelda's Lullaby in heavy **augmentation**; by night, the old main Zelda theme (GMTK 4:30).
- Slowing down plays a jingle.

**Hidden motifs:** Temple of Time augments the Song of Time and breaks it up with silence, in solo piano with "bichords". Classic themes are withheld until "the perfect moment" (GMTK 10:25).

**Hyrule Castle, 8BMT Part 4 (nUoophDioZA):**
- **1:12** 5/4, G Aeolian ("the most gloomy kind of minor").
- **3:06** 6/4 every third bar of each 4-bar phrase.
- **4:21** Rising chromatic 4ths, "unsettling, totally ambiguous".
- **5:16** A known melody landing on the ♯11 of a **♭IImaj7♯11**.
- **8:04** Inside the castle: sus chords heard as minor, which give a "floaty feeling", plus B♭/A♭ Lydian voicings over ♭2. The interior and exterior versions crossfade.

**Kakariko, 8BMT Part 3 (xZBodzjVSjA):**
- **3:36** Shakuhachi melody in E minor pentatonic.
- **5:26** Koto runs in the *in* (insen) scale (1 ♭2 4 5 ♭7).
- **5:40** Koto cluster chords alternate natural 9 and ♭9.
- **7:10** It ends on an unresolved C major, which leads back to the top of the loop.

---

## Rules for writing original music in this style

S = supported by a cited source; I = my inference.

1. **Field music is solo piano only.** No pads, drums or bass under it. (S: Zelda Dungeon, geekdrums)
2. **Build field music from 6–15 short fragments, not a loop.** Each fragment is 2–7 notes and lasts about 1.5–6 s. Play them in random order, with a fixed opening fragment and a loose cycle. (S: geekdrums, Scruffy; the numbers are I)
3. **At least 60% of field time is silence.** The target is about 75%. Gaps between fragments are random between 3 and 13 s. (S: Zelda Dungeon's ¾ figure and 13 s maximum)
4. **High and low fragments run on two independent random timers,** so they drift relative to each other. (S: Scruffy)
5. **Randomise each fragment's volume (±3 dB) and pan (±30%).** (S for the randomisation, geekdrums; I for the ranges)
6. **Use the extremes of the keyboard.** Most notes above C5, rare single bass notes below C2, almost nothing in the middle. Save the lowest note for the climactic fragment. (S: Zelda Dungeon, 8BMT 5:27)
7. **Hold back the major 3rd.** Prefer root–5th, 4ths and sus sonorities. Outline the full major or major-7 chord only in a "resolution" fragment, used at most once per cycle. (S: 8BMT 4:53, 5:18, 5:49)
8. **No perfect authentic cadence in field, shrine or castle-interior music.** End phrases on the 5th, 2nd or 9th, on a sus chord, or on a chord with no 3rd. (S: 8BMT on the 5th "keeps the music from resolving" and the no-3rd C5 ending; I as a strict rule)
9. **Every field set includes ♭7 mode mixture** (a ♭VII or ♭7-chord fragment). Every "story" theme includes at least one **♭II** (Neapolitan or Phrygian) chord. (S: 8BMT Part 1 3:09, Part 4 5:16; Armes)
10. **The field piano is unmetered and rubato.** Sustain pedal rings through each fragment. No staccato in field fragments; staccato belongs to combat. (S for rubato, Zelda Dungeon; I for pedal and staccato)
11. **Allow colour chords as single rolled events:** maj7, add9, 13, or a whole-tone flash. Never a functional progression longer than 3 chords. (S: 8BMT's D♭13 roll; I for the limit)
12. **Ambient sound comes first.** Field music sits about 6–10 dB below wind and footsteps. Duck it further when crouching or sneaking. High-pass it in storms or snow. (S: Wakai, Schooley, Scruffy; I for the dB figures)
13. **Combat has 4 sections plus intro and outro, escalating by threat.** Weak foes loop the first two sections; strong foes unlock the last two. Switch only at loop boundaries. (S: geekdrums)
14. **Combat comes in 3 keys a major third apart.** Odd meter (7/4) at the start, 4/4 at the peak. Percussion and staccato piano or string stabs first; melody only after about 30 s; brass at the top. (S: Scruffy, Zelda Dungeon)
15. **Quantise hit stingers to the next beat,** in the current key, with 2–3 tiers by hit strength. (S: Scruffy, geekdrums)
16. **Shrine music is layered and generative.** About 5 stems, each with 2–4 variations. Randomise how many layers play and which ones, with a compatibility table. Synth lead over plucked strings and a drone, in a floating 6/8. (S: Nomax, Zelda Dungeon)
17. **Jingles are short and tiered:** 4 s for common items, 6–7 s for medium rewards, at most 9 s for key items. Tower activation is about 19 s and timed to a camera reveal. (S: OST durations, Abe)
18. **Day and night share material.** Night is slower and has fewer instruments. Ramp the tempo over about 15 game-minutes, at a musical boundary. (S: geekdrums, Scruffy)
19. **The big tutti is saved for one reveal,** such as leaving the starting cave. The main theme gets one sudden full-stop "breath" rest. (S: Kataoka on the break; I for applying it to the reveal)
20. **Quote motifs only by augmentation and fragmentation,** and only at rare, earned moments. In a parody, quote your *own* leitmotifs this way, never BotW's. (S: Temple of Time and riding analyses, GMTK; I for the parody rule)
