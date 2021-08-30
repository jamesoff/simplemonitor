window.$ = require("jquery");
window.bootstrap = require("bootstrap");
import "bootstrap/dist/css/bootstrap.min.css";
import "./style.css";

window.too_old = function () {
  $("#refresh_badge").removeClass("d-none");
  $("#refresh_status").addClass("d-inline");
  $("#summary").removeClass("border-success border-danger");
  $("#summary").addClass("border-warning");
};

window.update_age = function (props) {
  const now = parseInt(Date.now() / 1000); // ms to s
  const diff = now - props.timestamp;
  var updated = "at some point";
  if (diff < 10) {
    updated = "just now";
  } else {
    updated = `${diff} seconds ago`;
  }
  // not using Bootstrap tooltip here as it gets stuck if this element is
  // updated while the tooltip is shown
  const update_string = `Updated <span
  title="${props.updated}">${updated}</span> by ${props.host}
  (${props.version})`;
  $("#updated").html(update_string);
  $("#updatedfooter").html(update_string);
};
