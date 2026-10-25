# Methodology

## Measurement

- `ping -c 10 -i 0.3 -W 2 1.1.1.1` every 30 s from a laptop on the phone's Wi-Fi hotspot.
  One CSV row per burst: loss %, min / avg / max round-trip time.
- The Wi-Fi hop laptop → phone was checked at the start (signal −30 dBm, 144 Mbit/s,
  ping to the phone ~10 ms), so the numbers describe the cellular link.
- A reply later than 2 s counts as lost. Very congested moments therefore show as loss,
  not only as high latency.

## Position

1. **GPS** from the phone, when a track point exists within 90 s of the measurement.
2. **Timetable** otherwise: constant speed between timed stops, straight lines between
   consecutive stations (including stations the train passes without stopping).
   Observed delays shift the model from the moment they were noticed. Error: a few km,
   more on long non-stop sections.

## Base stations

UKE publishes lists of radio permits per band (bip.uke.gov.pl, "Stacje GSM, UMTS, LTE,
5GNR oraz CDMA"). We take LTE 800/1800/2100/2600 and 5G 2100 for Orange and T-Mobile,
which share most rural sites through NetWorkS!, and keep sites within 8 km of the route.
A permit does not prove the station is on air or that it covers the track.

## Exclusions

Time windows in `trip.json → excluded` are shown on the map in grey and left out of all
statistics. Each one states the reason.

## Hotspot dropouts

On the first trip the iPhone switched its hotspot off by itself twice, both times
right after a long loss of cellular data. The laptop's NetworkManager log
(`ssid-not-found`, then a new DHCP lease) gives the exact window. Such windows, plus
about a minute after reconnecting, are excluded: they measure the phone, not the network.
Check `journalctl -u NetworkManager` after every trip.

## Limits

- One phone, one network, one trip per folder. Treat a single trip as an observation.
- Ping measures latency and loss, not throughput.
- Train cars attenuate signal differently. Windows with metal coatings are common in
  newer stock.
