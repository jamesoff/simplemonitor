window.L = require("leaflet");
import "leaflet/dist/leaflet.css";

import IconUp from "./marker-single-up.png";
import IconDown from "./marker-single-down.png";
import IconShadow from "./marker-shadow.png";

window.markerIconUp = L.icon({
  iconUrl: IconUp,
  shadowUrl: IconShadow,
  popupAnchor: [11, 2],
});

window.markerIconDown = L.icon({
  iconUrl: IconDown,
  shadowUrl: IconShadow,
  popupAnchor: [11, 2],
});
