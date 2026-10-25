# Contributing / Jak dołożyć przejazd

## Record a trip

1. **Before departure**
   - Connect the laptop to the phone's hotspot. Put the phone by the window, at glass height.
   - Start a GPS recorder on the phone (e.g. *Open GPX Tracker* on iOS, *GPSLogger* on Android).
   - Start the logger: `railcov/logger.sh trips/<YYYY-MM-DD>-<train>-<from>-<to>/ping.csv`
2. **During the trip**
   - Do not download anything big over the same link. A 7 MB download on a 2 Mbit/s
     uplink produced ten minutes of fake "dead zone" in the first trip.
   - Note delays and confirmed stops (time + station). They go into `trip.json`.
3. **After the trip**
   - Copy `trips/2026-10-25-ic141-bialystok-krakow/trip.json` as a template and fill in
     the train, timetable, network, delays and any time windows to exclude.
   - Add `stations.json` (name, lat, lon from OpenStreetMap).
   - `python -m railcov.gpx trips/<id> recording.gpx`. This keeps only the part between
     the first and the last station, so the track does not reveal where you live.
   - `python -m railcov.bts trips/<id>`, `python -m railcov.report trips/<id>`, `python -m railcov.site`
   - Open a pull request with the trip folder.

## What makes a trip useful

- A line or operator that is not covered yet. Check the map first.
- An honest `trip.json`: device, network, where the phone was, what else used the link.
- Android extras (optional): a log from *Network Cell Info* or *G-NetTrack* with RSRP and
  cell ID. Put it in the trip folder as `cells.csv` and describe the columns in the PR;
  support in the code will follow.

## Other contributions

- Better train positions: OSM rail geometry instead of straight lines between stations
  (`railcov/model.py`).
- Other operators' base stations (`railcov/bts.py --operators Plus,Play`).
- Translations, charts, and checks of the method in [docs/methodology.md](docs/methodology.md).

## Privacy

Publish only your own measurements. Do not include phone numbers, IMEI, IP addresses,
or GPS points outside the train route.

---

**Po polsku w skrócie:** podłącz laptopa do hotspotu, włącz nagrywanie GPS w telefonie,
uruchom `railcov/logger.sh`, w trakcie jazdy nic dużego nie pobieraj, po podróży uzupełnij
`trip.json` i wyślij pull request z folderem przejazdu. Ślad GPS jest automatycznie
przycinany do odcinka od stacji do stacji.
