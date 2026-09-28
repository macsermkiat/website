# 2. Ship the band as pre-mixed recorded stems

The prototype writes the ballad live in the browser from samples. That limits it to one reverb, simple dynamics and a synthetic-sounding sax. The real site ships a composed ballad rendered and mixed offline, one audio stem per instrument (sax, piano, bass, drums), plus a mixed reverb return. The page plays the stems in sync, pans them by the bandstand's position and can feature one player.

Considered: live generation (varies every chorus but sounds cheaper) and a single stereo mix (smallest, but loses spatial placement and featuring). Stems cost about four times the bytes of a stereo mix, so each stem is compressed and streamed after the market is visible.
