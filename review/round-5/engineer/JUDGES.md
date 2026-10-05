# Judges on engineer, round 5 pass 2

## Improve

Failed:
- Ticket reading surface looks crafted under the night light: In read_carousel_ticket.jpg the card is still a flat grey-mauve with a pale pink stub. It reads like a UI box, not a warm printed ticket.
- Riesenrad gondola placards carry the questions in production: The builder says they are left out of production builds until Mac confirms the questions, so the placards still fall back to the noticeboard.

Fixes:
- Get Mac to confirm the three questions in content/questions.md, and have the writer remove the review notes, so the gondola placards ship in production.
- Fix the ticket look. Get the ride builder (or the lighting designer) to apply the deeper stub tint from rides_ticket_stub.patch. Warm the ticket card's backing or lighting so it no longer reads grey-mauve. Then re-shoot read_carousel_ticket.jpg.
- Have the carpenter ship the write_reading_card node in stall_buecher.glb, which retires the code-built stand-in card.
- Recapture the home still and rebuild after the next lighting or layout change.
